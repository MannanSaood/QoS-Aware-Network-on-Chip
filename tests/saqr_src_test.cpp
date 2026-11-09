// Unit tests for SAQR-SC, the source-classified SAQR (docs/SAQR_SPEC_V2.md §19).
// Build: g++ -std=c++17 -O2 tests/saqr_src_test.cpp -o saqr_src_test
#include "../algorithms/saqr_src/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static bool productive(int cur,int dst,int k,int p){ int dx=dst%k-cur%k, dy=dst/k-cur/k;
    return (p==E&&dx>0)||(p==W&&dx<0)||(p==S&&dy>0)||(p==N&&dy<0); }

// Route sets: always minimal, XY port over both VCs present at lowest priority,
// non-compliant hops only on VC offset 1, deterministic packets = exact XY,
// adaptive packets = the soft-O1TURN SAQR set. Walks reach the destination
// minimally whatever entry is taken.
static void test_routes() {
    std::mt19937 g(7);
    for(int k=2;k<=10;++k) for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) for(int ad=0;ad<2;++ad) for(int plan=0;plan<2;++plan) {
        int cur=src, hops=0; bool yx=plan;
        while(true) {
            RouteSet rs=saqr_src_route(cur,dst,k,ad,yx);
            CHECK(rs.n>=1 && rs.n<=2);
            if(cur==dst){ CHECK(rs.n==1 && rs.e[0].port==LOCAL); break; }
            const int x=xy(cur,dst,k); bool has_x=false; int minpri=99;
            for(int i=0;i<rs.n;++i){ CHECK(productive(cur,dst,k,rs.e[i].port)); minpri=std::min(minpri,rs.e[i].pri);
                if(non_compliant_hop(cur,dst,k,rs.e[i].port)) CHECK(rs.e[i].vc_lo==1 && rs.e[i].vc_hi==1);
                if(rs.e[i].port==x){ has_x=true; CHECK(rs.e[i].vc_lo==0 && rs.e[i].vc_hi==1); } }
            CHECK(has_x);
            for(int i=0;i<rs.n;++i) if(rs.e[i].port==x) CHECK(rs.e[i].pri==minpri);
            if(rs.n==2) CHECK(rs.e[0].pri!=rs.e[1].pri);
            if(!ad) CHECK(rs.n==1 && rs.e[0].port==x && !rs.switched);
            else { RouteSet o=saqr_o1turn_route(cur,dst,k,yx); CHECK(o.n==rs.n && o.switched==rs.switched);
                   for(int i=0;i<rs.n;++i) CHECK(o.e[i].port==rs.e[i].port && o.e[i].vc_lo==rs.e[i].vc_lo && o.e[i].vc_hi==rs.e[i].vc_hi && o.e[i].pri==rs.e[i].pri); }
            int p=rs.e[g()%rs.n].port;
            if(yx && (p==E||p==W) && dst/k!=cur/k) yx=false;     // sticky plan abandonment, as in the simulator
            int nx=neighbor(cur,p,k); CHECK(nx>=0); CHECK(distance(nx,dst,k)==distance(cur,dst,k)-1); cur=nx; ++hops;
        }
        CHECK(hops==distance(src,dst,k));
    }
}

// Classifier: EWMA arithmetic, history ring, hysteresis truth table.
static void test_classifier() {
    SrcParams p; p.on=128; p.off=64; p.hist=4; p.shift=4; p.validate();
    // A single repeated destination (permutation flow) turns adaptive after a few packets and stays.
    { SrcState s; int first=-1;
      for(int i=0;i<200;++i){ bool a=saqr_src_observe(s,5,p); if(a && first<0) first=i; if(first>=0) CHECK(a); }
      CHECK(first>0 && first<=16); CHECK(s.ewma>=240 && s.ewma<=256); }
    // All-distinct destinations never adapt; EWMA stays 0.
    { SrcState s; for(int i=0;i<1000;++i){ CHECK(!saqr_src_observe(s,i,p)); CHECK(s.ewma==0); } }
    // Hysteresis: after switching on, it switches off only below `off`.
    { SrcState s; for(int i=0;i<50;++i) saqr_src_observe(s,3,p); CHECK(s.adaptive);
      int i=0; while(s.adaptive){ int before=s.ewma; bool a=saqr_src_observe(s,1000+i,p); CHECK(s.ewma<=before);
          if(a) CHECK(s.ewma>=p.off); else CHECK(s.ewma<p.off); ++i; CHECK(i<200); }
      CHECK(s.ewma<p.off); }
    // EWMA always within [0,256]; history only remembers the last M destinations.
    { std::mt19937 g(3); for(int m=1;m<=8;++m) for(int sh=1;sh<=8;++sh){ SrcParams q; q.on=200; q.off=100; q.hist=m; q.shift=sh; q.validate();
          SrcState s; std::vector<int> recent;
          for(int i=0;i<4000;++i){ int d=g()%(m+3); bool hit=false; for(int r:recent) hit|=(r==d);
              int before=s.ewma; saqr_src_observe(s,d,q);
              CHECK(s.ewma>=0 && s.ewma<=256);
              if(hit) CHECK(s.ewma>=before); else CHECK(s.ewma<=before);
              recent.push_back(d); if((int)recent.size()>m) recent.erase(recent.begin()); } } }
    // Uniform destinations: the adaptive share stays tiny at k >= 8 (statistical sanity, fixed seed).
    for(int k: {8,16}) { std::mt19937 g(11); SrcState s; long long on=0, n=200000;
        for(long long i=0;i<n;++i) on+=saqr_src_observe(s,g()%(k*k),p);
        CHECK(on*1000<n); }                                  // < 0.1 % of packets
    // Validation errors.
    { SrcParams q; q.on=10; q.off=20; bool threw=false; try{ q.validate(); }catch(const std::invalid_argument&){ threw=true; } CHECK(threw); }
    { SrcParams q; q.on=10; q.off=5; q.hist=9; bool threw=false; try{ q.validate(); }catch(const std::invalid_argument&){ threw=true; } CHECK(threw); }
    { SrcParams q; bool threw=false; try{ q.validate(); }catch(...){ threw=true; } CHECK(!threw); }   // disabled = always valid
}

int main() {
    test_routes();
    test_classifier();
    std::printf("saqr_src_test PASS (%lld checks)\n",checks);
}
