// Gate 1 unit tests for SAQR and its comparators (docs/SAQR_SPEC_V2.md §6.1).
// Build: g++ -std=c++17 -O2 tests/saqr_test.cpp -o saqr_test
#include "../algorithms/saqr/routing.hpp"
#include <cstdio>
#include <cstdlib>
#include <random>

static long long checks=0;
#define CHECK(c) do { ++checks; if(!(c)) { std::fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); std::exit(1); } } while(0)
using namespace noc;

static const int CAP=10;
static bool productive(int cur,int dst,int k,int p){ int dx=dst%k-cur%k, dy=dst/k-cur/k;
    return (p==E&&dx>0)||(p==W&&dx<0)||(p==S&&dy>0)||(p==N&&dy<0); }

static void random_state(std::mt19937& g,ChrState& st,std::array<int,4>& s,ChrView& v){
    for(int c=0;c<2;++c) for(int p=0;p<4;++p){ st.e[c][p]=g()%61; st.h[c][p]=g()%2; }
    for(auto& x:s) x=g()%16;
    for(auto& p:v){ p.used=g()%(CAP+1); p.peak=std::min(p.used,5); p.free_vcs=g()%3; }
}
// Common structural checks on any route set.
static void check_set(const RouteSet& rs,int cur,int dst,int k){
    CHECK(rs.n>=1 && rs.n<=2);
    if(cur==dst){ CHECK(rs.n==1 && rs.e[0].port==LOCAL); return; }
    for(int i=0;i<rs.n;++i){
        CHECK(productive(cur,dst,k,rs.e[i].port));
        CHECK(rs.e[i].vc_lo>=0 && rs.e[i].vc_lo<=rs.e[i].vc_hi && rs.e[i].vc_hi<=1);
    }
    if(rs.n==2){
        CHECK(rs.e[0].pri!=rs.e[1].pri);                  // BookSim's set collapses equal priorities
        // Same port twice only with disjoint VC ranges (Duato: adaptive VC + escape VC on the XY port).
        if(rs.e[0].port==rs.e[1].port) CHECK(rs.e[0].vc_hi<rs.e[1].vc_lo || rs.e[1].vc_hi<rs.e[0].vc_lo);
    }
}

static void test_saqr_paths(){
    std::mt19937 g(77);
    for(int k:{3,4,5,8}) for(auto var:{SaqrVariant::Local,SaqrVariant::Regional,SaqrVariant::NoGate})
    for(int cl=0;cl<2;++cl) for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) for(int t=0;t<3;++t){
        SaqrParams prm; prm.variant=var; int cur=src, hops=0;
        while(cur!=dst){
            ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
            auto rs=saqr_route(cur,dst,k,cl,st,s,prm); check_set(rs,cur,dst,k);
            int x=xy(cur,dst,k);
            // The XY port over BOTH class VCs is always present, at the lowest priority.
            bool has_x=false; int minpri=99;
            for(int i=0;i<rs.n;++i){ minpri=std::min(minpri,rs.e[i].pri);
                if(rs.e[i].port==x){ has_x=true; CHECK(rs.e[i].vc_lo==0 && rs.e[i].vc_hi==1); } }
            CHECK(has_x);
            for(int i=0;i<rs.n;++i) if(rs.e[i].port==x) CHECK(rs.e[i].pri==minpri);
            // CTY: non-compliant entries may only use VC offset 1.
            for(int i=0;i<rs.n;++i) if(non_compliant_hop(cur,dst,k,rs.e[i].port)) CHECK(rs.e[i].vc_lo==1);
            // Exact XY when calm: gate closed (and not NoGate) => only the XY entry.
            if(var!=SaqrVariant::NoGate && st.h[cl][x]==0) CHECK(rs.n==1 && rs.e[0].port==x);
            CHECK(rs.switched==(rs.n==2));
            // Class isolation: class (1-cl) state does not change the decision.
            ChrState st2=st; for(int p=0;p<4;++p){ st2.e[1-cl][p]=60-st2.e[1-cl][p]; st2.h[1-cl][p]^=1; }
            auto rs2=saqr_route(cur,dst,k,cl,st2,s,prm);
            CHECK(rs2.n==rs.n && rs2.e[0].port==rs.e[0].port);
            // Follow a random entry (the allocator may grant either).
            int p=rs.e[g()%rs.n].port; int nx=neighbor(cur,p,k); CHECK(nx>=0);
            CHECK(distance(nx,dst,k)==distance(cur,dst,k)-1); cur=nx; ++hops;
        }
        CHECK(hops==distance(src,dst,k));
    }
}

