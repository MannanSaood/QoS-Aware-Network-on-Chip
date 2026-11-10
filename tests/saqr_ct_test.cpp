// Unit tests for SAQR-CT, the transit-evidence gate (docs/SAQR_SPEC_V2.md §23).
// Build: g++ -std=c++17 -O2 -Wall tests/saqr_ct_test.cpp -o saqr_ct_test
#include "../algorithms/saqr_ct/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static CtParams P(int thr){ CtParams p; p.thr=thr; p.validate(); return p; }

// Reference model, written independently of the header (mirrors the §23 pseudo-code).
struct Ref { int cnt=0,r=0; };
static bool ref_inject(Ref& s,int thr){ int x=(s.cnt>8?8:s.cnt)*32; s.r+=(x-s.r)>>3; if(s.r<0) s.r=0; s.cnt=0; return s.r>=thr; }

// Fraction of injections with evidence when each injection is preceded by Poisson-like transit counts of mean m.
static double ev_rate(double m,int thr,unsigned seed){
    std::mt19937 g(seed); std::poisson_distribution<int> pd(m); CtState s; CtParams p=P(thr); long long on=0,n=0;
    for(int i=0;i<20000;++i){ int c=pd(g); for(int j=0;j<c;++j) saqr_ct_transit(s); bool e=saqr_ct_inject(s,p); if(i>=200){ on+=e; ++n; } }
    return double(on)/n;
}

int main(){
    // 1. Header equals the reference model on random event streams.
    for(int thr:{16,32,64}) for(unsigned seed=1;seed<=300;++seed){
        std::mt19937 g(seed); CtState s; Ref r; CtParams p=P(thr);
        for(int i=0;i<4000;++i){
            if(g()%3){ int c=g()%12; for(int j=0;j<c;++j){ saqr_ct_transit(s); if(r.cnt<255) ++r.cnt; } CHECK(s.cnt==r.cnt); }
            else { bool a=saqr_ct_inject(s,p), b=ref_inject(r,thr); CHECK(a==b); CHECK(s.r==r.r); CHECK(s.cnt==0); CHECK(s.r>=0 && s.r<=256); }
        }
    }
    // 2. No transit (butterfly sources, edge sources): never evidence, so the SAQR-H bit passes through.
    { CtState s; CtParams p=P(16); for(int i=0;i<1000;++i) CHECK(!saqr_ct_inject(s,p)); CHECK(s.r==0); }
    // 3. Rich transit (interior routers of bit complement / tornado rows): evidence almost always.
    CHECK(ev_rate(3.0,32,1)>0.99); CHECK(ev_rate(1.5,16,2)>0.99);
    // 4. Sparse transit below the threshold: rarely evidence.
    CHECK(ev_rate(0.1,32,3)<0.01); CHECK(ev_rate(0.1,16,4)<0.05);
    // 5. Saturation: the per-injection count is capped at 8, r never exceeds 256.
    { CtState s; CtParams p=P(256); for(int i=0;i<500;++i){ for(int j=0;j<300;++j) saqr_ct_transit(s); saqr_ct_inject(s,p); CHECK(s.r<=256); } CHECK(s.r>=248); }   // integer EWMA settles 7 below the input
    // 6. Header bit.
    for(int cb=0;cb<2;++cb) for(int h=0;h<2;++h) for(int e=0;e<2;++e) CHECK(saqr_ct_classify(cb,h,e)==bool(cb || (h && !e)));
    // 7. Validation.
    int bad=0; for(int t:{0,257,1000}) { try{ P(t); }catch(const std::invalid_argument&){ ++bad; } } CHECK(bad==3);
    { CtParams off; off.validate(); CHECK(off.thr<0); }
    std::printf("evidence rate: mean 1.0 thr16 %.3f thr32 %.3f; mean 0.5 thr16 %.3f thr32 %.3f\n",ev_rate(1,16,5),ev_rate(1,32,6),ev_rate(.5,16,7),ev_rate(.5,32,8));
    std::printf("saqr_ct_test: %lld checks PASS\n",checks);
}
