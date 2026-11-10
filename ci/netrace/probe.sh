#!/bin/bash
# Netrace probe (runs on GitHub Actions only): download the Netrace 1.0 library and the three
# smallest PARSEC traces from the authors' site, print the library header and README, and report
# per-trace statistics (regions, packet types and sizes, region-of-interest injection rate).
# Nothing downloaded here is committed to the repository.
set -euo pipefail
OUT=${OUT:-$PWD/netrace_out}; mkdir -p "$OUT" nt && cd nt
BASE=https://www.cs.utexas.edu/~netrace/download
curl -fsSL -o netrace-1.0.tar.bz2 "$BASE/netrace-1.0.tar.bz2"
for t in blackscholes_64c_simsmall fluidanimate_64c_simsmall x264_64c_simsmall; do curl -fsSL -o $t.tra.bz2 "$BASE/$t.tra.bz2"; done
sha256sum *.bz2 | tee "$OUT/sha256.txt"; ls -la | tee -a "$OUT/sha256.txt"
tar xjf netrace-1.0.tar.bz2; find . -maxdepth 3 -type f | grep -v '\.tra\.bz2$' | tee "$OUT/files.txt"
src=$(dirname "$(find . -name netrace.h | head -1)")
cp "$src/netrace.h" "$OUT/"; cp "$src"/README* "$OUT/" 2>/dev/null || true; cp "$src/netrace.c" "$OUT/"
cat > stats.c <<'C'
#include <stdio.h>
#include <stdlib.h>
#include "netrace.h"
int main(int argc,char** argv){
    nt_open_trfile(argv[1]);
    nt_disable_dependencies();
    nt_header_t* h=nt_get_trheader();
    nt_print_trheader();
    long long cnt[64]={0}, sz[256]={0}, n=0, src[64]={0}, dst[64]={0}, st[8]={0}, dt[8]={0};
    unsigned long long first=0,last=0;
    nt_seek_region(&h->regions[2]);
    nt_packet_t* p;
    while((p=nt_read_packet())!=NULL){
        if(n==0) first=p->cycle; last=p->cycle; ++n;
        if(p->type<64) cnt[p->type]++;
        int s=nt_get_packet_size(p); if(s>=0&&s<256) sz[s]++;
        if(p->src<64) src[p->src]++; if(p->dst<64) dst[p->dst]++;
        int a=nt_get_src_type(p), b=nt_get_dst_type(p); if(a>=0&&a<8) st[a]++; if(b>=0&&b<8) dt[b]++;
        nt_packet_free(p);
        if(n>=h->regions[2].num_packets) break;
    }
    printf("ROI packets read %lld of %llu, cycles %llu..%llu (span %llu, region cycles %llu)
",n,h->regions[2].num_packets,first,last,last-first,h->regions[2].num_cycles);
    for(int i=0;i<64;++i) if(cnt[i]) printf("type %d %s: %lld
",i,nt_packet_types[i],cnt[i]);
    for(int i=0;i<256;++i) if(sz[i]) printf("size %d B: %lld
",i,sz[i]);
    for(int i=0;i<4;++i) printf("src type %s: %lld   dst type: %lld
",nt_node_type_to_string(i),st[i],dt[i]);
    printf("src:"); for(int i=0;i<64;++i) printf(" %lld",src[i]); printf("
dst:"); for(int i=0;i<64;++i) printf(" %lld",dst[i]); printf("
");
    nt_close_trfile(); return 0;
}
C
gcc -O2 -I"$src" stats.c "$src/netrace.c" -o stats 2> "$OUT/stats_build.log" || { cat "$OUT/stats_build.log"; exit 1; }
for t in blackscholes_64c_simsmall fluidanimate_64c_simsmall x264_64c_simsmall; do echo "== $t"; ./stats $t.tra.bz2; done 2>&1 | tee "$OUT/stats.txt"
