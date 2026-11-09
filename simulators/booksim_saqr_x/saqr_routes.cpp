#include "saqr_routes.hpp"
#include "noc_algorithms/saqr_hot/routing.hpp"   // SAQR-H build (§20); includes saqr_src and saqr routing
#include "noc_algorithms/dbar/routing.hpp"       // DBAR-style comparator (§21)
#include "noc_algorithms/footprint/routing.hpp"  // Footprint-style comparator (§21)
#include "noc_extension.hpp"
#include "qos_runtime.hpp"
#include "routefunc.hpp"
#include "globals.hpp"
#include "iq_router.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

// Comparator build (§21): copy of simulators/booksim_saqr_hot/saqr_routes.cpp plus the
// DBAR-style and Footprint-style comparator routes. Every other route is unchanged.
// Original header of the SAQR-H build:
// SAQR-H build: copy of simulators/booksim_saqr_src/saqr_routes.cpp plus the §20
// hot-destination tracker (NOC_SAQR_HOT_*). Tracker unset, behaviour equals the SAQR-SC build;
// classifier unset too, behaviour equals the SAQR build.
// Re-route hook in the SAQR study build of IQRouter (installed only when the
// stall rule is enabled; null keeps the router bit-identical to the frozen one).
extern bool (*gNocVcStallHook)(const Router*,int,int,const Flit*);

