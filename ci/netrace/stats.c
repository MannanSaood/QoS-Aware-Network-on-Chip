// Netrace trace statistics for the region of interest (region 2). Built on the Actions runner
// against the downloaded Netrace 1.0 library; see ci/netrace/probe.sh.
#include <stdio.h>
#include <stdlib.h>
#include "netrace.h"

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: stats trace.tra.bz2\n"); return 2; }
    nt_open_trfile(argv[1]);
    nt_disable_dependencies();
    nt_header_t* h = nt_get_trheader();
    nt_print_trheader();
    long long cnt[64] = {0}, sz[256] = {0}, n = 0, src[64] = {0}, dst[64] = {0}, st[8] = {0}, dt[8] = {0};
    unsigned long long first = 0, last = 0;
    nt_seek_region(&h->regions[2]);
    nt_packet_t* p;
    while ((p = nt_read_packet()) != NULL) {
        if (n == 0) first = p->cycle;
        last = p->cycle; ++n;
        if (p->type < 64) cnt[p->type]++;
        int s = nt_get_packet_size(p);
        if (s >= 0 && s < 256) sz[s]++;
        if (p->src < 64) src[p->src]++;
        if (p->dst < 64) dst[p->dst]++;
        int a = nt_get_src_type(p), b = nt_get_dst_type(p);
        if (a >= 0 && a < 8) st[a]++;
        if (b >= 0 && b < 8) dt[b]++;
        nt_packet_free(p);
        if ((unsigned long long)n >= h->regions[2].num_packets) break;
    }
    printf("ROI packets read %lld of %llu, cycles %llu..%llu (span %llu, region cycles %llu)\n",
           n, h->regions[2].num_packets, first, last, last - first, h->regions[2].num_cycles);
    for (int i = 0; i < 64; ++i) if (cnt[i]) printf("type %d %s: %lld\n", i, nt_packet_types[i], cnt[i]);
    for (int i = 0; i < 256; ++i) if (sz[i]) printf("size %d B: %lld\n", i, sz[i]);
    for (int i = 0; i < 4; ++i) printf("src type %s: %lld   dst type: %lld\n", nt_node_type_to_string(i), st[i], dt[i]);
    printf("src:"); for (int i = 0; i < 64; ++i) printf(" %lld", src[i]);
    printf("\ndst:"); for (int i = 0; i < 64; ++i) printf(" %lld", dst[i]);
    printf("\n");
    nt_close_trfile();
    return 0;
}
