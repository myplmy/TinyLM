// Run the compact G270 engine and exec the decoder in the same process.
#include <cstdio>
#include <cstdlib>
#include <unistd.h>

int run_compact_g4(int argc, char** argv);

int main(int argc, char** argv) {
    if (argc != 10) {
        fprintf(stderr, "g270 text exec: invalid arguments\n");
        return 2;
    }
    const int model_fd = atoi(argv[1]);
    const int original_stdout = atoi(argv[2]);
    if (model_fd < 3 || original_stdout < 3 || model_fd == original_stdout) return 2;
    char no_logits[] = "-1";
    char* args[] = {argv[0], argv[1], no_logits, nullptr};
    printf("{\"pid\":%ld,\"native\":", static_cast<long>(getpid()));
    const int status = run_compact_g4(3, args);
    if (status != 0) return status;
    printf("}\n");
    if (fflush(stdout) != 0 || dup2(original_stdout, STDOUT_FILENO) < 0) {
        perror("g270 text exec: result stream");
        return 1;
    }
    close(original_stdout);
    close(model_fd);

    char isolated[] = "-I", no_site[] = "-S", no_cache[] = "-B", flag[] = "-X", utf8[] = "utf8";
    char decode[] = "decode";
    char* decoder[] = {argv[3], isolated, no_site, no_cache, flag, utf8, argv[4], decode,
                      argv[5], argv[6], argv[7], argv[8], argv[9], nullptr};
    execv(argv[3], decoder);
    perror("g270 text exec: decoder");
    return 1;
}
