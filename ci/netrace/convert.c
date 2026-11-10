// Netrace -> SAQR study demand traces (docs/SAQR_SPEC_V2.md §24). Built on the Actions runner
// against the downloaded Netrace 1.0 library; the traces are never committed.
//
// Reads region 2 (PARSEC region of interest) of a 64-node trace. The replay window starts
// `start_permille`/1000 of the way into the region. For each time-compression factor f, a packet
// injected `o` native cycles after the window start is written at cycle floor(o / f), for every
// packet with floor(o / f) < 25000 (the study's 5,000 warm-up + 20,000 measured cycles).
// Output format is the frozen demand format: "cycle src dst class" per line, in cycle order.
// Class: 8-byte control packets (requests, acknowledgements, invalidations) -> 0 (critical);
// 72-byte data packets (read/exclusive responses, writebacks) -> 1 (best effort).
// Packet dependencies are not enforced (timestamp replay); every packet is 5 flits in the
// simulator, as in every other study stage.
//
// usage: convert trace.tra.bz2 out_prefix start_permille f1 [f2 ...]
//   writes out_prefix_f<f>.txt for each factor and prints "factor packets critical" per file.
#include <stdio.h>
#include <stdlib.h>
#include "netrace.h"

#define WINDOW 25000ULL
#define MAXF 32

int main(int argc, char** argv) {
    if (argc < 5) { fprintf(stderr, "usage: convert trace out_prefix start_permille f1 [f2 ...]\n"); return 2; }
    int nf = argc - 4;
    if (nf > MAXF) { fprintf(stderr, "too many factors\n"); return 2; }
    unsigned long long f[MAXF], cnt[MAXF] = {0}, crit[MAXF] = {0}, fmax = 0;
    FILE* out[MAXF];
    for (int i = 0; i < nf; ++i) {
        f[i] = strtoull(argv[4 + i], NULL, 10);
        if (f[i] < 1) { fprintf(stderr, "factor must be >= 1\n"); return 2; }
        if (f[i] > fmax) fmax = f[i];
        char name[1024];
        snprintf(name, sizeof name, "%s_f%llu.txt", argv[2], f[i]);
        out[i] = fopen(name, "w");
        if (!out[i]) { perror(name); return 1; }
    }
    nt_open_trfile(argv[1]);
    nt_disable_dependencies();
    nt_header_t* h = nt_get_trheader();
    if (h->num_nodes != 64) { fprintf(stderr, "expected 64 nodes, got %d\n", h->num_nodes); return 1; }
    nt_regionhead_t* roi = &h->regions[2];
    nt_seek_region(roi);
    unsigned long long start = 0, n = 0, base = 0;
    const unsigned long long offset = roi->num_cycles / 1000ULL * strtoull(argv[3], NULL, 10);
    nt_packet_t* p;
    while ((p = nt_read_packet()) != NULL) {
        if (n++ == 0) { base = p->cycle; start = base + offset; }
        if (p->cycle >= start) {
            unsigned long long o = p->cycle - start;
            if (o >= WINDOW * fmax) { nt_packet_free(p); break; }
            int size = nt_get_packet_size(p);
            if (size != 8 && size != 72) { fprintf(stderr, "unexpected packet size %d (type %d)\n", size, p->type); return 1; }
            int cls = size == 8 ? 0 : 1;
            for (int i = 0; i < nf; ++i) {
                unsigned long long t = o / f[i];
                if (t < WINDOW) { fprintf(out[i], "%llu %u %u %d\n", t, p->src, p->dst, cls); ++cnt[i]; crit[i] += cls == 0; }
            }
        }
        nt_packet_free(p);
        if (n >= roi->num_packets) break;
    }
    for (int i = 0; i < nf; ++i) { fclose(out[i]); printf("%llu %llu %llu\n", f[i], cnt[i], crit[i]); }
    nt_close_trfile();
    return 0;
}
