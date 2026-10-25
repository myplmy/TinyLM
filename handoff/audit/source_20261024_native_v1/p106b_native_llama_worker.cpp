// Exact b11396 headers, existing shared libraries only; no sampler or HTTP.
// Wire is explicitly little endian, NOT a Python copy of a llama C struct.
#include "llama.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr uint32_t MAX_FRAME = 14000000;
constexpr uint32_t MAX_CONTEXT = 1024;
const char * ENGINE = "/home/uranus/llama-b11396";
double stop_epoch = 0;
double now() { return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count(); }
void deadline() { if (now() >= stop_epoch) throw std::runtime_error("worker deadline expired"); }
bool progress(float, void *) { return now() < stop_epoch; }
using Bytes = std::vector<uint8_t>;
void u32(Bytes & b, uint32_t v) { for (int i=0;i<4;++i) b.push_back(uint8_t(v>>(8*i))); }
void u64(Bytes & b, uint64_t v) { for (int i=0;i<8;++i) b.push_back(uint8_t(v>>(8*i))); }
void f64(Bytes & b, double v) { uint64_t bits; std::memcpy(&bits,&v,8); u64(b,bits); }
void f32(Bytes & b, float v) { uint32_t bits; std::memcpy(&bits,&v,4); u32(b,bits); }
void text(Bytes & b, const std::string & s) { u32(b,uint32_t(s.size())); b.insert(b.end(),s.begin(),s.end()); }
struct Reader {
    const Bytes & data; size_t pos=0;
    uint32_t number() { if (data.size()-pos<4) throw std::runtime_error("short wire integer"); uint32_t v=0; for(int i=0;i<4;++i) v|=uint32_t(data[pos++])<<(8*i); return v; }
    std::string string() { auto n=number(); if(n>1000000 || data.size()-pos<n) throw std::runtime_error("invalid wire text length"); std::string s(data.begin()+pos,data.begin()+pos+n); pos+=n; return s; }
    std::vector<llama_token> tokens(uint32_t cap=MAX_CONTEXT) { auto n=number(); if(n>cap || data.size()-pos<size_t(n)*4) throw std::runtime_error("invalid token count"); std::vector<llama_token> t; t.reserve(n); for(uint32_t i=0;i<n;++i)t.push_back(int32_t(number())); return t; }
    void end() { if(pos!=data.size()) throw std::runtime_error("wire trailing bytes"); }
};
bool frame(Bytes & b) {
    char h[4]; std::cin.read(h,4); if(std::cin.gcount()==0 && std::cin.eof()) return false;
    if(std::cin.gcount()!=4) throw std::runtime_error("short frame header");
    uint32_t n=0; for(int i=0;i<4;++i)n|=uint32_t(uint8_t(h[i]))<<(8*i);
    if(n<8 || n>MAX_FRAME) throw std::runtime_error("frame cap violated");
    b.resize(n); std::cin.read(reinterpret_cast<char *>(b.data()),n);
    if(size_t(std::cin.gcount())!=n) throw std::runtime_error("short frame body");
    return true;
}
void reply(uint32_t op,uint32_t id,uint32_t status,const Bytes & body) {
    Bytes out; u32(out,op);u32(out,id);u32(out,status);out.insert(out.end(),body.begin(),body.end());
    if(out.size()>MAX_FRAME) throw std::runtime_error("response frame cap violated");
    Bytes h;u32(h,uint32_t(out.size())); std::cout.write(reinterpret_cast<const char *>(h.data()),h.size());
    std::cout.write(reinterpret_cast<const char *>(out.data()),out.size());std::cout.flush();
    if(!std::cout) throw std::runtime_error("worker stdout closed");
}
std::pair<double,bool> target_logp(const float * row,int32_t count,int32_t target) {
    if(!row || target<0 || target>=count) throw std::runtime_error("invalid logits/target");
    double maximum=-std::numeric_limits<double>::infinity(); int32_t argmax=0;
    for(int32_t j=0;j<count;++j) { if(!std::isfinite(row[j]))throw std::runtime_error("nonfinite raw logit"); if(row[j]>maximum){maximum=row[j];argmax=j;} }
    long double sum=0;for(int32_t j=0;j<count;++j)sum+=std::exp(double(row[j])-maximum);
    double lp=double(static_cast<long double>(row[target])-maximum-std::log(sum));
    if(!std::isfinite(lp) || lp>0)throw std::runtime_error("invalid target logp");
    return {lp,argmax==target};
}
struct Runtime {
    llama_model * model=nullptr; llama_context * ctx=nullptr; const llama_vocab * vocab=nullptr;
    ggml_backend_dev_t devices[2]={nullptr,nullptr}; int32_t size=0; uint64_t clears=0;
    Runtime(const std::string & path,const std::string & architecture) {
        try {
            deadline(); ggml_backend_load_all_from_path(ENGINE); llama_backend_init();
            devices[0]=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
            if(!devices[0])throw std::runtime_error("no native GPU backend; CPU fallback is not admitted");
            auto mp=llama_model_default_params();mp.devices=devices;mp.n_gpu_layers=-1;mp.split_mode=LLAMA_SPLIT_MODE_NONE;
            mp.use_extra_bufts=false;mp.load_mtp=false;mp.check_tensors=true;mp.progress_callback=progress;
            model=llama_model_load_from_file(path.c_str(),mp);if(!model)throw std::runtime_error("native model loading failed");
            char arch[128];if(llama_model_meta_val_str(model,"general.architecture",arch,sizeof arch)<0 || architecture!=arch)throw std::runtime_error("native architecture differs");
            vocab=llama_model_get_vocab(model);size=llama_vocab_n_tokens(vocab);
            if(size<2 || llama_model_n_ctx_train(model)<1024)throw std::runtime_error("invalid native vocabulary/context");
            if(architecture=="gpt2" && (size!=50257 || llama_model_n_ctx_train(model)!=1024))throw std::runtime_error("GPT2 vocabulary/context identity differs");
            auto cp=llama_context_default_params();cp.n_ctx=1024;cp.n_batch=1024;cp.n_ubatch=1024;cp.n_seq_max=1;
            cp.n_outputs_max=1024;cp.n_outputs_max_per_seq=1024;cp.n_rs_seq=0;cp.n_threads=4;cp.n_threads_batch=4;
            cp.attention_type=LLAMA_ATTENTION_TYPE_CAUSAL;cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
            cp.type_k=GGML_TYPE_F32;cp.type_v=GGML_TYPE_F32;cp.no_perf=false;cp.embeddings=false;
            cp.offload_kqv=true;cp.op_offload=true;cp.samplers=nullptr;cp.n_samplers=0;
            ctx=llama_init_from_model(model,cp);if(!ctx)throw std::runtime_error("native context creation failed");
            if(llama_n_ctx_seq(ctx)!=1024 || llama_n_batch(ctx)!=1024 || llama_n_ubatch(ctx)!=1024)throw std::runtime_error("native context/batch differs");
            clear();deadline();
        } catch(...) { release();throw; }
    }
    void release() { if(ctx){llama_free(ctx);ctx=nullptr;}if(model){llama_model_free(model);model=nullptr;} }
    ~Runtime(){release();}
    void ids(const std::vector<llama_token> & t,bool empty=false) { if(t.empty()&&!empty)throw std::runtime_error("empty token input");for(auto v:t)if(v<0||v>=size)throw std::runtime_error("token outside actual vocabulary"); }
    void clear(){if(ctx){llama_memory_clear(llama_get_memory(ctx),true);++clears;}}
    struct Clear {Runtime & owner; explicit Clear(Runtime & r):owner(r){owner.clear();}~Clear(){owner.clear();}};
    void decode(const std::vector<llama_token> & input,const std::vector<uint32_t> & positions) {
        ids(input);if(input.size()>MAX_CONTEXT || positions.empty())throw std::runtime_error("invalid bounded decode input");
        auto batch=llama_batch_init(int32_t(input.size()),0,1);
        try {
            batch.n_tokens=int32_t(input.size());
            for(size_t i=0;i<input.size();++i){batch.token[i]=input[i];batch.pos[i]=int32_t(i);batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;batch.logits[i]=0;}
            for(auto p:positions){if(p>=input.size())throw std::runtime_error("logits position out of range");batch.logits[p]=1;}
            deadline();int rc=llama_decode(ctx,batch);if(rc!=0)throw std::runtime_error("llama_decode returned "+std::to_string(rc));deadline();
        }catch(...){llama_batch_free(batch);throw;}
        llama_batch_free(batch);
    }
    Bytes info(const std::string & architecture) {
        Bytes out; for(auto v:{size,llama_model_n_ctx_train(model),int32_t(llama_n_ctx_seq(ctx)),int32_t(llama_n_batch(ctx)),int32_t(llama_n_ubatch(ctx)),llama_vocab_bos(vocab),llama_vocab_eos(vocab)})u32(out,uint32_t(v));
        u32(out,llama_vocab_get_add_bos(vocab));u32(out,llama_vocab_get_add_eos(vocab));u32(out,uint32_t(llama_vocab_type(vocab)));
        u64(out,llama_model_n_params(model));u64(out,llama_model_size(model));text(out,architecture);text(out,ggml_backend_dev_name(devices[0]));
        for(auto key:{"tokenizer.ggml.model","tokenizer.ggml.pre"}){
            char value[1024];int n=llama_model_meta_val_str(model,key,value,sizeof value);
            if(n>=int(sizeof value))throw std::runtime_error("tokenizer metadata exceeds bound");
            text(out,n<0?"<ABSENT>":std::string(value));
        }
        return out;
    }
    Bytes command(uint32_t op,Reader & in) {
        deadline();Bytes out;
        if(op==2){
            uint32_t flags=in.number();if(flags>3)throw std::runtime_error("tokenizer flags invalid");auto text=in.string();in.end();
            int32_t n=llama_tokenize(vocab,text.data(),int32_t(text.size()),nullptr,0,flags&1,flags&2);
            if(n==std::numeric_limits<int32_t>::min())throw std::runtime_error("tokenization overflow");
            std::vector<llama_token> tokens(size_t(n<0?-n:n));
            int32_t actual=llama_tokenize(vocab,text.data(),int32_t(text.size()),tokens.data(),int32_t(tokens.size()),flags&1,flags&2);
            if(actual<0 || size_t(actual)!=tokens.size())throw std::runtime_error("tokenizer count changed");
            ids(tokens,true);u32(out,uint32_t(tokens.size()));for(auto t:tokens)u32(out,uint32_t(t));
        }else if(op==3){
            auto input=in.tokens();uint32_t start=in.number();auto labels=in.tokens();in.end();ids(labels);
            if(start+labels.size()!=input.size())throw std::runtime_error("target-label alignment differs");
            for(size_t i=0;i+1<labels.size();++i)if(input[start+i+1]!=labels[i])throw std::runtime_error("teacher-forced label shift differs");
            std::vector<uint32_t> positions;for(uint32_t i=start;i<input.size();++i)positions.push_back(i);
            Clear guard(*this);decode(input,positions);std::vector<std::pair<double,bool>> scores;long double sum=0;bool greedy=true;
            for(size_t i=0;i<labels.size();++i){auto s=target_logp(llama_get_logits_ith(ctx,int32_t(start+i)),size,labels[i]);scores.push_back(s);sum+=s.first;greedy=greedy&&s.second;}
            u32(out,uint32_t(scores.size()));f64(out,double(sum));u32(out,greedy);for(auto s:scores){f64(out,s.first);u32(out,s.second);}
        }else if(op==4){
            auto input=in.tokens();auto count=in.number();if(count==0 || uint64_t(count)*uint64_t(size)*4+32>MAX_FRAME)throw std::runtime_error("raw logits frame cap");
            std::vector<uint32_t> positions;for(uint32_t i=0;i<count;++i){auto p=in.number();if(i&&p<=positions.back())throw std::runtime_error("logits positions must increase");positions.push_back(p);}in.end();
            Clear guard(*this);decode(input,positions);u32(out,count);u32(out,uint32_t(size));
            for(auto p:positions){auto row=llama_get_logits_ith(ctx,int32_t(p));if(!row)throw std::runtime_error("missing full logits row");for(int32_t i=0;i<size;++i){if(!std::isfinite(row[i]))throw std::runtime_error("nonfinite full logit");f32(out,row[i]);}}
        }else if(op==5){
            auto tokens=in.tokens(1000000);in.end();ids(tokens,true);int32_t n=llama_detokenize(vocab,tokens.data(),int32_t(tokens.size()),nullptr,0,false,true);
            if(n==std::numeric_limits<int32_t>::min())throw std::runtime_error("detokenization overflow");
            std::string result(size_t(n<0?-n:n),'\0');
            int32_t actual=llama_detokenize(vocab,tokens.data(),int32_t(tokens.size()),result.data(),int32_t(result.size()),false,true);
            if(actual<0 || size_t(actual)!=result.size())throw std::runtime_error("detokenizer size changed");
            text(out,result);
        }else throw std::runtime_error("unknown wire operation");
        deadline();return out;
    }
};
}