static void test_saqr_rule_exact(){
    // 4x4, cur 5 -> dst 0: dx<0, dy<0. XY = W; alternative = N (non-compliant).
    const int k=4,cur=5,dst=0; CHECK(xy(cur,dst,k)==W && productive_other(cur,dst,k,W)==N);
    long long n=0;
    for(int ew=0;ew<=60;++ew) for(int en=0;en<=60;++en) for(int hw=0;hw<2;++hw) for(int sw=0;sw<16;++sw) for(int sn=0;sn<16;sn+=5)
    for(auto var:{SaqrVariant::Local,SaqrVariant::Regional}) for(int m:{0,1}) {
        ChrState st; st.e[0][W]=ew; st.e[0][N]=en; st.h[0][W]=hw;
        std::array<int,4> s{}; s[W]=sw; s[N]=sn;
        SaqrParams prm; prm.variant=var; prm.margin=m;
        auto rs=saqr_route(cur,dst,k,0,st,s,prm); ++n;
        int cw=(ew>>2)+(var==SaqrVariant::Regional?(sw>>1):0), cn=(en>>2)+(var==SaqrVariant::Regional?(sn>>1):0);
        bool sw_expect = hw && (cn+m<cw);
        CHECK(rs.switched==sw_expect);
        if(sw_expect){ CHECK(rs.e[0].port==N && rs.e[0].vc_lo==1 && rs.e[0].pri==1 && rs.e[1].port==W && rs.e[1].pri==0); }
        else CHECK(rs.n==1 && rs.e[0].port==W);
    }
    // Compliant alternative: cur 0 -> dst 5: XY = E, alternative = S (dx!=0 -> non-compliant too).
    // Construct a compliant alternative case: none exists by construction (alternative is always Y with dx!=0).
    std::printf("saqr decision states checked: %lld\n",n);
}

static void test_ratio_rule(){
    // Same hop as test_saqr_rule_exact (XY = W, alternative N, non-compliant).
    const int k=4,cur=5,dst=0; long long n=0;
    for(int ew=0;ew<=60;++ew) for(int en=0;en<=60;++en) for(int hw=0;hw<2;++hw) for(int sw=0;sw<16;sw+=3) for(int sn=0;sn<16;sn+=5)
    for(auto var:{SaqrVariant::Local,SaqrVariant::Regional,SaqrVariant::NoGate}) for(auto rd:{std::pair<int,int>{2,1},{3,2}}) {
        ChrState st; st.e[0][W]=ew; st.e[0][N]=en; st.h[0][W]=hw;
        std::array<int,4> s{}; s[W]=sw; s[N]=sn;
        SaqrParams prm; prm.variant=var; prm.ratio_num=rd.first; prm.ratio_den=rd.second;
        auto rs=saqr_route(cur,dst,k,0,st,s,prm); ++n;
        bool reg=var!=SaqrVariant::Local;
        int cw=ew+(reg?(sw<<2)>>1:0), cn=en+(reg?(sn<<2)>>1:0);
        bool gate = var==SaqrVariant::NoGate || hw;
        bool expect = gate && cn*rd.first < cw*rd.second;
        CHECK(rs.switched==expect);
        if(expect) CHECK(rs.e[0].port==N && rs.e[0].vc_lo==1 && rs.e[1].port==W);
        // Equal congestion never switches under a ratio rule (the uniform-traffic case).
        if(cw==cn) CHECK(!rs.switched);
    }
    std::printf("saqr ratio states checked: %lld\n",n);
}

static void test_class_mask(){
    std::mt19937 g(5);
    for(int mask=0;mask<4;++mask) for(int cl=0;cl<2;++cl) for(int i=0;i<20000;++i){
        int k=8, cur=g()%64, dst=g()%64; ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
        SaqrParams prm; prm.variant=SaqrVariant::NoGate; prm.adapt_class_mask=mask;
        auto rs=saqr_route(cur,dst,k,cl,st,s,prm); check_set(rs,cur,dst,k);
        if(!((mask>>cl)&1) && cur!=dst) CHECK(rs.n==1 && rs.e[0].port==xy(cur,dst,k));
    }
}

