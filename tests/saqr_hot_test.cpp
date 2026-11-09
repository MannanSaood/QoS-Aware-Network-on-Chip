// Unit tests for SAQR-H, SAQR-SC plus the hot-destination tracker (docs/SAQR_SPEC_V2.md §20).
// Build: g++ -std=c++17 -O2 -Wall tests/saqr_hot_test.cpp -o saqr_hot_test
#include "../algorithms/saqr_hot/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static HotParams hp(int on,int off,int floor,int init,int shift){ HotParams p; p.on=on; p.off=off; p.floor=floor; p.init=init; p.shift=shift; p.validate(); return p; }
static SrcParams sp(){ SrcParams p; p.on=128; p.off=64; p.hist=4; p.shift=4; p.validate(); return p; }

// Reference model, written independently of the header (mirrors the §20 pseudo-code).
struct Ref { int cand=-1,f=0; bool ad=false; std::vector<int> hist; };
static bool ref_step(Ref& r,int d,const HotParams& p){
    bool hit=false; for(int x:r.hist) hit|=(x==d);
    if(d==r.cand) r.f+=(4096-r.f)>>p.shift; else r.f-=r.f>>p.shift;
    if(r.f<p.floor && hit && d!=r.cand){ r.cand=d; r.f=p.init; }
    if(!r.ad && r.f>=p.on) r.ad=true; else if(r.ad && r.f<p.off) r.ad=false;
    r.hist.push_back(d); if(r.hist.size()>4) r.hist.erase(r.hist.begin());
    return r.ad;
}

static double adaptive_share(int n,double hot_share,int packets,int skip,const HotParams& p,unsigned seed,bool tracker_only){
    std::mt19937 g(seed); std::uniform_real_distribution<double> u(0,1); long long on=0,tot=0;
    for(int trial=0;trial<200;++trial){
        SrcState s; HotState h; SrcParams q=sp();
        for(int i=0;i<packets;++i){
            int d = u(g)<hot_share ? 0 : int(g()%n);
            bool hit=saqr_hot_history_hit(s,d);
            bool hb=saqr_hot_observe(h,d,hit,p); bool rb=saqr_src_observe(s,d,q);
            if(i>=skip){ on += tracker_only ? hb : (hb||rb); ++tot; }
        }
    }
    return double(on)/tot;
}

int main(){
    const HotParams P=hp(451,328,205,410,4);   // design point (.11 / .08 / .05 / .10, shift 4)
    // 1. Header equals the independent reference model on random streams (many parameter sets).
    {   std::mt19937 g(5);
        for(int shift=1;shift<=8;++shift) for(int trial=0;trial<40;++trial){
            int floor=1+int(g()%800), init=floor+int(g()%800), on=init+int(g()%800), off=int(g()%(on+1));
            HotParams p=hp(on,off,floor,init,shift); int n=1+int(g()%300); double hs=(g()%100)/100.0;
            SrcState s; HotState h; Ref r; std::uniform_real_distribution<double> u(0,1);
            for(int i=0;i<3000;++i){ int d = u(g)<hs ? 7%n : int(g()%n);
                bool hit=saqr_hot_history_hit(s,d); bool a=saqr_hot_observe(h,d,hit,p); saqr_src_observe(s,d,sp());
                bool b=ref_step(r,d,p); CHECK(a==b); CHECK(h.f==r.f); CHECK(h.cand==r.cand);
                CHECK(h.f>=0 && h.f<=HOT_SCALE); } } }
    // 2. Separation at the design point (statistical, fixed seeds; thresholds from the §20 offline model).
    for(int k: {8,16,32}) CHECK(adaptive_share(k*k,0.0,400,0,P,11+k,true) < (k==8 ? 0.10 : 0.02));   // uniform: tracker mostly off
    CHECK(adaptive_share(64,0.2,367,73,P,3,true)  > 0.90);          // k=8 hotspot, packets after warm-up
    CHECK(adaptive_share(256,0.2,96,19,P,4,true)  > 0.80);          // k=16 hotspot
    CHECK(adaptive_share(256,1.0,50,10,P,6,false) > 0.99);          // fixed destination: adaptive (SAQR-SC bit and tracker)
    // 3. Disabled tracker: classify() equals SAQR-SC exactly.
    {   std::mt19937 g(9); HotParams off; SrcState a,b; HotState h; SrcParams q=sp();
        for(int i=0;i<200000;++i){ int d=int(g()%37); CHECK(saqr_hot_classify(a,h,d,q,off)==saqr_src_observe(b,d,q)); } }
    // 4. Combined bit = SAQR-SC bit OR tracker bit.
    {   std::mt19937 g(10); SrcState a,b; HotState h1,h2; SrcParams q=sp();
        for(int i=0;i<200000;++i){ int d = g()%5==0 ? 3 : int(g()%64);
            bool hit=saqr_hot_history_hit(b,d); bool hb=saqr_hot_observe(h2,d,hit,P); bool rb=saqr_src_observe(b,d,q);
            CHECK(saqr_hot_classify(a,h1,d,q,P)==(hb||rb)); } }
    // 5. Candidate is only adopted from a history repeat; a never-repeating stream never adapts.
    {   SrcState s; HotState h; for(int i=0;i<5000;++i){ bool hit=saqr_hot_history_hit(s,i); CHECK(!hit); CHECK(!saqr_hot_observe(h,i,hit,P)); saqr_src_observe(s,i,sp()); CHECK(h.cand==-1); } }
    // 6. Validation.
    auto bad=[](int on,int off,int fl,int in,int sh){ HotParams p; p.on=on;p.off=off;p.floor=fl;p.init=in;p.shift=sh; try{ p.validate(); }catch(const std::invalid_argument&){ return true; } return false; };
    CHECK(bad(100,200,10,50,4)); CHECK(bad(100,50,0,50,4)); CHECK(bad(100,50,60,50,4)); CHECK(bad(100,50,10,150,4));
    CHECK(bad(100,50,10,50,0)); CHECK(bad(100,50,10,50,9)); CHECK(bad(5000,50,10,50,4)); CHECK(!bad(-1,-1,-1,-1,4));
    std::printf("saqr_hot_test PASS (%lld checks)\n",checks);
}
