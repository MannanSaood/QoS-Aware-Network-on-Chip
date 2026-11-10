// Netrace -> SAQR study demand traces (docs/SAQR_SPEC_V2.md §24). Built on the Actions runner
// against the downloaded Netrace 1.0 library; the traces are never committed.
//
// Reads region 2 (PARSEC region of interest) of a 64-node trace. One replay window per benchmark:
// it starts `start_permille`/1000 of the way into the region and spans 25000 * F native cycles,
// time-compressed by F into the study's 25,000 cycles (5,000 warm-up + 20,000 measured): a packet
// injected `o` native cycles after the window start is written at cycle floor(o / F).
// Load points: the same window, keeping a fixed subset of its packets, packet id hashed
// (Knuth multiplicative) into 0..999 and kept when below the keep fraction in permille. Every load
// point therefore has the same phases and spatial pattern; lower points are sparser.
// Output format is the frozen demand format: "cycle src dst class" per line, in cycle order.
// Class: 8-byte control packets (requests, acknowledgements, invalidations) -> 0 (critical);
// 72-byte data packets (read/exclusive responses, writebacks) -> 1 (best effort).
// Packet dependencies are not enforced (timestamp replay); every packet is 5 flits in the
// simulator, as in every other study stage.
//
// usage: convert trace.tra.bz2 out_prefix start_permille F keep1 [keep2 ...]   (keep in permille)
//   writes out_prefix_q<keep>.txt for each keep fraction and prints "keep packets critical" per file.
#include <stdio.h>
#include <stdlib.h>
#include "netrace.h"

#define WINDOW 25000ULL
#define MAXF 32

int main(int argc, char** argv) {
    if (argc < 6) { fprintf(stderr, "usage: convert trace out_prefix start_permille F keep1 [keep2 ...]
"); return 2; }
    const unsigned long long F = strtoull(argv[4], NULL, 10);
    int nq = argc - 5;
    if (F < 1 || nq > MAXF) { fprintf(stderr, "bad arguments
"); return 2; }
    unsigned q[MAXF]; unsigned long long cnt[MAXF] = {0}, crit[MAXF] = {0};
    FILE* out[MAXF];
    for (int i = 0; i < nq; ++i) {
        q[i] = (unsigned)strtoul(argv[5 + i], NULL, 10);
        if (q[i] < 1 || q[i] > 1000) { fprintf(stderr, "keep must be 1..1000
"); return 2; }
        char name[1024];
        snprintf(name, sizeof name, "%s_q%u.txt", argv[2], q[i]);
        out[i] = fopen(name, "w");
        if (!out[i]) { perror(name); return 1; }
    }
    nt_open_trfile(argv[1]);
    nt_disable_dependencies();
    nt_header_t* h = nt_get_trheader();
    if (h->num_nodes != 64) { fprintf(stderr, "expected 64 nodes, got %d
", h->num_nodes); return 1; }
    nt_regionhead_t* roi = &h->regions[2];
    nt_seek_region(roi);
    unsigned long long start = 0, n = 0;
    const unsigned long long offset = roi->num_cycles / 1000ULL * strtoull(argv[3], NULL, 10);
    nt_packet_t* p;
    while ((p = nt_read_packet()) != NULL) {
        if (n++ == 0) start = p->cycle + offset;
        if (p->cycle >= start) {
            unsigned long long t = (p->cycle - start) / F;
            if (t >= WINDOW) { nt_packet_free(p); break; }
            int size = nt_get_packet_size(p);
            if (size != 8 && size != 72) { fprintf(stderr, "unexpected packet size %d (type %d)
", size, p->type); return 1; }
            int cls = size == 8 ? 0 : 1;
            unsigned bucket = (unsigned)(((unsigned long long)p->id * 2654435761ULL) % 1000ULL);
            for (int i = 0; i < nq; ++i)
                if (bucket < q[i]) { fprintf(out[i], "%llu %u %u %d
", t, p->src, p->dst, cls); ++cnt[i]; crit[i] += cls == 0; }
        }
        nt_packet_free(p);
        if (n >= roi->num_packets) break;
    }
    for (int i = 0; i < nq; ++i) { fclose(out[i]); printf("%u %llu %llu
", q[i], cnt[i], crit[i]); }
    nt_close_trfile();
    return 0;
}