static void test_two_tier(){
    // Same hop: XY = W, alternative N (non-compliant). Critical (class 0)
    // always compares with the additive rule; BE (class 1) needs the gate
    // and a 2:1 asymmetry on full-resolution costs.
    const int k=4,cur=5,dst=0; long long n=0;
    for(int ew=0;ew<=60;++ew) for(int en=0;en<=60;++en) for(int hw=0;hw<2;++hw) for(int sw=0;sw<16;sw+=3) for(int sn=0;sn<16;sn+=5)
    for(int cl=0;cl<2;++cl) for(auto rd:{std::pair<int,int>{2,1},{3,1}}) {
        ChrState st; st.e[cl][W]=ew; st.e[cl][N]=en; st.h[cl][W]=hw;
        std::array<int,4> s{}; s[W]=sw; s[N]=sn;
        SaqrParams prm; prm.variant=SaqrVariant::NoGate;
        prm.cls_gate[1]=1; prm.cls_ratio_num[1]=rd.first; prm.cls_ratio_den[1]=rd.second;
        auto rs=saqr_route(cur,dst,k,cl,st,s,prm); ++n; check_set(rs,cur,dst,k);
        int cw=(ew>>2)+(sw>>1), cn=(en>>2)+(sn>>1);           // additive (regional, shift 1)
        int fw=ew+((sw<<2)>>1), fn=en+((sn<<2)>>1);           // full resolution
        bool expect = cl==0 ? (cn<cw) : (hw && fn*rd.first<fw*rd.second);
        CHECK(rs.switched==expect);
        CHECK(rs.gated==(cl==0 ? true : hw==1));
        if(expect) CHECK(rs.e[0].port==N && rs.e[0].vc_lo==1 && rs.e[1].port==W && rs.e[1].vc_lo==0 && rs.e[1].vc_hi==1);
        if(cl==1 && !hw) CHECK(rs.n==1 && rs.e[0].port==W);   // BE calm => exact XY
    }
    // Overrides equal to the globals change nothing (bit-identical defaults).
    std::mt19937 g(13);
    for(int i=0;i<200000;++i){
        int kk=8, c=g()%64, d=g()%64, cl=g()%2; ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
        SaqrParams a; a.variant=SaqrVariant(g()%3); a.ratio_num=(g()%2)?2:0; a.ratio_den=1;
        SaqrParams b=a; b.cls_gate={{a.variant==SaqrVariant::NoGate?0:1, a.variant==SaqrVariant::NoGate?0:1}};
        b.cls_ratio_num={{a.ratio_num,a.ratio_num}}; b.cls_ratio_den={{a.ratio_den,a.ratio_den}};
        auto r1=saqr_route(c,d,kk,cl,st,s,a), r2=saqr_route(c,d,kk,cl,st,s,b);
        CHECK(r1.n==r2.n && r1.switched==r2.switched && r1.gated==r2.gated);
        for(int j=0;j<r1.n;++j) CHECK(r1.e[j].port==r2.e[j].port && r1.e[j].vc_lo==r2.e[j].vc_lo && r1.e[j].pri==r2.e[j].pri);
    }
    std::printf("saqr two-tier states checked: %lld\n",n);
}

static void test_stall_route(){
    // Before the wait threshold: exact XY. After: XY preferred, other productive
    // port as fallback; CTY VC restriction on non-compliant hops; XY over both VCs.
    for(int k:{3,4,5,8,16}) for(int cur=0;cur<k*k;++cur) for(int dst=0;dst<k*k;++dst) for(int w=0;w<2;++w){
        auto rs=saqr_stall_route(cur,dst,k,w); check_set(rs,cur,dst,k);
        if(cur==dst) continue;
        int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
        CHECK(rs.e[0].port==x && rs.e[0].vc_lo==0 && rs.e[0].vc_hi==1);
        if(!w || a<0) CHECK(rs.n==1);
        else { CHECK(rs.n==2 && rs.e[0].pri>rs.e[1].pri && rs.e[1].port==a);
               CHECK(rs.e[1].vc_lo==(non_compliant_hop(cur,dst,k,a)?1:0)); CHECK(!rs.switched); }
        for(int i=0;i<rs.n;++i) if(non_compliant_hop(cur,dst,k,rs.e[i].port)) CHECK(rs.e[i].vc_lo==1);
    }
}

static void test_regime(){
    // Detector off by default: always "on" (no gating).
    { SaqrParams p; for(int i=0;i<100;++i) CHECK(saqr_regime_next(i%2,i*7,i*3,p)); }
    // Hysteresis: on at ratio > 5.0, stays on while > 3.5, needs x > floor.
    SaqrParams p; p.regime_on=50; p.regime_off=35; p.regime_floor=100;
    for(long long x=0;x<=3000;x+=37) for(long long y=0;y<=3000;y+=41) for(int on=0;on<2;++on){
        bool r=saqr_regime_next(on,x,y,p);
        bool expect = x>100 && x*10 > y*(on?35:50);
        CHECK(r==expect);
        if(!on && r) CHECK(saqr_regime_next(true,x,y,p));      // once on, same input keeps it on
        if(on && !r) CHECK(!saqr_regime_next(false,x,y,p));    // off from on implies off from off
    }
    // Slow EWMA converges toward used*256 from both sides, monotonically, never overshooting.
    for(int shift:{1,4,8}) for(int target:{0,3,10,20}) for(long long s0:{0LL,5120LL,2560LL}){
        long long s=s0, goal=(long long)target<<8;
        for(int i=0;i<(40<<shift);++i){ long long n=saqr_slow_next(s,target,shift);
            if(s<goal) CHECK(n>=s && n<=goal); else CHECK(n<=s && n>=goal); s=n; }
        CHECK(s<=goal && goal-s < (1LL<<shift));
    }
}

