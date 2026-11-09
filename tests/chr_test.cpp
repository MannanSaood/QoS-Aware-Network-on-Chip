// Gate 1 unit tests for CHR-OE and the OE-fixed control.
// See docs/CHR_OE_CANDIDATE_SPEC.md sections 2, 3 and 7.
// Build: g++ -std=c++17 -O2 tests/chr_test.cpp -o chr_test
#include "../algorithms/chr/routing.hpp"
#include "../algorithms/oefixed/routing.hpp"
#include "../algorithms/xy/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <map>
#include <random>
#include <set>
#include <vector>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)

using namespace noc;

static const ChrVariant VARIANTS[]={ChrVariant::Cls,ChrVariant::Hyst,ChrVariant::Full};
static const int DEPTH=8, CLASS_VCS=2, CAP=CLASS_VCS*DEPTH;

static ChrPort random_port(std::mt19937& rng) {
    ChrPort p; int a=rng()%(DEPTH+1), b=rng()%(DEPTH+1);
    p.used=a+b; p.peak=std::max(a,b); p.free_vcs=rng()%(CLASS_VCS+1); return p;
}
static void randomize(ChrState& st,ChrView& v,std::mt19937& rng) {
    for(int c=0;c<CHR_CLASSES;++c) for(int p=0;p<CHR_DIRS;++p) { st.e[c][p]=rng()%61; st.h[c][p]=rng()%2; }
    for(auto& p:v) p=random_port(rng);
}
static int step(int cur,int p,int k){ int n=neighbor(cur,p,k); CHECK(n>=0); return n; }

// 1. Every variant, every (src,dst), random state at every hop: legal output,
//    strictly minimal progress, arrival in exactly Manhattan-distance hops.
static void test_paths() {
    std::mt19937 rng(20261107);
    for(int k:{3,4,5,8}) for(auto var:VARIANTS) for(int cl=0;cl<2;++cl) {
        ChrParams prm; prm.variant=var;
        for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) for(int trial=0;trial<4;++trial) {
            int cur=src, hops=0;
            while(cur!=dst) {
                ChrState st; ChrView v; randomize(st,v,rng);
                auto legal=odd_even(src,cur,dst,k);
                auto d=chr_decide(src,cur,dst,k,cl,st,prm,v,CAP,DEPTH);
                CHECK(d.candidates==int(legal.size()));
                bool member=false; for(int p:legal) member|=(p==d.port);
                CHECK(member);
                CHECK(d.switched==(d.port!=legal[0]));
                if(legal.size()==1) CHECK(!d.pressured && !d.switched);
                int next=step(cur,d.port,k);
                CHECK(distance(next,dst,k)==distance(cur,dst,k)-1);
                cur=next; ++hops;
            }
            CHECK(hops==distance(src,dst,k));
            auto d=chr_decide(src,dst,dst,k,cl,ChrState{},prm,ChrView{},CAP,DEPTH);
            CHECK(d.port==LOCAL);
        }
    }
}

