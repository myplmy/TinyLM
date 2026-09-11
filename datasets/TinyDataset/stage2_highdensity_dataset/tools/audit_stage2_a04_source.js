const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=process.cwd();
const src=path.join(root,'stage2_highdensity_dataset','sources','train');
const files=fs.readdirSync(src).filter(f=>/^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(f)).sort();
const warningRulesPath=path.join(root,'stage2_highdensity_dataset','tools','primary_naturalness_warning_rules_v1.json');
const warningRulesRaw=fs.readFileSync(warningRulesPath),warningRules=JSON.parse(warningRulesRaw.toString('utf8'));
const firstOnly=process.argv[2]==='first';
const outIndex=process.argv.indexOf('--out');
const outPath=outIndex>=0?process.argv[outIndex+1]:null;
if(outIndex>=0&&(!outPath||outPath.startsWith('--')))throw new Error('--out requires a path');
const tokPath=path.resolve(root,'..','..','data_cache','tok-ko-en-32768.json');
const payload=JSON.parse(fs.readFileSync(tokPath,'utf8')), model=payload.model;
const bv=[],uv=[];
for(let i=33;i<=126;i++){bv.push(i);uv.push(i);}
for(let i=161;i<=172;i++){bv.push(i);uv.push(i);}
for(let i=174;i<=255;i++){bv.push(i);uv.push(i);}
let extra=0; const enc=new Map();
for(let i=0;i<bv.length;i++)enc.set(bv[i],String.fromCodePoint(uv[i]));
const used=new Set(bv);
for(let i=0;i<256;i++)if(!used.has(i)){enc.set(i,String.fromCodePoint(256+extra));extra++;}
const rank=new Map(model.merges.map((p,i)=>[p[0]+'\u0000'+p[1],i]));
const rx=/'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+/gu;
const cache=new Map();
function bpe(token){
  if(cache.has(token))return cache.get(token);
  let w=Array.from(token);
  if(w.length<=1){cache.set(token,w);return w;}
  while(true){
    let best=null,br=1e12;
    for(let i=0;i<w.length-1;i++){let k=w[i]+'\u0000'+w[i+1],r=rank.has(k)?rank.get(k):1e12;if(r<br){br=r;best=[w[i],w[i+1]];}}
    if(!best||br===1e12)break;
    let out=[],i=0;
    while(i<w.length){if(i<w.length-1&&w[i]===best[0]&&w[i+1]===best[1]){out.push(w[i]+w[i+1]);i+=2;}else{out.push(w[i]);i++;}}
    w=out;if(w.length===1)break;
  }
  cache.set(token,w);return w;
}
function count(t){
  let n=0;
  for(const p of t.match(rx)||[]){let s='';for(const b of Buffer.from(p,'utf8'))s+=enc.get(b);n+=bpe(s).length;}
  return n;
}
const nw=value=>String(value||'').normalize('NFKC').replace(/\s+/gu,' ').trim();
const qualifier=primary=>{const m=nw(primary).match(/\s+[—–-]\s+(.+)$/u);return m?m[1]:null;};
function naturalnessWarnings(rows){
  const assignments=[];
  const add=(row,code,rule,extra={})=>assignments.push({owner:row.owner,primary:row.primary,text:row.text,code,expression:rule.term||rule.prefix||rule.phrase||null,category:rule.category||null,reason:rule.reason||null,...extra});
  for(const row of rows){
    const q=qualifier(row.primary);
    if(q){
      add(row,'primary_dash_qualifier',{}, {qualifier:q});
      const exact=(warningRules.qualifier_exact_terms||[]).find(rule=>q===nw(rule.term));
      if(exact)add(row,'primary_warning_expression_exact',exact);
      else{
        const prefix=(warningRules.qualifier_prefix_terms||[]).find(rule=>q===nw(rule.prefix)||q.startsWith(nw(rule.prefix)+' '));
        if(prefix)add(row,'primary_warning_expression_prefix',prefix,{qualifier:q});
      }
    }
    const primary=nw(row.primary),text=nw(row.text);
    for(const rule of warningRules.primary_contains_terms||[])if(primary.includes(nw(rule.term)))add(row,'primary_warning_constructed_term',rule);
    for(const rule of warningRules.text_opaque_phrases||[])if(text.includes(nw(rule.phrase)))add(row,'text_warning_opaque_record_keeping',rule);
  }
  const summarize=selector=>{
    const buckets=new Map();
    for(const item of assignments){const key=selector(item);if(!buckets.has(key))buckets.set(key,{value:key,assignments:0,owners:new Set(),examples:[]});const bucket=buckets.get(key);bucket.assignments++;bucket.owners.add(item.owner);if(bucket.examples.length<5)bucket.examples.push({owner:item.owner,primary:item.primary,text:item.text});}
    return [...buckets.values()].map(bucket=>({value:bucket.value,assignments:bucket.assignments,records:bucket.owners.size,examples:bucket.examples})).sort((a,b)=>b.records-a.records||a.value.localeCompare(b.value));
  };
  const dashRows=rows.filter(row=>qualifier(row.primary));
  const dashOwners=new Set(dashRows.map(row=>row.owner));
  const dashStyle=warningRules.dash_style_review||{};
  const particles=Array.isArray(dashStyle.copied_subject_particles)?dashStyle.copied_subject_particles:['은','는','이','가','에서','으로'];
  const threshold=Number.isInteger(dashStyle.core_reuse_min_records)?dashStyle.core_reuse_min_records:2;
  const groups=new Map();
  for(const row of dashRows){const core=nw(row.primary).split(/\s+[—–-]\s+/u,1)[0];if(!groups.has(core))groups.set(core,[]);groups.get(core).push(row);}
  const reused=[...groups.entries()].map(([core,members])=>({core,records:members.length,distinct_qualifiers:new Set(members.map(row=>qualifier(row.primary))).size,examples:members.slice(0,3).map(row=>({owner:row.owner,primary:row.primary,text:row.text}))})).filter(group=>group.records>=threshold).sort((a,b)=>b.records-a.records||b.distinct_qualifiers-a.distinct_qualifiers||a.core.localeCompare(b.core));
  const copied=dashRows.filter(row=>{const primary=nw(row.primary),text=nw(row.text);return text.startsWith(primary)&&particles.some(particle=>text.slice(primary.length).startsWith(particle));});
  return {mode:'ADVISORY_WARNING_ONLY',rules_path:path.relative(root,warningRulesPath).split(path.sep).join('/'),rules_sha256:crypto.createHash('sha256').update(warningRulesRaw).digest('hex'),warning_records:new Set(assignments.map(item=>item.owner)).size,warning_assignments:assignments.length,primary_dash_records:dashOwners.size,primary_dash_ratio:rows.length?dashOwners.size/rows.length:0,dash_style_review:{core_reuse_min_records:threshold,copied_subject_particles:particles,text_begins_exact_dash_primary_plus_particle_records:copied.length,text_begins_exact_dash_primary_plus_particle_ratio:rows.length?copied.length/rows.length:0,repeated_core_groups:reused.length,records_in_repeated_core_groups:reused.reduce((n,group)=>n+group.records,0),top_repeated_core_groups:reused.slice(0,20),interpretation:'This is an advisory style signal only; it does not make the structural or token audit fail.'},by_code:summarize(item=>item.code),by_expression:summarize(item=>item.expression||item.code),examples:assignments.slice(0,20).map(item=>({owner:item.owner,primary:item.primary,code:item.code,expression:item.expression,category:item.category,text:item.text})),note:'Warnings collect evidence only; they do not change source or fail structural/token gates.'};
}
let total=0,mins=1e9,maxs=0,all=[],stats=[];
for(const f of files){
  let rows=fs.readFileSync(path.join(src,f),'utf8').trimEnd().split(/\r?\n/).map(x=>JSON.parse(x));
  if(firstOnly) rows=rows.map(r=>({...r,text:r.text.split('.')[0]+'.'}));
  const cs=rows.map(r=>r.text.length),ts=rows.map(r=>count(r.text)+1);
  total+=ts.reduce((a,b)=>a+b,0);mins=Math.min(mins,...ts);maxs=Math.max(maxs,...ts);
  stats.push({f,records:rows.length,tokens:ts.reduce((a,b)=>a+b,0),mean:ts.reduce((a,b)=>a+b,0)/ts.length,min:Math.min(...ts),max:Math.max(...ts),cmin:Math.min(...cs),cmean:cs.reduce((a,b)=>a+b,0)/cs.length,cmax:Math.max(...cs)});
  all.push(...rows.map((row,index)=>({...row,owner:`${f}:${index+1}`})));
}
const means=stats.map(x=>x.mean);
const relation=['is_a','subclass_of','part_of','classification','boundary','contrast','comparison','function','role','process','state','attribute','other'];
let rd={};for(const r of relation)rd[r]=all.reduce((n,x)=>n+(x.relations.includes(r)?1:0),0);
let ng=new Map(),op=new Map();
const words=s=>(s.normalize('NFKC').toLowerCase().match(/[0-9A-Za-z가-힣]+/g)||[]);
for(const r of all){
  let w=words(r.text),seen=new Set();
  for(let i=0;i<=w.length-5;i++){let g=w.slice(i,i+5).join(' ');seen.add(g);}
  for(const g of seen)ng.set(g,(ng.get(g)||0)+1);
  if(w.length>=4){let g=w.slice(0,4).join(' ');op.set(g,(op.get(g)||0)+1);}
}
const rep=[...ng].filter(x=>x[1]>1).sort((a,b)=>b[1]-a[1]),ro=[...op].filter(x=>x[1]>1).sort((a,b)=>b[1]-a[1]);
const serialized=JSON.stringify({files:files.length,rows:all.length,tokenizer:path.relative(root,tokPath),tokenizer_sha256:crypto.createHash('sha256').update(fs.readFileSync(tokPath)).digest('hex'),tokens_plus_eos:total,mean_plus_eos:total/all.length,record_min:mins,record_max:maxs,file_mean_min:Math.min(...means),file_mean_max:Math.max(...means),files_passing:stats.filter(x=>x.mean>=37.4625&&x.mean<=45.7875).length,chars_total:all.reduce((n,r)=>n+r.text.length,0),chars_min:Math.min(...all.map(r=>r.text.length)),chars_mean:all.reduce((n,r)=>n+r.text.length,0)/all.length,chars_max:Math.max(...all.map(r=>r.text.length)),relations:rd,repeat5_types:rep.length,repeat5_assignments:rep.reduce((n,x)=>n+x[1],0),repeat5_top:rep.slice(0,12),repeat4_opening_types:ro.length,repeat4_top:ro.slice(0,8),naturalness_warnings:naturalnessWarnings(all),file_stats:stats},null,2)+'\n';
if(outPath)fs.writeFileSync(path.resolve(outPath),serialized,'utf8');else process.stdout.write(serialized);