namespace {
int vcs=4, depth=8, side=4, classes=2, packet_flits=5;
std::string active;
bool is_saqr=false;              // saqr, saqr_local, saqr_nogate
noc::SaqrParams params;
std::vector<noc::ChrState> filters;
std::vector<noc::SaqrRegional> regional, regional_next;
long long last_progress[2]={0,0}; // UFA watchdog: per class, last cycle a head flit was routed in-network
const int WATCHDOG=10000;
struct Counters { long long routed=0, two_option=0, switched=0, gated=0, invariant_checks=0, stall_reroutes=0; };
Counters counters[2];

// ---- Hop-delay diagnostic (§15). Read-only: never changes a routing decision.
// For each in-network hop, delay = cycles between the head flit's route call
// at the previous router and at this one (VC wait + switch + link). Hop kinds
// are decided by the output actually taken at the previous router:
//   0 X hop, 1 X hop right after a Y->X turn, 2 compliant Y hop (dx == 0),
//   3 non-compliant Y hop (detour, dx != 0, VC offset 1 only).
// Indexed [class][kind][packet has detoured before this hop: 0/1].
struct HopStat { long long n=0, sum=0, max=0; };
HopStat hops[2][4][2];
struct PacketState { int router=-1, first=0, last_time=0, last_router=-1, last_in_dir=-1; bool rerouted=false, detoured=false; signed char plan=-1, mark=-1; };
std::unordered_map<int,PacketState> pstate;
bool stall_reroute_pending=false;

// SAQR-SC (§19): per-source destination classifier; mark = header bit fixed at injection.
noc::SrcParams src;
std::vector<noc::SrcState> src_state;
long long src_marked[2][2]={{0,0},{0,0}};   // [class][0 deterministic, 1 adaptive], packets classified in window
// SAQR-H (§20): per-source hot-destination tracker; ORed into the same header bit.
noc::HotParams hot;
std::vector<noc::HotState> hot_state;
long long hot_only[2]={0,0};   // [class] packets adaptive only because of the tracker, in window
// §21 comparators. occ[cl][router][port]: class-local used credits, snapshot at the start of the cycle
// (DBAR reads it for every router on the path: zero-delay, idealized). fp[cl][router][port]: Footprint
// destination of the packet that last entered that output port's adaptive VC.
std::vector<std::array<int,4>> occ[2], fp[2];
bool is_dbar=false, is_footprint=false;

// Regime detector state (§16): slow[id][0] = BE pressure on X ports, [1] = Y ports.
std::vector<std::array<long long,2>> slow;
std::vector<char> regime;
bool regime_observe=false;   // compute and log, never gate
struct RegimeStats { long long samples=0, on=0, sum_x=0, sum_y=0; std::array<long long,200> hist{}; } regime_stats;

bool stall_hook(const Router* r,int /*input*/,int /*vc*/,const Flit* f) {
    // Called by IQRouter on every failed VC allocation (only when installed).
    if(f->cl!=1) return false;
    auto it=pstate.find(f->pid); if(it==pstate.end()) return false;
    PacketState& s=it->second;
    if(s.router!=r->GetID() || s.rerouted || GetSimTime()-s.first<params.be_stall) return false;
    s.rerouted=true; stall_reroute_pending=true;
    return true;
}

int per_class() { return vcs/classes; }
int class_capacity() { return per_class()*std::min(depth,packet_flits); }
bool in_window(int t) { return noc_fixed() && t>=noc_warmup() && t<noc_warmup()+noc_measure(); }
// BookSim kncube input ports: 0 from +x neighbour (travelling W), 1 from -x (E),
// 2 from +y (N), 3 from -y (S), 4 = injection.
int travel_dir(int in_channel) { static const int d[4]={noc::W,noc::E,noc::N,noc::S}; return in_channel<4 ? d[in_channel] : -1; }

void view_of(const Router* r,int cl,noc::ChrView& view) {
    auto used=r->UsedCredits(); const int first=cl*per_class();
    for(int p=0;p<4;++p){ view[p]=noc::ChrPort{};
        if(noc::neighbor(r->GetID(),p,side)<0) continue;
        for(int v=first;v<first+per_class();++v){ view[p].used+=used[p*vcs+v]; view[p].peak=std::max(view[p].peak,used[p*vcs+v]); } }
}

// Runtime CTY / escape invariant on every in-network head flit.
void check_invariant(const Router* r,const Flit* f,int in_channel) {
    int d=travel_dir(in_channel); if(d<0) return;
    const int cur=r->GetID(), off=f->vc-f->cl*per_class();
    const bool y_move=(d==noc::S||d==noc::N), dx_nonzero=(f->dest%side)!=(cur%side);
    if(is_saqr && y_move && dx_nonzero && off!=1)
        throw std::runtime_error("SAQR CTY invariant violated: non-compliant packet outside designated VC");
    if(active=="o1turn") {
        const bool dy_nonzero=(f->dest/side)!=(cur/side);
        if(off==0 && y_move && dx_nonzero) throw std::runtime_error("O1TURN invariant violated: XY-subnet packet made a Y hop with dx != 0");
        if(off==1 && !y_move && dy_nonzero) throw std::runtime_error("O1TURN invariant violated: YX-subnet packet made an X hop with dy != 0");
    }
    if((active=="duato"||is_dbar||is_footprint) && off==0 && y_move && dx_nonzero)
        throw std::runtime_error("Duato-framework invariant violated: non-XY packet in escape VC");
    ++counters[f->cl].invariant_checks;
}

void route(const Router* r,const Flit* f,int in_channel,OutputSet* outputs,bool inject) {
    outputs->Clear();
    const int base=f->cl*per_class();
    if(inject) { outputs->AddRange(-1,base,base+per_class()-1); return; }
    const int cur=r->GetID(), now=GetSimTime();
    const bool reroute=stall_reroute_pending; stall_reroute_pending=false;
    last_progress[f->cl]=now;
    if(!reroute) check_invariant(r,f,in_channel);
    noc::RouteSet rs; bool yx_plan=false, src_adaptive=false;
    if(is_saqr && !reroute) {
        PacketState& s=pstate[f->pid];
        const int d=travel_dir(in_channel);
        if(s.last_router>=0 && d>=0) {
            const int prev=s.last_router; const bool ymove=(d==noc::S||d==noc::N);
            int kind = ymove ? ((f->dest%side)!=(prev%side) ? 3 : 2)
                             : ((s.last_in_dir==noc::S||s.last_in_dir==noc::N) ? 1 : 0);
            if(in_window(now)) { HopStat& h=hops[f->cl][kind][s.detoured]; ++h.n; h.sum+=now-s.last_time; h.max=std::max<long long>(h.max,now-s.last_time); }
            if(kind==3) s.detoured=true;
        }
        if(s.plan<0) s.plan=noc::o1turn_plan_yx(f->pid) ? 1 : 0;
        // A YX-planned packet that moved in X while rows remain took the XY escape: plan abandoned (sticky).
        if(s.plan==1 && (d==noc::E||d==noc::W) && (f->dest/side)!=(cur/side)) s.plan=0;
        yx_plan = s.plan==1;
        if(src.on>=0 && s.mark<0) {              // first sight = source router (injection port)
            if(cur==f->dest) s.mark=0;
            else {
                noc::SrcState& ss=src_state.at(cur); noc::HotState& hs=hot_state.at(cur);
                const bool hit=noc::saqr_hot_history_hit(ss,f->dest);
                const bool hb = hot.on>=0 ? noc::saqr_hot_observe(hs,f->dest,hit,hot) : false;
                const bool rb = noc::saqr_src_observe(ss,f->dest,src);
                s.mark = (rb||hb) ? 1 : 0;
                if(in_window(now)) { ++src_marked[f->cl][s.mark]; if(hb && !rb) ++hot_only[f->cl]; }
            }
        }
        src_adaptive = s.mark==1;
        s.router=cur; s.first=now; s.rerouted=false; s.last_time=now; s.last_router=cur; s.last_in_dir=d;
        if(cur==f->dest) pstate.erase(f->pid);
    }
    if(is_saqr && f->cl==1 && params.be_stall>=0) {
        rs=noc::saqr_stall_route(cur,f->dest,side,reroute);
        if(reroute) { if(in_window(now)) ++counters[1].stall_reroutes;
            for(int i=0;i<rs.n;++i) outputs->AddRange(rs.e[i].port,base+rs.e[i].vc_lo,base+rs.e[i].vc_hi,rs.e[i].pri);
            return; }
    } else if(is_saqr && src.on>=0) {
        rs = noc::saqr_src_route(cur,f->dest,side,src_adaptive,yx_plan);
    } else if(is_saqr) {
        std::array<int,4> s_down{};
        for(int p=0;p<4;++p){ int nb=noc::neighbor(cur,p,side); if(nb>=0) s_down[p]=regional[nb].s[f->cl][p]; }
        rs = ((params.o1turn_class_mask>>f->cl)&1) ? noc::saqr_o1turn_route(cur,f->dest,side,yx_plan)
                                                  : noc::saqr_route(cur,f->dest,side,f->cl,filters.at(cur),s_down,params);
        // Regime detector (§16): best effort leaves XY only where the detector is on.
        if(f->cl==1 && params.regime_on>=0 && !regime_observe && !regime[cur] && cur!=f->dest) {
            rs=noc::RouteSet{}; rs.add(noc::xy(cur,f->dest,side),0,1,0);
        }
    } else {
        noc::ChrView view; view_of(r,f->cl,view);
        if(active=="duato") {
            int off = (in_channel==4) ? 1 : f->vc-base;   // injected packets start adaptive
            rs=noc::duato_route(cur,f->dest,side,f->cl,off,view,class_capacity());
        } else if(is_dbar) {
            int off = (in_channel==4) ? 1 : f->vc-base;
            const auto& o=occ[f->cl];
            rs=noc::dbar_route(cur,f->dest,side,off,[&](int rr,int p){ return o.at(rr)[p]; });
        } else if(is_footprint) {
            int off = (in_channel==4) ? 1 : f->vc-base;
            const int d=travel_dir(in_channel);
            if(d>=0 && off==1) {                      // record the footprint this packet left upstream
                int back = d==noc::E?noc::W : d==noc::W?noc::E : d==noc::S?noc::N : noc::S;   // upstream router
                int up=noc::neighbor(cur,back,side); if(up>=0) fp[f->cl].at(up)[d]=f->dest;
            }
            auto used=r->UsedCredits(); noc::FootprintView v;
            for(int p=0;p<4;++p){ if(noc::neighbor(cur,p,side)<0) continue;
                v[p].used=view[p].used; v[p].adaptive_used=used[p*vcs+base+1];
                v[p].fp_dest = v[p].adaptive_used>0 ? fp[f->cl].at(cur)[p] : -1; }
            rs=noc::footprint_route(cur,f->dest,side,off,v,class_capacity());
        } else if(active=="o1turn") rs=noc::o1turn_route(cur,f->dest,side,noc::o1turn_plan_yx(f->pid));
        else if(active=="westfirst") rs=noc::westfirst_route(cur,f->dest,side,view,class_capacity());
        else rs=noc::ufa_route(cur,f->dest,side,view,class_capacity());
    }
    for(int i=0;i<rs.n;++i) outputs->AddRange(rs.e[i].port,base+rs.e[i].vc_lo,base+rs.e[i].vc_hi,rs.e[i].pri);
    if(in_window(GetSimTime()) && cur!=f->dest) {
        Counters& c=counters[f->cl]; ++c.routed; c.two_option+=(rs.n==2); c.switched+=rs.switched; c.gated+=rs.gated;
    }
}
void entry(const Router*r,const Flit*f,int in,OutputSet*o,bool i){ route(r,f,in,o,i); }
}

