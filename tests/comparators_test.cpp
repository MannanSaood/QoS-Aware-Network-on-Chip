// Unit tests for the §21 comparators (DBAR-style, Footprint-style), Duato framework.
// Deadlock freedom rests on Duato's condition: the escape VC (class offset 0) carries only
// XY routes (acyclic channel dependency graph) and every packet can always request it;
// a packet in the escape VC stays there. These tests check exactly those properties,
// plus minimality, for random congestion states on k = 2..10 meshes.
// Build: g++ -std=c++17 -O2 -Wall tests/comparators_test.cpp -o comparators_test
#include "../algorithms/dbar/routing.hpp"
#include "../algorithms/footprint/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static bool productive(int cur,int dst,int k,int p){ int dx=dst%k-cur%k, dy=dst/k-cur/k;
    return (p==E&&dx>0)||(p==W&&dx<0)||(p==S&&dy>0)||(p==N&&dy<0); }

static void check_set(const RouteSet& rs,int cur,int dst,int k,int in_off) {
    if(cur==dst){ CHECK(rs.n==1 && rs.e[0].port==LOCAL); return; }
    const int x=xy(cur,dst,k);
    CHECK(rs.n>=1 && rs.n<=2);
    bool escape_xy=false;
    for(int i=0;i<rs.n;++i){
        CHECK(productive(cur,dst,k,rs.e[i].port));                       // minimal
        CHECK(rs.e[i].vc_lo>=0 && rs.e[i].vc_hi<=1 && rs.e[i].vc_lo<=rs.e[i].vc_hi);
        if(rs.e[i].vc_lo==0){ CHECK(rs.e[i].port==x); CHECK(rs.e[i].vc_hi==0); escape_xy=true; }   // escape VC: XY only
    }
    CHECK(escape_xy);                                                     // escape always offered
    if(in_off==0){ CHECK(rs.n==1 && rs.e[0].port==x && rs.e[0].vc_lo==0 && rs.e[0].vc_hi==0); }   // escape stays escape
}

int main() {
    std::mt19937 g(21);
    for(int k=2;k<=10;++k){
        const int n=k*k; std::vector<std::array<int,4>> occ(n);
        for(int trial=0;trial<30;++trial){
            for(auto& a:occ) for(int& v:a) v=int(g()%9);
            for(int cur=0;cur<n;++cur) for(int dst=0;dst<n;++dst) for(int off=0;off<2;++off){
                RouteSet d=dbar_route(cur,dst,k,off,[&](int r,int p){ return occ[r][p]; });
                check_set(d,cur,dst,k,off);
                FootprintView v; for(int p=0;p<4;++p){ v[p].used=int(g()%9); v[p].adaptive_used=int(g()%5)*(g()%2); v[p].fp_dest = g()%3==0 ? dst : int(g()%n); }
                RouteSet f=footprint_route(cur,dst,k,off,v,8);
                check_set(f,cur,dst,k,off);
                // DBAR picks the direction with the lower destination-truncated sum (ties: XY port).
                if(off==1 && cur!=dst){ int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
                    if(a>=0){ int cx=dbar_cost(cur,dst,k,x,[&](int r,int p){ return occ[r][p]; }), ca=dbar_cost(cur,dst,k,a,[&](int r,int p){ return occ[r][p]; });
                        CHECK(d.e[0].port==(ca<cx ? a : x)); } }
                // Footprint: congested (no free adaptive VC) and exactly one port holds a footprint -> that port.
                if(off==1 && cur!=dst){ int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
                    if(a>=0 && v[x].adaptive_used>0 && v[a].adaptive_used>0 && ((v[x].fp_dest==dst)!=(v[a].fp_dest==dst)))
                        CHECK(f.e[0].port==(v[a].fp_dest==dst ? a : x)); }
            }
        }
    }
    // dbar_cost truncates at the destination coordinate.
    { const int k=8; std::vector<std::array<int,4>> occ(64,{1,1,1,1});
      CHECK(dbar_cost(0,3,k,E,[&](int r,int p){ return occ[r][p]; })==3);
      CHECK(dbar_cost(0,8*5,k,S,[&](int r,int p){ return occ[r][p]; })==5); }
    std::printf("comparators_test PASS (%lld checks)\n",checks);
}
