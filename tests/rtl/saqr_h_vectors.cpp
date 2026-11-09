// Writes test vectors for rtl/saqr/saqr_h_classifier.sv from the C++ model
// (algorithms/saqr_hot/routing.hpp, the code the simulator runs).
// Output lines: "<dest> <expected mark>". Streams mix uniform, hotspot (20 %),
// fixed-destination, small-flow-set and adversarial (alternating) phases.
// Build: g++ -std=c++17 -O2 tests/rtl/saqr_h_vectors.cpp -o saqr_h_vectors
//        ./saqr_h_vectors <hot_en 0|1> <out file>
#include "../../algorithms/saqr_hot/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>

int main(int argc,char** argv) {
    if(argc<3) { std::fprintf(stderr,"usage: %s hot_en out\n",argv[0]); return 2; }
    const bool hot_en = std::atoi(argv[1])!=0;
    noc::SrcParams sp; sp.on=128; sp.off=64; sp.hist=4; sp.shift=4; sp.validate();
    noc::HotParams hp; if(hot_en){ hp.on=451; hp.off=328; hp.floor=205; hp.init=410; hp.shift=4; } hp.validate();
    noc::SrcState s; noc::HotState h;
    std::mt19937 g(2026); std::uniform_real_distribution<double> u(0,1);
    FILE* f=std::fopen(argv[2],"w"); if(!f) return 1;
    const int n=1024; long long count=0;
    for(int phase=0; phase<60; ++phase) {
        int mode=phase%5, len=500+int(g()%1500), hot=int(g()%n), fixed=int(g()%n);
        int flows[4]; for(int& x:flows) x=int(g()%n);
        for(int i=0;i<len;++i) {
            int d;
            switch(mode) {
                case 0: d=int(g()%n); break;                                  // uniform
                case 1: d= u(g)<0.2 ? hot : int(g()%n); break;                // hotspot
                case 2: d=fixed; break;                                       // permutation flow
                case 3: d=flows[g()%4]; break;                                // small flow set
                default: d= (i&1) ? fixed : int(g()%8); break;                // adversarial mix
            }
            bool m=noc::saqr_hot_classify(s,h,d,sp,hp);
            std::fprintf(f,"%d %d\n",d,m?1:0); ++count;
        }
    }
    std::fclose(f);
    std::printf("wrote %lld vectors (hot_en=%d)\n",count,hot_en?1:0);
}