void saqr_register(const Configuration& config) {
    vcs=config.GetInt("num_vcs"); depth=config.GetInt("vc_buf_size"); side=config.GetInt("k");
    classes=config.GetInt("classes"); packet_flits=config.GetInt("packet_size");
    for(auto n:{"saqr","saqr_local","saqr_nogate","duato","westfirst","ufa","o1turn","dbar","footprint"}) gRoutingFunctionMap[std::string("noc_")+n+"_mesh"]=&entry;
    std::string fn=config.GetStr("routing_function");
    active = fn.rfind("noc_",0)==0 ? fn.substr(4) : fn;
    is_saqr = active=="saqr" || active=="saqr_local" || active=="saqr_nogate";
    is_dbar = active=="dbar"; is_footprint = active=="footprint";
    const bool mine = is_saqr || active=="duato" || active=="westfirst" || active=="ufa" || active=="o1turn" || is_dbar || is_footprint;
    if(!mine) return;
    if(per_class()!=2) throw std::invalid_argument("SAQR study routes assume 2 VCs per class");
    if(config.GetInt("wait_for_tail_credit")!=1 || depth<packet_flits)
        throw std::invalid_argument("SAQR safety argument requires wait_for_tail_credit=1 and depth >= packet length (VCT)");
    if(active=="saqr_local") params.variant=noc::SaqrVariant::Local;
    else if(active=="saqr_nogate") params.variant=noc::SaqrVariant::NoGate;
    else params.variant=noc::SaqrVariant::Regional;
    auto env_int=[](const char* k,int d){ const char* v=std::getenv(k); return v?std::stoi(v):d; };
    params.filter.t_on=env_int("NOC_SAQR_T_ON",params.filter.t_on);
    params.filter.t_off=env_int("NOC_SAQR_T_OFF",params.filter.t_off);
    params.filter.alpha_shift=env_int("NOC_SAQR_ALPHA_SHIFT",params.filter.alpha_shift);
    params.margin=env_int("NOC_SAQR_MARGIN",params.margin);
    params.regional_shift=env_int("NOC_SAQR_REGIONAL_SHIFT",params.regional_shift);
    params.ratio_num=env_int("NOC_SAQR_RATIO_NUM",params.ratio_num);
    params.ratio_den=env_int("NOC_SAQR_RATIO_DEN",params.ratio_den);
    params.adapt_class_mask=env_int("NOC_SAQR_CLASS_MASK",params.adapt_class_mask);
    if(params.adapt_class_mask<0 || params.adapt_class_mask>3) throw std::invalid_argument("SAQR class mask must be 0..3");
    // Two-tier per-class overrides (class 0 = critical, 1 = best effort); -1 inherits.
    const char* tag[2]={"CRIT","BE"};
    for(int c=0;c<2;++c){
        std::string p=std::string("NOC_SAQR_")+tag[c]+"_";
        params.cls_gate[c]=env_int((p+"GATE").c_str(),-1);
        params.cls_ratio_num[c]=env_int((p+"RATIO_NUM").c_str(),-1);
        params.cls_ratio_den[c]=env_int((p+"RATIO_DEN").c_str(),-1);
        if(params.cls_gate[c]<-1 || params.cls_gate[c]>1) throw std::invalid_argument("SAQR class gate must be -1, 0 or 1");
        int n=params.cls_ratio_num[c]>=0?params.cls_ratio_num[c]:params.ratio_num, d=params.cls_ratio_den[c]>=0?params.cls_ratio_den[c]:params.ratio_den;
        if(n<0 || d<=0 || (n>0 && n<d)) throw std::invalid_argument("SAQR class ratio must satisfy num >= den > 0 (or num = 0)");
    }
    if(params.ratio_num<0 || params.ratio_den<=0 || (params.ratio_num>0 && params.ratio_num<params.ratio_den))
        throw std::invalid_argument("SAQR ratio must satisfy ratio_num >= ratio_den > 0 (or ratio_num = 0)");
    params.be_stall=env_int("NOC_SAQR_BE_STALL",params.be_stall);
    if(params.be_stall>=0 && !is_saqr) throw std::invalid_argument("stall rule is a SAQR option");
    gNocVcStallHook = (is_saqr && params.be_stall>=0) ? &stall_hook : nullptr;
    params.o1turn_class_mask=env_int("NOC_SAQR_O1TURN_MASK",0);
    if(params.o1turn_class_mask<0 || params.o1turn_class_mask>3 || (params.o1turn_class_mask && !is_saqr)) throw std::invalid_argument("O1TURN mask must be 0..3 on a SAQR route");
    params.regime_on=env_int("NOC_SAQR_REGIME_ON",params.regime_on);
    params.regime_off=env_int("NOC_SAQR_REGIME_OFF",params.regime_on);
    params.regime_floor=env_int("NOC_SAQR_REGIME_FLOOR",0);
    params.regime_shift=env_int("NOC_SAQR_REGIME_SHIFT",params.regime_shift);
    regime_observe=env_int("NOC_SAQR_REGIME_OBSERVE",0)!=0;
    if(params.regime_on>=0 && (!is_saqr || params.regime_off<0 || params.regime_off>params.regime_on || params.regime_shift<1 || params.regime_shift>16))
        throw std::invalid_argument("regime detector needs a SAQR route, 0 <= off <= on and shift in 1..16");
    src.on=env_int("NOC_SAQR_SRC_ON",-1); src.off=env_int("NOC_SAQR_SRC_OFF",src.on);
    src.hist=env_int("NOC_SAQR_SRC_HIST",src.hist); src.shift=env_int("NOC_SAQR_SRC_SHIFT",src.shift);
    src.validate();
    if(src.on>=0 && (!is_saqr || params.be_stall>=0 || params.regime_on>=0 || regime_observe))
        throw std::invalid_argument("SAQR-SC needs a SAQR route and excludes the stall rule and the regime detector");
    src_state.assign(side*side,noc::SrcState{});
    hot.on=env_int("NOC_SAQR_HOT_ON",-1); hot.off=env_int("NOC_SAQR_HOT_OFF",hot.on);
    hot.floor=env_int("NOC_SAQR_HOT_FLOOR",-1); hot.init=env_int("NOC_SAQR_HOT_INIT",-1); hot.shift=env_int("NOC_SAQR_HOT_SHIFT",hot.shift);
    hot.validate();
    if(hot.on>=0 && src.on<0) throw std::invalid_argument("SAQR-H tracker needs the SAQR-SC classifier (NOC_SAQR_SRC_ON)");
    hot_state.assign(side*side,noc::HotState{});
    slow.assign(side*side,{});
    regime.assign(side*side,0);
    params.filter.validate();
    filters.assign(side*side,noc::ChrState{});
    regional.assign(side*side,noc::SaqrRegional{}); regional_next=regional;
    for(int c=0;c<2;++c){ occ[c].assign(side*side,{0,0,0,0}); fp[c].assign(side*side,{-1,-1,-1,-1}); }
}