static void test_o1turn(){
    int yxc=0,tot=0; for(int pid=0;pid<100000;++pid){ yxc+=o1turn_plan_yx(pid); ++tot; }
    CHECK(yxc>tot*49/100 && yxc<tot*51/100);                        // ~50/50 split
    for(int k:{3,4,5,8,16}) for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) for(int plan=0;plan<2;++plan){
        // Strict: follow the route; the path is exactly XY or exactly YX, on one VC.
        int cur=src, hops=0; bool seen_second=false;
        while(cur!=dst){ auto rs=o1turn_route(cur,dst,k,plan); CHECK(rs.n==1);
            int p=rs.e[0].port; CHECK(productive(cur,dst,k,p)); CHECK(rs.e[0].vc_lo==plan && rs.e[0].vc_hi==plan);
            bool first_dim = plan ? (p==S||p==N) : (p==E||p==W);
            if(!first_dim) seen_second=true; else CHECK(!seen_second);    // one turn at most
            cur=neighbor(cur,p,k); ++hops; }
        CHECK(hops==distance(src,dst,k));
        // Soft: CTY-valid, XY port over both VCs always present, YX preference on VC1.
        cur=src; while(cur!=dst){ auto rs=saqr_o1turn_route(cur,dst,k,plan); check_set(rs,cur,dst,k);
            int x=xy(cur,dst,k); bool hx=false; for(int i=0;i<rs.n;++i){ if(rs.e[i].port==x){ hx=true; CHECK(rs.e[i].vc_lo==0&&rs.e[i].vc_hi==1); }
                if(non_compliant_hop(cur,dst,k,rs.e[i].port)) CHECK(rs.e[i].vc_lo==1); }
            CHECK(hx); if(plan && productive_other(cur,dst,k,x)>=0) CHECK(rs.n==2 && rs.e[0].pri>rs.e[1].pri); else CHECK(rs.n==1);
            cur=neighbor(cur,rs.e[0].port,k); }
    }
}

static void test_regional(){
    for(int e=0;e<=60;++e) for(int s=0;s<16;++s){ int r=saqr_regional_next(e,s); CHECK(r>=0 && r<=15); }
    // Converges to the local value when the downstream summary equals it.
    for(int u=0;u<16;++u) CHECK(saqr_regional_next(4*u,u)==u);
}

static void test_comparators(){
    std::mt19937 g(91);
    for(int k:{3,4,5,8}) for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) for(int t=0;t<3;++t){
        // Duato: once in escape (offset 0), stay in escape on the XY port.
        int cur=src, off=1, hops=0;
        while(cur!=dst){
            ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
            auto rs=duato_route(cur,dst,k,0,off,v,CAP); check_set(rs,cur,dst,k);
            if(off==0) CHECK(rs.n==1 && rs.e[0].port==xy(cur,dst,k) && rs.e[0].vc_lo==0 && rs.e[0].vc_hi==0);
            else { CHECK(rs.n==2 && rs.e[0].vc_lo==1 && rs.e[0].vc_hi==1 && rs.e[1].vc_hi==0 && rs.e[1].port==xy(cur,dst,k)); }
            int i=g()%rs.n; int p=rs.e[i].port; off = (off==0 || rs.e[i].vc_hi==0) ? 0 : 1;
            int nx=neighbor(cur,p,k); CHECK(distance(nx,dst,k)==distance(cur,dst,k)-1); cur=nx; ++hops;
        }
        CHECK(hops==distance(src,dst,k));
        // West-first: no westward hop after any non-west hop.
        cur=src; bool left_west=false;
        while(cur!=dst){
            ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
            auto rs=westfirst_route(cur,dst,k,v,CAP); check_set(rs,cur,dst,k); CHECK(rs.n==1);
            int p=rs.e[0].port; if(p==W) CHECK(!left_west); else left_west=true;
            cur=neighbor(cur,p,k);
        }
        // UFA: productive only.
        cur=src;
        while(cur!=dst){
            ChrState st; std::array<int,4> s; ChrView v; random_state(g,st,s,v);
            auto rs=ufa_route(cur,dst,k,v,CAP); check_set(rs,cur,dst,k); cur=neighbor(cur,rs.e[0].port,k);
        }
    }
}

int main(){
    test_saqr_paths(); test_saqr_rule_exact(); test_ratio_rule(); test_class_mask(); test_two_tier(); test_stall_route(); test_regime(); test_o1turn(); test_regional(); test_comparators();
    std::printf("saqr_test: PASS (%lld checks)\n",checks);
}
