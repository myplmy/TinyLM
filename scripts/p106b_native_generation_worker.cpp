// Reuse only the archived wire/Reader/clock helpers, without editing Core6.
// Neither its GPU-only Runtime nor its old main is invoked by this program.
#define main archived_core6_main_not_called
#include "p106b_native_llama_worker.cpp"
#undef main
#include <functional>

namespace {
double steady_seconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
llama_token pick(const float * row, int count) {
    if (!row || count < 2) throw std::runtime_error("missing generation logits");
    llama_token result=0;
    for(int i=0;i<count;++i) {
        if(!std::isfinite(row[i]))throw std::runtime_error("nonfinite generation logit");
        if(row[i]>row[result])result=i;
    }
    return result;
}
struct GenerationRuntime {
    llama_model * model=nullptr;
    llama_context * ctx=nullptr;
    const llama_vocab * vocab=nullptr;
    ggml_backend_dev_t devices[2]={nullptr,nullptr};
    bool cuda=false;
    int size=0;
    uint32_t prefill_chunk=512;
    uint64_t clears=0,decodes=0,copies=0;
    explicit GenerationRuntime(const std::string & path,const std::string & device) {
        try {
            deadline();cuda=device=="cuda";
            ggml_backend_load_all_from_path(ENGINE);llama_backend_init();
            auto mp=llama_model_default_params();
            if(cuda) {
                devices[0]=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
                if(!devices[0])throw std::runtime_error("CUDA requested; native GPU backend absent");
            }
            mp.devices=devices;mp.n_gpu_layers=cuda?-1:0;
            mp.split_mode=LLAMA_SPLIT_MODE_NONE;mp.use_extra_bufts=false;
            mp.load_mtp=false;mp.check_tensors=true;mp.progress_callback=progress;
            model=llama_model_load_from_file(path.c_str(),mp);
            if(!model)throw std::runtime_error("native generation model load failed");
            char arch[128];
            if(llama_model_meta_val_str(model,"general.architecture",arch,sizeof arch)<0 || std::string(arch)!="gpt2")
                throw std::runtime_error("exact GPT2 architecture required");
            vocab=llama_model_get_vocab(model);size=llama_vocab_n_tokens(vocab);
            if(size!=50257 || llama_model_n_ctx_train(model)!=1024 || llama_vocab_eos(vocab)!=50256)
                throw std::runtime_error("GPT2 vocabulary/context/EOS differs");
            auto cp=llama_context_default_params();
            cp.n_ctx=1024;cp.n_batch=512;cp.n_ubatch=512;cp.n_seq_max=1;
            cp.n_outputs_max=1;cp.n_outputs_max_per_seq=1;cp.n_rs_seq=0;
            cp.n_threads=cuda?2:1;cp.n_threads_batch=cuda?2:1;
            cp.attention_type=LLAMA_ATTENTION_TYPE_CAUSAL;
            cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
            cp.type_k=GGML_TYPE_F32;cp.type_v=GGML_TYPE_F32;
            cp.no_perf=false;cp.embeddings=false;cp.samplers=nullptr;cp.n_samplers=0;
            cp.offload_kqv=cuda;cp.op_offload=cuda;
            ctx=llama_init_from_model(model,cp);
            if(!ctx || llama_n_ctx_seq(ctx)!=1024 || llama_n_batch(ctx)!=512 || llama_n_ubatch(ctx)!=512)
                throw std::runtime_error("exact generation context/batch required");
            clear();deadline();
        } catch(...) {release();throw;}
    }
    ~GenerationRuntime(){release();}
    void release(){if(ctx){llama_free(ctx);ctx=nullptr;}if(model){llama_model_free(model);model=nullptr;}}
    void clear(){if(ctx){llama_memory_clear(llama_get_memory(ctx),true);llama_synchronize(ctx);++clears;}}
    void ids(const std::vector<llama_token> & values,bool empty=false) {
        if(values.empty()&&!empty)throw std::runtime_error("empty generation input");
        for(auto v:values)if(v<0 || v>=size)throw std::runtime_error("generation ID out of vocabulary");
    }
    void decode(const std::vector<llama_token> & tokens,int start) {
        ids(tokens);
        if(tokens.size()>512 || start<0 || size_t(start)+tokens.size()>1024)
            throw std::runtime_error("native generation context bound");
        auto batch=llama_batch_init(int(tokens.size()),0,1);
        try {
            batch.n_tokens=int(tokens.size());
            for(size_t i=0;i<tokens.size();++i) {
                batch.token[i]=tokens[i];batch.pos[i]=start+int(i);
                batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;
                batch.logits[i]=i+1==tokens.size();
            }
            deadline();int rc=llama_decode(ctx,batch);++decodes;llama_synchronize(ctx);deadline();
            if(rc!=0)throw std::runtime_error("generation llama_decode returned "+std::to_string(rc));
            if(llama_memory_seq_pos_max(llama_get_memory(ctx),0)!=start+int(tokens.size())-1)
                throw std::runtime_error("native KV position differs");
        }catch(...){llama_batch_free(batch);throw;}
        llama_batch_free(batch);
    }
    void prefix_decode(const std::vector<llama_token> & tokens) {
        ids(tokens);
        for(size_t start=0;start<tokens.size();start+=prefill_chunk) {
            size_t end=std::min(tokens.size(),start+prefill_chunk);
            decode(std::vector<llama_token>(tokens.begin()+start,tokens.begin()+end),int(start));
        }
    }
    Bytes info() {
        Bytes out;
        for(auto n:{size,llama_model_n_ctx_train(model),int(llama_n_ctx_seq(ctx)),int(llama_n_batch(ctx)),
                    int(llama_n_ubatch(ctx)),llama_vocab_bos(vocab),llama_vocab_eos(vocab)})u32(out,uint32_t(n));
        u32(out,llama_vocab_get_add_bos(vocab));u32(out,llama_vocab_get_add_eos(vocab));u32(out,uint32_t(llama_vocab_type(vocab)));
        u64(out,llama_model_n_params(model));u64(out,llama_model_size(model));
        text(out,"gpt2");text(out,cuda?ggml_backend_dev_name(devices[0]):"CPU_OFFLOAD0");
        for(auto key:{"tokenizer.ggml.model","tokenizer.ggml.pre"}) {
            char value[1024];int n=llama_model_meta_val_str(model,key,value,sizeof value);
            if(n>=int(sizeof value))throw std::runtime_error("native metadata too long");
            text(out,n<0?"<ABSENT>":std::string(value));
        }
        return out;
    }
    Bytes command(uint32_t op,Reader & in,const std::function<void(const Bytes &)> & event) {
        deadline();Bytes out;
        if(op==2) {
            auto flags=in.number();if(flags>3)throw std::runtime_error("invalid tokenizer flags");
            auto content=in.string();in.end();
            int n=llama_tokenize(vocab,content.data(),int(content.size()),nullptr,0,flags&1,flags&2);
            if(n==std::numeric_limits<int>::min())throw std::runtime_error("tokenizer overflow");
            std::vector<llama_token> values(size_t(n<0?-n:n));
            int actual=llama_tokenize(vocab,content.data(),int(content.size()),values.data(),int(values.size()),flags&1,flags&2);
            if(actual<0 || size_t(actual)!=values.size())throw std::runtime_error("tokenizer size differs");
            ids(values,true);u32(out,uint32_t(values.size()));for(auto v:values)u32(out,uint32_t(v));
        } else if(op==5) {
            auto values=in.tokens(1000000);in.end();ids(values,true);
            int n=llama_detokenize(vocab,values.data(),int(values.size()),nullptr,0,false,true);
            if(n==std::numeric_limits<int>::min())throw std::runtime_error("detokenizer overflow");
            std::string content(size_t(n<0?-n:n),'\0');
            int actual=llama_detokenize(vocab,values.data(),int(values.size()),content.data(),int(content.size()),false,true);
            if(actual<0 || size_t(actual)!=content.size())throw std::runtime_error("detokenizer size differs");
            text(out,content);
        } else if(op==7) {
            auto prefix=in.tokens(512);auto cap=in.number(),flags=in.number();in.end();ids(prefix);
            if(cap<1 || cap>128 || flags>3 || prefix.size()+cap>1024)throw std::runtime_error("generation bound/flags differ");
            const bool natural=flags&1,observed=flags&2;double began=steady_seconds();
            clear();prefix_decode(prefix);std::vector<llama_token> generated;double first=0;
            try {
                for(uint32_t i=0;i<cap;++i) {
                    // -1 addresses the last requested output, including bulk prefill.
                    deadline();auto token=pick(llama_get_logits_ith(ctx,-1),size);generated.push_back(token);
                    double stamp=observed?steady_seconds()-began:0;
                    if(i==0)first=steady_seconds()-began;
                    if(observed){Bytes e;u32(e,i);u32(e,uint32_t(token));f64(e,stamp);event(e);}
                    if((natural&&llama_vocab_is_eog(vocab,token)) || i+1==cap)break;
                    decode({token},int(prefix.size()+i));
                }
                int final_pos=llama_memory_seq_pos_max(llama_get_memory(ctx),0);
                if(final_pos!=int(prefix.size()+generated.size())-2)throw std::runtime_error("final generation KV position differs");
                u32(out,uint32_t(generated.size()));for(auto v:generated)u32(out,uint32_t(v));
                u32(out,natural&&llama_vocab_is_eog(vocab,generated.back())?1:0);u32(out,uint32_t(final_pos));
                f64(out,first);clear();f64(out,steady_seconds()-began);
            }catch(...){clear();throw;}
        } else if(op==8 || op==9) {
            auto prefix=in.tokens(512);ids(prefix);
            auto tail=op==9?in.tokens(4):std::vector<llama_token>{};in.end();ids(tail,true);
            if(prefix.size()+tail.size()>512)throw std::runtime_error("numeric prefix bound");
            clear();
            try {
                prefix_decode(prefix);u32(out,uint32_t(tail.size()+1));u32(out,uint32_t(size));
                for(size_t i=0;i<=tail.size();++i) {
                    auto row=llama_get_logits_ith(ctx,-1);pick(row,size);
                    for(int j=0;j<size;++j){f32(out,row[j]);}
                    ++copies;
                    if(i<tail.size())decode({tail[i]},int(prefix.size()+i));
                }
                clear();
            }catch(...){clear();throw;}
        } else if(op==10) {
            auto value=in.number();in.end();
            if(value!=1 && value!=32 && value!=512)throw std::runtime_error("unregistered prefill chunk");
            clear();prefill_chunk=value;u32(out,prefill_chunk);
        } else throw std::runtime_error("unknown generation operation");
        deadline();return out;
    }
};
}