// Start of every cycle, before routers step: decisions in cycle t read state
// registered from credits up to t-1. Regional summaries move one hop per cycle.
void saqr_tick(const std::vector<Network*>& nets,int time) {
    // A class-level deadlock can freeze one class while the other keeps moving,
    // so progress is tracked per class.
    for(int cl=0;cl<classes && active=="ufa";++cl) if(time-last_progress[cl]>WATCHDOG && time>noc_warmup()/2) {
        const char* path=std::getenv("NOC_SAQR_METRICS");
        if(path){ std::ofstream o(path); o<<"{\"route\":\"ufa\",\"watchdog_fired\":true,\"class_id\":"<<cl<<",\"cycle\":"<<time<<"}\n"; }
        throw std::runtime_error("UFA_DEADLOCK_SUSPECTED: a class routed no in-network head flit for 10000 cycles");
    }
    if(is_dbar) for(auto r:nets.at(0)->GetRouters()) {   // DBAR congestion snapshot (previous cycle, every router)
        auto used=r->UsedCredits(); const int id=r->GetID();
        for(int cl=0;cl<classes;++cl) for(int p=0;p<4;++p){ int sum=0;
            if(noc::neighbor(id,p,side)>=0) for(int v=cl*per_class();v<(cl+1)*per_class();++v) sum+=used[p*vcs+v];
            occ[cl][id][p]=sum; }
    }
    if(!is_saqr) return;
    for(auto r:nets.at(0)->GetRouters()) {
        auto used=r->UsedCredits(); const int id=r->GetID();
        for(int cl=0;cl<classes;++cl) for(int p=0;p<4;++p) {
            if(noc::neighbor(id,p,side)<0) continue;
            int sum=0; for(int v=cl*per_class();v<(cl+1)*per_class();++v) sum+=used[p*vcs+v];
            noc::chr_update(filters[id],params.filter,cl,p,noc::chr_quantize(sum,class_capacity()));
        }
    }
    for(int id=0;id<side*side;++id) for(int cl=0;cl<classes;++cl) for(int p=0;p<4;++p) {
        int nb=noc::neighbor(id,p,side);
        regional_next[id].s[cl][p] = nb<0 ? 0 : noc::saqr_regional_next(filters[id].e[cl][p], regional[nb].s[cl][p]);
    }
    regional.swap(regional_next);
    if(params.regime_on<0 && !regime_observe) return;
    // Regime detector: slow BE pressure per router on X ports (E+W) and Y ports
    // (N+S), pooled as a row mean (X) and a column mean (Y). Pooling stands in
    // for a summary network; at a 2^-8 per-cycle EWMA its latency is negligible.
    const int cl=1;
    for(auto r:nets.at(0)->GetRouters()) {
        auto used=r->UsedCredits(); const int id=r->GetID(); int u[2]={0,0};
        for(int p=0;p<4;++p) { if(noc::neighbor(id,p,side)<0) continue;
            for(int v=cl*per_class();v<(cl+1)*per_class();++v) u[(p==noc::N||p==noc::S)?1:0]+=used[p*vcs+v]; }
        for(int d=0;d<2;++d) slow[id][d]=noc::saqr_slow_next(slow[id][d],u[d],params.regime_shift);
    }
    std::vector<long long> rowx(side,0), coly(side,0);
    for(int id=0;id<side*side;++id){ rowx[id/side]+=slow[id][0]; coly[id%side]+=slow[id][1]; }
    const bool win=in_window(time);
    for(int id=0;id<side*side;++id) {
        long long x=rowx[id/side]/side, y=coly[id%side]/side;
        regime[id]=noc::saqr_regime_next(regime[id],x,y,params);
        if(win) { ++regime_stats.samples; regime_stats.on+=regime[id];
            int b = y>0 ? int(std::min<long long>(199,x*10/y)) : 199; ++regime_stats.hist[b];
            regime_stats.sum_x+=x; regime_stats.sum_y+=y; }
    }
}