// 2. Exhaustive decision-state sweep on a two-candidate hop (0 -> 5 on 4x4:
//    candidates E then S). Checks the spec rule exactly, plus monotonicity.
static void test_decision_exhaustive() {
    const int k=4, src=0, cur=0, dst=5;
    auto legal=odd_even(src,cur,dst,k);
    CHECK(legal.size()==2 && legal[0]==E && legal[1]==S);
    long long cases=0;
    for(int m:{0,2,4}) for(int fp:{0,4,8}) {
        ChrParams prm; prm.variant=ChrVariant::Full; prm.margin=m; prm.free_penalty=fp;
        for(int e0=0;e0<=60;++e0) for(int e1=0;e1<=60;++e1) for(int h0=0;h0<2;++h0) for(int h1=0;h1<2;++h1)
        for(int f0=0;f0<=2;++f0) for(int f1=0;f1<=2;++f1) {
            ChrState st; st.e[0][E]=e0; st.e[0][S]=e1; st.h[0][E]=h0; st.h[0][S]=h1;
            ChrView v; v[E].free_vcs=f0; v[S].free_vcs=f1;
            auto d=chr_decide(src,cur,dst,k,0,st,prm,v,CAP,DEPTH); ++cases;
            int c0=(f0==0?fp:0)+(e0>>2), c1=(f1==0?fp:0)+(e1>>2);
            int expect = (h0 && c1+m<=c0) ? S : E;
            CHECK(d.port==expect);
            CHECK(d.pressured==(h0!=0));
            if(!h0) CHECK(d.port==E);                 // unpressured default is never left
            // Monotone: making the alternative cheaper never flips S back to E.
            if(d.port==S && e1>0) {
                ChrState s2=st; s2.e[0][S]=e1-1;
                CHECK(chr_decide(src,cur,dst,k,0,s2,prm,v,CAP,DEPTH).port==S);
            }
            // Class isolation: class-1 state never affects a class-0 decision.
            ChrState s3=st; for(int p=0;p<4;++p){ s3.e[1][p]=60-s3.e[1][p]; s3.h[1][p]^=1; }
            CHECK(chr_decide(src,cur,dst,k,0,s3,prm,v,CAP,DEPTH).port==d.port);
        }
    }
    // Hyst and Cls variants: exact rules.
    for(int e0=0;e0<=60;++e0) for(int e1=0;e1<=60;++e1) for(int h0=0;h0<2;++h0) {
        ChrParams prm; prm.variant=ChrVariant::Hyst;
        ChrState st; st.e[0][E]=e0; st.e[0][S]=e1; st.h[0][E]=h0;
        CHECK(chr_decide(src,cur,dst,k,0,st,prm,ChrView{},CAP,DEPTH).port==((h0 && e1<e0)?S:E)); ++cases;
    }
    for(int a0=0;a0<=DEPTH;++a0) for(int b0=0;b0<=DEPTH;++b0) for(int a1=0;a1<=DEPTH;++a1) for(int b1=0;b1<=DEPTH;++b1) {
        ChrParams prm; prm.variant=ChrVariant::Cls;
        ChrView v; v[E].used=a0+b0; v[E].peak=std::max(a0,b0); v[S].used=a1+b1; v[S].peak=std::max(a1,b1);
        bool trig=10*v[E].peak>=6*DEPTH;
        int expect=(trig && chr_quantize(v[S].used,CAP)<chr_quantize(v[E].used,CAP))?S:E;
        CHECK(chr_decide(src,cur,dst,k,0,ChrState{},prm,v,CAP,DEPTH).port==expect); ++cases;
    }
    std::printf("decision states checked: %lld\n",cases);
}

// 3. Filter and hysteresis behaviour.
static void test_filter() {
    for(int s=1;s<=3;++s) for(int u=0;u<=15;++u) for(int start=0;start<=60;++start) {
        ChrParams prm; prm.alpha_shift=s; ChrState st; st.e[0][0]=start;
        for(int t=0;t<200;++t) { chr_update(st,prm,0,0,u); CHECK(st.e[0][0]<=60); }
        int e=st.e[0][0], target=4*u;
        // Floor rounding: exact from above, up to 2^s-1 below the target from below.
        CHECK(e<=target && e>=target-((1<<s)-1));
        if(start>=target) CHECK(e==target);
    }
    // Hysteresis: a step to full sets h; values strictly between the
    // thresholds never toggle it; a step to empty clears it.
    ChrParams prm; ChrState st; int toggles=0, last=0;
    for(int t=0;t<50;++t){ chr_update(st,prm,0,0,15); }
    CHECK(st.h[0][0]==1);
    for(int t=0;t<500;++t) {
        int u = 6 + (t%3);                       // 24..32 on the e scale: inside (23,38)
        chr_update(st,prm,0,0,u); toggles+=(st.h[0][0]!=last); last=st.h[0][0];
    }
    CHECK(st.h[0][0]==1 && toggles==1);          // only the initial 0->1 counted
    for(int t=0;t<50;++t){ chr_update(st,prm,0,0,0); }
    CHECK(st.h[0][0]==0);
    // Spec G2.2 at unit level: a ramp switches the decision only after e
    // crosses t_on, and switches back only after e falls to t_off.
    ChrState r; ChrParams fp; ChrView v; v[E].free_vcs=v[S].free_vcs=2;
    int first_switch=-1;
    for(int t=0;t<100;++t) {
        chr_update(r,fp,0,E,15); chr_update(r,fp,0,S,0);
        int p=chr_decide(0,0,5,4,0,r,fp,v,CAP,DEPTH).port;
        if(p==S && first_switch<0) { first_switch=t; CHECK(r.e[0][E]>=fp.t_on); }
        if(first_switch<0) CHECK(p==E);
    }
    CHECK(first_switch>0);
    bool back=false;
    for(int t=0;t<100 && !back;++t) {
        chr_update(r,fp,0,E,0);
        int p=chr_decide(0,0,5,4,0,r,fp,v,CAP,DEPTH).port;
        if(p==E) { back=true; CHECK(r.h[0][E]==0 || (r.e[0][S]>>2)+fp.margin>(r.e[0][E]>>2)); }
    }
    CHECK(back);
    // Parameter validation rejects inconsistent thresholds.
    bool rejected=false; ChrParams bad; bad.t_on=20; bad.t_off=30;
    try { bad.validate(); } catch(const std::invalid_argument&) { rejected=true; }
    CHECK(rejected); ChrParams{}.validate();
}