int main(int argc,char ** argv) {
    if(argc==2 && std::string(argv[1])=="--self-test") {
        float values[]={-3,2,2};if(pick(values,3)!=1)return 8;
        Bytes b;u32(b,42);Reader r{b};if(r.number()!=42)return 8;r.end();
        std::cout<<"CPU_WIRE_ONLY; backend_init=0; model_loads=0\n";return 0;
    }
    if(argc!=5 || std::string(argv[1])!="--execute") {
        std::cerr<<"explicit --execute EXACT_GPT2_PATH cpu|cuda DEADLINE_EPOCH required\n";return 8;
    }
    try {
        const std::string allowed="/home/uranus/tinyLM/HF/benchmark_20261023/gpt2_q4km/gpt2-q4_k_m.gguf";
        const std::string device=argv[3];stop_epoch=std::stod(argv[4]);
        if(argv[2]!=allowed || (device!="cpu"&&device!="cuda") || !std::isfinite(stop_epoch)
           || stop_epoch>1793088000)throw std::runtime_error("exact asset/device/27Oct17KST authority required");
        deadline();GenerationRuntime runtime(argv[2],device);Bytes request;
        while(frame(request)) {
            Reader in{request};auto op=in.number(),id=in.number();
            try {
                if(op==1){in.end();reply(op,id,0,runtime.info());}
                else if(op==6){in.end();Bytes out;u64(out,runtime.clears);u64(out,runtime.decodes);u64(out,runtime.copies);reply(op,id,0,out);break;}
                else reply(op,id,0,runtime.command(op,in,[&](const Bytes & event){reply(op,id,2,event);}));
            }catch(const std::exception & e){runtime.clear();Bytes out;text(out,e.what());reply(op,id,1,out);return 9;}
        }
        return 0;
    }catch(const std::exception & e){std::cerr<<"native generation error: "<<e.what()<<"\n";return 9;}
}