void saqr_finish() {
    const char* path=std::getenv("NOC_SAQR_METRICS"); if(!path) return;
    std::ofstream out(path);
    out<<"{\"route\":\""<<active<<"\",\"watchdog_fired\":false,\"params\":{\"t_on\":"<<params.filter.t_on<<",\"t_off\":"<<params.filter.t_off
       <<",\"alpha_shift\":"<<params.filter.alpha_shift<<",\"margin\":"<<params.margin<<",\"regional_shift\":"<<params.regional_shift
       <<",\"ratio_num\":"<<params.ratio_num<<",\"ratio_den\":"<<params.ratio_den<<",\"class_mask\":"<<params.adapt_class_mask
       <<",\"cls_gate\":["<<params.cls_gate[0]<<','<<params.cls_gate[1]<<"],\"cls_ratio\":[["<<params.cls_ratio_num[0]<<','<<params.cls_ratio_den[0]
       <<"],["<<params.cls_ratio_num[1]<<','<<params.cls_ratio_den[1]<<"]],\"o1turn_mask\":"<<params.o1turn_class_mask<<",\"be_stall\":"<<params.be_stall<<",\"variant\":"<<int(params.variant)<<"},\"classes\":[";
    for(int cl=0;cl<classes;++cl){ const Counters& c=counters[cl]; if(cl) out<<',';
        out<<"{\"class_id\":"<<cl<<",\"routed\":"<<c.routed<<",\"two_option\":"<<c.two_option<<",\"switched\":"<<c.switched
           <<",\"gated\":"<<c.gated<<",\"invariant_checks\":"<<c.invariant_checks<<",\"stall_reroutes\":"<<c.stall_reroutes<<",\"hops\":[";
        for(int k=0;k<4;++k) for(int d=0;d<2;++d){ const HopStat& h=hops[cl][k][d]; if(k||d) out<<',';
            out<<"{\"kind\":"<<k<<",\"detoured\":"<<d<<",\"n\":"<<h.n<<",\"sum\":"<<h.sum<<",\"max\":"<<h.max<<'}'; }
        out<<"]}"; }
    out<<"],\"src\":{\"on\":"<<src.on<<",\"off\":"<<src.off<<",\"hist\":"<<src.hist<<",\"shift\":"<<src.shift
       <<",\"marked\":[["<<src_marked[0][0]<<','<<src_marked[0][1]<<"],["<<src_marked[1][0]<<','<<src_marked[1][1]<<"]]}";
    out<<",\"hot\":{\"on\":"<<hot.on<<",\"off\":"<<hot.off<<",\"floor\":"<<hot.floor<<",\"init\":"<<hot.init<<",\"shift\":"<<hot.shift
       <<",\"hot_only\":["<<hot_only[0]<<','<<hot_only[1]<<"]}";
    out<<",\"regime\":{\"on\":"<<params.regime_on<<",\"off\":"<<params.regime_off<<",\"floor\":"<<params.regime_floor<<",\"shift\":"<<params.regime_shift
       <<",\"observe\":"<<(regime_observe?1:0)<<",\"samples\":"<<regime_stats.samples<<",\"on_samples\":"<<regime_stats.on
       <<",\"sum_x\":"<<regime_stats.sum_x<<",\"sum_y\":"<<regime_stats.sum_y<<",\"ratio_hist_tenths\":[";
    for(int b=0;b<200;++b){ if(b) out<<','; out<<regime_stats.hist[b]; }
    out<<"]}}\n";
}
