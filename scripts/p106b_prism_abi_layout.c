/* ABI layout probe from pinned adfffbe declarations; no external library. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
typedef void * ggml_backend_dev_t;
typedef bool (*llama_progress_callback)(float, void *);
typedef bool (*ggml_backend_sched_eval_callback)(void *, bool, void *);
typedef bool (*ggml_abort_callback)(void *);
typedef int32_t llama_token;
typedef int32_t llama_pos;
typedef int32_t llama_seq_id;
enum llama_split_mode { SPLIT_PROBE_ZERO = 0 };
enum llama_load_mode { LOAD_PROBE_NEG = -1, LOAD_PROBE_FOUR = 4 };
enum llama_context_type { CONTEXT_PROBE_ZERO = 0 };
enum llama_rope_scaling_type { ROPE_PROBE_NEG = -1 };
enum llama_pooling_type { POOL_PROBE_NEG = -1 };
enum llama_attention_type { ATTENTION_PROBE_NEG = -1 };
enum llama_flash_attn_type { FLASH_PROBE_NEG = -1, FLASH_PROBE_ONE = 1 };
enum ggml_type { GGML_PROBE_ZERO = 0 };
struct llama_model_params {
        // Opt-in DSpark head borrowing. Caller guarantees the bound target and keeps it alive
        // until the drafter and all drafter contexts are destroyed. No head weights are copied.
        const struct llama_model * dspark_head_source;

        // NULL-terminated list of devices to use for offloading (if NULL, all available devices are used)
        ggml_backend_dev_t * devices;

        // NULL-terminated list of buffer types to use for tensors that match a pattern
        const struct llama_model_tensor_buft_override * tensor_buft_overrides;

        int32_t n_gpu_layers; // number of layers to store in VRAM, a negative value means all layers
        enum llama_split_mode split_mode; // how to split the model across multiple GPUs
        enum llama_load_mode  load_mode;  // how to load the model

        // the GPU that is used for the entire model when split_mode is LLAMA_SPLIT_MODE_NONE
        int32_t main_gpu;

        // proportion of the model (layers or rows) to offload to each GPU, size: llama_max_devices()
        const float * tensor_split;

        // Called with a progress value between 0.0 and 1.0. Pass NULL to disable.
        // If the provided progress_callback returns true, model loading continues.
        // If it returns false, model loading is immediately aborted.
        llama_progress_callback progress_callback;

        // context pointer passed to the progress callback
        void * progress_callback_user_data;

        // override key-value pairs of the model meta data
        const struct llama_model_kv_override * kv_overrides;

        // Keep the booleans together to avoid misalignment during copy-by-value.
        bool vocab_only;      // only load the vocabulary, no weights
        bool check_tensors;   // validate model tensor data
        bool use_extra_bufts; // use extra buffer types (used for weight repacking)
        bool no_host;         // bypass host buffer allowing extra buffers to be used
        bool no_alloc;        // only load metadata and simulate memory allocations
        bool load_mtp;        // whether to load MTP layers
    };

struct llama_context_params {
        uint32_t n_ctx;                 // text context, 0 = from model
        uint32_t n_batch;               // logical maximum batch size that can be submitted to llama_decode
        uint32_t n_ubatch;              // physical maximum batch size
        uint32_t n_seq_max;             // max number of sequences (i.e. distinct states for recurrent models)
        uint32_t n_rs_seq;              // number of recurrent-state snapshots per seq for rollback (0 = no rollback) [EXPERIMENTAL]
        uint32_t n_outputs_max;         // max outputs in a ubatch (0 = n_batch)
        uint32_t n_outputs_max_per_seq; // max outputs per sequence (0 = n_outputs_max)
        int32_t  n_threads;             // number of threads to use for generation
        int32_t  n_threads_batch;       // number of threads to use for batch processing

        enum llama_context_type      ctx_type;          // set the context type (e.g. MTP)
        enum llama_rope_scaling_type rope_scaling_type; // RoPE scaling type, from `enum llama_rope_scaling_type`
        enum llama_pooling_type      pooling_type;      // whether to pool (sum) embedding results by sequence id
        enum llama_attention_type    attention_type;    // attention type to use for embeddings
        enum llama_flash_attn_type   flash_attn_type;   // when to enable Flash Attention

        // ref: https://github.com/ggml-org/llama.cpp/pull/2054
        float    rope_freq_base;   // RoPE base frequency, 0 = from model
        float    rope_freq_scale;  // RoPE frequency scaling factor, 0 = from model
        float    yarn_ext_factor;  // YaRN extrapolation mix factor, negative = from model
        float    yarn_attn_factor; // YaRN magnitude scaling factor
        float    yarn_beta_fast;   // YaRN low correction dim
        float    yarn_beta_slow;   // YaRN high correction dim
        uint32_t yarn_orig_ctx;    // YaRN original context size
        float    defrag_thold;     // [DEPRECATED] defragment the KV cache if holes/size > thold, <= 0 disabled (default)

        ggml_backend_sched_eval_callback cb_eval;
        void * cb_eval_user_data;

        enum ggml_type type_k; // data type for K cache [EXPERIMENTAL]
        enum ggml_type type_v; // data type for V cache [EXPERIMENTAL]

        // optional path to a per-layer K-cache mean-centering bias file (GGUF), or NULL to disable.
        // the bias is subtracted from the K vector for each (kv-head, channel) right before it is
        // written into the K cache, which improves quantization fidelity for GGML_TYPE_Q4_0 without
        // changing attention results (the same constant is added to every logit in a query's row,
        // which softmax is invariant to). currently only supported when type_k == GGML_TYPE_Q4_0.
        // see tools/kv-mean-center to generate this file and docs/kv-mean-center.md for details.
        const char * path_kv_mean_center;

        // Abort callback
        // if it returns true, execution of llama_decode() will be aborted
        // currently works only with CPU execution
        ggml_abort_callback abort_callback;
        void *              abort_callback_data;

        // Keep the booleans together and at the end of the struct to avoid misalignment during copy-by-value.
        bool embeddings;  // if true, extract embeddings (together with logits)
        bool offload_kqv; // offload the KQV ops (including the KV cache) to GPU
        bool no_perf;     // measure performance timings
        bool op_offload;  // offload host tensor operations to device
        bool swa_full;    // use full-size SWA cache (https://github.com/ggml-org/llama.cpp/pull/13194#issuecomment-2868343055)
                          // NOTE: setting to false when n_seq_max > 1 can cause bad performance in some cases
                          //       ref: https://github.com/ggml-org/llama.cpp/pull/13845#issuecomment-2924800573
        bool kv_unified;  // use a unified buffer across the input sequences when computing the attention
                          // try to disable when n_seq_max > 1 for improved performance when the sequences do not share a large prefix
                          // ref: https://github.com/ggml-org/llama.cpp/pull/14363

        // [EXPERIMENTAL]
        // backend sampler chain configuration (make sure the caller keeps the sampler chains alive)
        // note: the samplers must be sampler chains (i.e. use llama_sampler_chain_init)
        struct llama_sampler_seq_config * samplers;
        size_t                            n_samplers;

        // a source/target/parent context
        // can be utilized in various ways, for example by sharing results or llama_memory between 2 contexts
        struct llama_context * ctx_other;
    };

typedef struct llama_batch {
        int32_t n_tokens;

        llama_token  *  token;
        float        *  embd;
        llama_pos    *  pos;
        int32_t      *  n_seq_id;
        llama_seq_id ** seq_id;
        int8_t       *  logits;   // TODO: rename this to "output"
    } llama_batch;
int main(void) {
    printf("STRUCT model %zu %zu\n", sizeof(struct llama_model_params), _Alignof(struct llama_model_params));
    printf("FIELD model dspark_head_source %zu\n", offsetof(struct llama_model_params, dspark_head_source));
    printf("FIELD model devices %zu\n", offsetof(struct llama_model_params, devices));
    printf("FIELD model tensor_buft_overrides %zu\n", offsetof(struct llama_model_params, tensor_buft_overrides));
    printf("FIELD model n_gpu_layers %zu\n", offsetof(struct llama_model_params, n_gpu_layers));
    printf("FIELD model split_mode %zu\n", offsetof(struct llama_model_params, split_mode));
    printf("FIELD model load_mode %zu\n", offsetof(struct llama_model_params, load_mode));
    printf("FIELD model main_gpu %zu\n", offsetof(struct llama_model_params, main_gpu));
    printf("FIELD model tensor_split %zu\n", offsetof(struct llama_model_params, tensor_split));
    printf("FIELD model progress_callback %zu\n", offsetof(struct llama_model_params, progress_callback));
    printf("FIELD model progress_callback_user_data %zu\n", offsetof(struct llama_model_params, progress_callback_user_data));
    printf("FIELD model kv_overrides %zu\n", offsetof(struct llama_model_params, kv_overrides));
    printf("FIELD model vocab_only %zu\n", offsetof(struct llama_model_params, vocab_only));
    printf("FIELD model check_tensors %zu\n", offsetof(struct llama_model_params, check_tensors));
    printf("FIELD model use_extra_bufts %zu\n", offsetof(struct llama_model_params, use_extra_bufts));
    printf("FIELD model no_host %zu\n", offsetof(struct llama_model_params, no_host));
    printf("FIELD model no_alloc %zu\n", offsetof(struct llama_model_params, no_alloc));
    printf("FIELD model load_mtp %zu\n", offsetof(struct llama_model_params, load_mtp));
    printf("STRUCT context %zu %zu\n", sizeof(struct llama_context_params), _Alignof(struct llama_context_params));
    printf("FIELD context n_ctx %zu\n", offsetof(struct llama_context_params, n_ctx));
    printf("FIELD context n_batch %zu\n", offsetof(struct llama_context_params, n_batch));
    printf("FIELD context n_ubatch %zu\n", offsetof(struct llama_context_params, n_ubatch));
    printf("FIELD context n_seq_max %zu\n", offsetof(struct llama_context_params, n_seq_max));
    printf("FIELD context n_rs_seq %zu\n", offsetof(struct llama_context_params, n_rs_seq));
    printf("FIELD context n_outputs_max %zu\n", offsetof(struct llama_context_params, n_outputs_max));
    printf("FIELD context n_outputs_max_per_seq %zu\n", offsetof(struct llama_context_params, n_outputs_max_per_seq));
    printf("FIELD context n_threads %zu\n", offsetof(struct llama_context_params, n_threads));
    printf("FIELD context n_threads_batch %zu\n", offsetof(struct llama_context_params, n_threads_batch));
    printf("FIELD context ctx_type %zu\n", offsetof(struct llama_context_params, ctx_type));
    printf("FIELD context rope_scaling_type %zu\n", offsetof(struct llama_context_params, rope_scaling_type));
    printf("FIELD context pooling_type %zu\n", offsetof(struct llama_context_params, pooling_type));
    printf("FIELD context attention_type %zu\n", offsetof(struct llama_context_params, attention_type));
    printf("FIELD context flash_attn_type %zu\n", offsetof(struct llama_context_params, flash_attn_type));
    printf("FIELD context rope_freq_base %zu\n", offsetof(struct llama_context_params, rope_freq_base));
    printf("FIELD context rope_freq_scale %zu\n", offsetof(struct llama_context_params, rope_freq_scale));
    printf("FIELD context yarn_ext_factor %zu\n", offsetof(struct llama_context_params, yarn_ext_factor));
    printf("FIELD context yarn_attn_factor %zu\n", offsetof(struct llama_context_params, yarn_attn_factor));
    printf("FIELD context yarn_beta_fast %zu\n", offsetof(struct llama_context_params, yarn_beta_fast));
    printf("FIELD context yarn_beta_slow %zu\n", offsetof(struct llama_context_params, yarn_beta_slow));
    printf("FIELD context yarn_orig_ctx %zu\n", offsetof(struct llama_context_params, yarn_orig_ctx));
    printf("FIELD context defrag_thold %zu\n", offsetof(struct llama_context_params, defrag_thold));
    printf("FIELD context cb_eval %zu\n", offsetof(struct llama_context_params, cb_eval));
    printf("FIELD context cb_eval_user_data %zu\n", offsetof(struct llama_context_params, cb_eval_user_data));
    printf("FIELD context type_k %zu\n", offsetof(struct llama_context_params, type_k));
    printf("FIELD context type_v %zu\n", offsetof(struct llama_context_params, type_v));
    printf("FIELD context path_kv_mean_center %zu\n", offsetof(struct llama_context_params, path_kv_mean_center));
    printf("FIELD context abort_callback %zu\n", offsetof(struct llama_context_params, abort_callback));
    printf("FIELD context abort_callback_data %zu\n", offsetof(struct llama_context_params, abort_callback_data));
    printf("FIELD context embeddings %zu\n", offsetof(struct llama_context_params, embeddings));
    printf("FIELD context offload_kqv %zu\n", offsetof(struct llama_context_params, offload_kqv));
    printf("FIELD context no_perf %zu\n", offsetof(struct llama_context_params, no_perf));
    printf("FIELD context op_offload %zu\n", offsetof(struct llama_context_params, op_offload));
    printf("FIELD context swa_full %zu\n", offsetof(struct llama_context_params, swa_full));
    printf("FIELD context kv_unified %zu\n", offsetof(struct llama_context_params, kv_unified));
    printf("FIELD context samplers %zu\n", offsetof(struct llama_context_params, samplers));
    printf("FIELD context n_samplers %zu\n", offsetof(struct llama_context_params, n_samplers));
    printf("FIELD context ctx_other %zu\n", offsetof(struct llama_context_params, ctx_other));
    printf("STRUCT batch %zu %zu\n", sizeof(struct llama_batch), _Alignof(struct llama_batch));
    printf("FIELD batch n_tokens %zu\n", offsetof(struct llama_batch, n_tokens));
    printf("FIELD batch token %zu\n", offsetof(struct llama_batch, token));
    printf("FIELD batch embd %zu\n", offsetof(struct llama_batch, embd));
    printf("FIELD batch pos %zu\n", offsetof(struct llama_batch, pos));
    printf("FIELD batch n_seq_id %zu\n", offsetof(struct llama_batch, n_seq_id));
    printf("FIELD batch seq_id %zu\n", offsetof(struct llama_batch, seq_id));
    printf("FIELD batch logits %zu\n", offsetof(struct llama_batch, logits));
    return 0;
}

