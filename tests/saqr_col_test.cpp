// Unit tests for SAQR-C, the turn-column convergence cue (docs/SAQR_SPEC_V2.md §22).
// Build: g++ -std=c++17 -O2 -Wall tests/saqr_col_test.cpp -o saqr_col_test
#include "../algorithms/saqr_col/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static ColParams cp(int on,int off,int floor,int init,int shift,int mode){ ColParams p; p.on=on; p.off=off; p.floor=floor; p.init=init; p.shift=shift; p.mode=mode; p.validate(); return p; }

// Reference model, written independently of the header (mirrors the §22 pseudo-code).
struct Ref { int cand=-1,f=0; bool conv=false; };
static void ref_step(Ref& r,int col,const ColParams& p){
    if(col==r.cand) r.f+=(4096-r.f)>>p.shift; else r.f-=r.f>>p.shift;
    if(r.f<p.floor && col!=r.cand){ r.cand=col; r.f=p.init; }
    if(!r.conv && r.f>=p.on) r.conv=true; else if(r.conv && r.f<p.off) r.conv=false;
}

// Share of observations after warm-up during which the converging bit is set, for a stream where a
// fraction `share` of the head flits go to column 0 and the rest to uniformly random columns of k.
static double conv_rate(int k,double share,const ColParams& p,unsigned seed){
    std::mt19937 g(seed); std::uniform_real_distribution<double> u(0,1); long long on=0,tot=0;
    for(int trial=0;trial<100;++trial){ ColState c;
        for(int i=0;i<4000;++i){ int col = u(g)<share ? 0 : int(g()%k); saqr_col_observe(c,col,p); if(i>=500){ on+=c.conv; ++tot; } } }
    return double(on)/tot;
}

int main(){
    const ColParams vs[4]={cp(2048,1434,512,1024,5,0),cp(1024,717,256,512,5,0),cp(2048,1434,512,1024,5,1),cp(1024,717,256,512,5,1)};
    // 1. Header equals the reference model on random streams (all variants, many seeds, several k).
    for(const ColParams& p:vs) for(unsigned seed=1;seed<=200;++seed){
        std::mt19937 g(seed); ColState c; Ref r; int k=4<<(seed%4);
        for(int i=0;i<3000;++i){ int col = (g()%3==0) ? int(seed%k) : int(g()%k);
            saqr_col_observe(c,col,p); ref_step(r,col,p);
            CHECK(c.cand==r.cand); CHECK(c.f==r.f); CHECK(c.conv==r.conv); CHECK(c.f>=0 && c.f<=4096); }
    }
    // 2. A single converging column (transpose / bit-reversal rows) sets the bit quickly and keeps it.
    for(const ColParams& p:vs){ ColState c; int first=-1;
        for(int i=0;i<200;++i){ saqr_col_observe(c,7,p); if(c.conv && first<0) first=i; if(i>first && first>=0) CHECK(c.conv); }
        CHECK(first>=0 && first<64); CHECK(c.cand==7); }
    // 3. Spread columns (bit complement / tornado / random flows): the strict variant never converges for k >= 8.
    for(int k:{8,16,32}) CHECK(conv_rate(k,0.0,vs[0],k)==0.0);
    for(int k:{16,32}) CHECK(conv_rate(k,0.0,vs[1],k)<0.01);
    // 4. Strong convergence is detected by both thresholds.
    for(int k:{8,16,32}){ CHECK(conv_rate(k,0.8,vs[0],k)>0.95); CHECK(conv_rate(k,0.5,vs[1],k)>0.95); }
    // 5. Packet bit: only the convergent column, never the source's own column, never when not converging.
    { ColState c; c.cand=3; c.conv=true; CHECK(saqr_col_bit(c,0,3)); CHECK(!saqr_col_bit(c,0,4)); CHECK(!saqr_col_bit(c,3,3));
      c.conv=false; CHECK(!saqr_col_bit(c,0,3)); }
    // 6. Modes: 0 = column bit only; 1 = column bit OR (hot AND NOT repeat).
    for(int cb=0;cb<2;++cb) for(int rep=0;rep<2;++rep) for(int hot=0;hot<2;++hot){
        CHECK(saqr_col_classify(cb,rep,hot,vs[0])==bool(cb));
        CHECK(saqr_col_classify(cb,rep,hot,vs[2])==bool(cb || (hot && !rep))); }
    // 7. Parameter validation.
    int bad=0; auto tryp=[&](int on,int off,int fl,int in,int sh,int mo){ try{ cp(on,off,fl,in,sh,mo); }catch(const std::invalid_argument&){ ++bad; } };
    tryp(2048,2049,512,1024,5,0); tryp(2048,1434,0,1024,5,0); tryp(2048,1434,512,1500,5,0); tryp(2048,1434,512,1024,9,0); tryp(2048,1434,512,1024,5,2);
    CHECK(bad==5);
    { ColParams off; off.validate(); CHECK(off.on<0); }
    std::printf("strict spread k=8 conv %.4f, loose spread k=8 conv %.4f, k=4 %.4f\n",conv_rate(8,0,vs[0],1),conv_rate(8,0,vs[1],2),conv_rate(4,0,vs[1],3));
    std::printf("saqr_col_test: %lld checks PASS\n",checks);
}