int main(int argc,char ** argv) {
    if(argc==2 && std::string(argv[1])=="--self-test") {
        float row[]={10000,9999,-10000};auto s=target_logp(row,3,1);
        if(std::abs(s.first-(-1-std::log1p(std::exp(-1))))>1e-10 || s.second)return 8;
        Bytes b;u32(b,0x12345678);Reader r{b};if(r.number()!=0x12345678)return 8;r.end();
        std::cout<<"CPU_ONLY; backend_init=0; model_loads=0\n";return 0;
    }
    if(argc!=5 || std::string(argv[1])!="--execute") {std::cerr<<"explicit --execute MODEL_PATH ARCHITECTURE DEADLINE_EPOCH required; no backend initialized\n";return 8;}
    try {
        stop_epoch=std::stod(argv[4]);
        if(!std::isfinite(stop_epoch) || stop_epoch>1792798800)throw std::runtime_error("deadline exceeds authorized 08:40 KST window");
        deadline();std::string architecture=argv[3];
        if(architecture!="gpt2" && architecture!="qwen35")throw std::runtime_error("unregistered architecture");
        const std::string allowed=architecture=="gpt2"
            ?"/home/uranus/tinyLM/HF/benchmark_20261023/gpt2_q4km/gpt2-q4_k_m.gguf"
            :"/home/uranus/tinyLM/HF/benchmark_20261023/qwen35_08b_iq2xxs/Qwen3.5-0.8B-UD-IQ2_XXS.gguf";
        if(argv[2]!=allowed)throw std::runtime_error("unregistered model path; no backend initialized");
        Runtime runtime(argv[2],architecture);Bytes request;
        while(frame(request)) {
            Reader in{request};auto op=in.number(),id=in.number();
            try {
                if(op==1){in.end();reply(op,id,0,runtime.info(architecture));}
                else if(op==6){in.end();Bytes out;u64(out,runtime.clears);reply(op,id,0,out);break;}
                else reply(op,id,0,runtime.command(op,in));
            }catch(const std::exception & e){runtime.clear();Bytes out;text(out,e.what());reply(op,id,1,out);return 9;}
        }
        return 0;
    }catch(const std::exception & e){std::cerr<<"native worker error: "<<e.what()<<"\n";return 9;}
}