// 4. OE-fixed is legal, minimal, and differs from XY only where OE forbids
//    the eastward hop (dx==1, dy!=0, even destination column).
static void test_oefixed() {
    for(int k:{3,4,5,8,16}) {
        long long differ=0;
        for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) {
            int cur=src; bool path_differs=false;
            while(cur!=dst) {
                int p=oefixed(src,cur,dst,k);
                if(p!=xy(cur,dst,k)) {
                    path_differs=true;
                    CHECK(dst%k-cur%k==1 && (dst%k)%2==0 && dst/k!=cur/k);
                }
                int next=step(cur,p,k);
                CHECK(distance(next,dst,k)==distance(cur,dst,k)-1);
                cur=next;
            }
            differ+=path_differs;
        }
        std::printf("k=%d oefixed paths differing from XY: %lld/%d\n",k,differ,k*k*k*k);
    }
}

// 5. Channel-dependency graph over the UNION of all CHR-reachable choices
//    (all of odd_even), plus a negative control proving the checker can
//    detect a cycle (unrestricted minimal adaptive routing).
using RouteSet=std::function<std::vector<int>(int,int,int,int)>;
static bool cdg_acyclic(int k,const RouteSet& routes) {
    std::map<int,std::set<int>> edges;
    for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) {
        std::set<std::pair<int,int>> seen;
        std::function<void(int,int)> visit=[&](int cur,int in) {
            if(cur==dst || !seen.insert({cur,in}).second) return;
            for(int p:routes(src,cur,dst,k)) {
                int ch=cur*4+p; if(in>=0) edges[in].insert(ch);
                visit(step(cur,p,k),ch);
            }
        };
        visit(src,-1);
    }
    std::map<int,int> color; bool cyc=false;
    std::function<void(int)> dfs=[&](int u){ color[u]=1; for(int w:edges[u]){ if(color[w]==1) cyc=true; else if(!color[w]) dfs(w);} color[u]=2; };
    for(auto& kv:edges) if(!color[kv.first]) dfs(kv.first);
    return !cyc;
}
static void test_cdg() {
    RouteSet oe=[](int s,int c,int d,int k){ return odd_even(s,c,d,k); };
    RouteSet full=[](int,int c,int d,int k){
        std::vector<int> out; int dx=d%k-c%k, dy=d/k-c/k;
        if(dx>0) out.push_back(E);
        if(dx<0) out.push_back(W);
        if(dy>0) out.push_back(S);
        if(dy<0) out.push_back(N);
        return out; };
    for(int k:{3,4,5,6,8}) {
        CHECK(cdg_acyclic(k,oe));
        CHECK(!cdg_acyclic(k,full));   // checker must see the fully adaptive cycle
    }
    // Empirical cover: every port CHR emits under random states lies in odd_even
    // (test 1); hence CHR's CDG is a subgraph of the acyclic OE union.
}

int main() {
    test_paths();
    test_decision_exhaustive();
    test_filter();
    test_oefixed();
    test_cdg();
    std::printf("chr_test: PASS (%lld checks)\n",checks);
    return 0;
}
