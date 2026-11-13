"""Read-only owned nvidia-smi stream; no installs, GPU reset or stale reuse.

Arrival timestamps are not hardware acquisition timestamps. Two-second
sampling cannot establish continuous peak/OOM safety. Old sessions are changed
only inside a process-local scope that restores all methods on exit.
"""
from __future__ import annotations
from contextlib import contextmanager
import os
import signal
import subprocess
import threading
import time
from unittest.mock import patch

COMMAND=('nvidia-smi','--query-gpu=memory.used,memory.free',
         '--format=csv,noheader,nounits','--id=0','--loop-ms=2000')


def parse_memory(line):
    parts=line.strip().split(',')
    if len(parts)!=2:raise ValueError('one GPU/two memory fields required')
    if any(not part.strip().isdigit() for part in parts):raise ValueError('invalid memory field')
    value=tuple(int(part.strip()) for part in parts)
    if any(part<0 for part in value):raise ValueError('negative memory field')
    return value


class FreshSamples:
    def __init__(self,*,clock=time.monotonic,timeout=5.,max_age=5.):
        self.clock,self.timeout,self.max_age=clock,timeout,max_age
        self.condition=threading.Condition();self.sequence=0;self.delivered=0
        self.latest=None;self.dead=None;self.calls=0;self.timeouts=0
        self.ages=[];self.latencies=[];self.arrival_gaps=[];self.last_arrival=None

    def observe(self,value):
        if not isinstance(value,tuple) or len(value)!=2 or any(type(v) is not int or v<0 for v in value):
            raise ValueError('invalid memory observation')
        now=self.clock()
        with self.condition:
            if self.last_arrival is not None:self.arrival_gaps.append(now-self.last_arrival)
            self.arrival_gaps=self.arrival_gaps[-1024:];self.last_arrival=now
            self.sequence+=1;self.latest=(self.sequence,now,value);self.condition.notify_all()

    def mark_dead(self,reason):
        with self.condition:self.dead=reason;self.condition.notify_all()

    def read(self):
        began=self.clock();deadline=began+self.timeout
        with self.condition:
            self.calls+=1
            while True:
                if self.dead is not None:raise RuntimeError('owned memory stream failed: '+self.dead)
                now=self.clock()
                if self.latest is not None:
                    sequence,stamp,value=self.latest;age=now-stamp
                    if sequence>self.delivered and 0<=age<=self.max_age:
                        self.delivered=sequence;self.ages.append(age);self.latencies.append(now-began)
                        self.ages=self.ages[-1024:];self.latencies=self.latencies[-1024:]
                        return value
                remaining=deadline-now
                if remaining<=0:
                    self.timeouts+=1
                    raise subprocess.TimeoutExpired(COMMAND,self.timeout)
                self.condition.wait(remaining)

    def snapshot(self):
        with self.condition:
            return dict(schema='P106B_FRESH_MEMORY_STREAM_V1',received_frames=self.sequence,
                delivered_sequence=self.delivered,calls=self.calls,timeout_calls=self.timeouts,
                last_received_monotonic=self.last_arrival,requested_loop_ms=2000,
                sample_age_max_sec=max(self.ages,default=None),
                call_latency_max_sec=max(self.latencies,default=None),
                arrival_gap_max_sec=max(self.arrival_gaps,default=None),
                bounded_tail_size=1024,dead_reason=self.dead,
                repeated_sequence_deliveries=0,hardware_timestamp_known=False,
                continuous_peak_verified=False,oom_safety='NOT_ESTABLISHED')


class PersistentMemory:
    def __init__(self):self.broker=FreshSamples();self.process=None;self.worker=None
    def __enter__(self):
        self.process=subprocess.Popen(COMMAND,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
            bufsize=1,start_new_session=True)
        def drain():
            try:
                for line in self.process.stdout:self.broker.observe(parse_memory(line))
                self.broker.mark_dead('unexpected EOF')
            except Exception as exc:self.broker.mark_dead(type(exc).__name__+': '+str(exc)[:200])
        self.worker=threading.Thread(target=drain,daemon=True);self.worker.start();return self
    def __call__(self):return self.broker.read()
    def snapshot(self):return dict(self.broker.snapshot(),owned_process_starts=1)
    def __exit__(self,*_):
        # Only this exact query subprocess group; never the user's teacher/GPU.
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGTERM)
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=2)
        if self.worker is not None:self.worker.join(timeout=1)
        if self.process is not None and self.process.stdout is not None:self.process.stdout.close()


@contextmanager
def stream_session_scope(reader):
    from scripts import diag_p106b_gemma_telemetry_resume as telemetry
    from scripts import diag_p106b_mtp_teacher as lifecycle
    original=lifecycle.Session.memory
    with telemetry.telemetry_scope(reader):
        measured=lifecycle.Session.memory
        def memory(session):
            result=measured(session)
            return dict(result,scope='persistent2s requested GPU query/process RSS; arrival-time samples, may miss peaks',
                reader_backend='PERSISTENT_NVIDIA_SMI_2S',continuous_peak_verified=False)
        with patch.object(lifecycle.Session,'memory',memory):yield
    assert lifecycle.Session.memory is original
