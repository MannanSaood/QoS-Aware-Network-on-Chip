#pragma once
// SAQR: Safe Adaptive QoS Routing (docs/SAQR_SPEC_V2.md), plus the comparator
// routes used in its study. Research candidate; not validated or benchmarked.
//
// Each function returns a route set: up to two (port, VC sub-range, priority)
// entries, VC offsets relative to the packet's class base (class has 2 VCs).
// Higher priority = preferred on the input side of VC allocation. Packet QoS
// priority still decides output-side arbitration (BookSim out_priority).
//
// Safety (SAQR / CTY): a Y hop taken while dx != 0 is "non-compliant" and may
// use only class VC offset 1. Every SAQR route set contains the XY port over
// both class VCs. See tests/saqr_deadlock_check.cpp for the mechanical check.
#include "../common/mesh.hpp"
#include "../xy/routing.hpp"
#include "../chr/routing.hpp"
#include <array>
#include <cstdint>
#include <stdexcept>

namespace noc {

struct RouteEntry { int port=-1, vc_lo=0, vc_hi=1, pri=0; };
struct RouteSet {
    std::array<RouteEntry,2> e{}; int n=0;
    bool switched=false;      // preferred entry is not the XY port
    bool gated=false;         // pressure gate was open
    void add(int port,int lo,int hi,int pri){ if(n>=2) throw std::logic_error("route set overflow"); e[n++]=RouteEntry{port,lo,hi,pri}; }
};

inline int productive_other(int cur,int dst,int k,int x_port) {
    // The productive direction other than the XY port, or -1 if only one exists.
    int dx=dst%k-cur%k, dy=dst/k-cur/k;
    if(dx!=0 && dy!=0 && (x_port==E || x_port==W)) return dy>0 ? S : N;
    return -1;   // XY moves in X first; once dx==0 only one productive port exists
}
inline bool non_compliant_hop(int cur,int dst,int k,int port) {
    return (port==S || port==N) && dst%k!=cur%k;
}

// Regional summaries: r[c][d] is a 4-bit decaying sum of class-c pressure
// looking outward from this router in direction d (DBAR-inspired; not
// destination-truncated). Propagated one hop per update.
struct SaqrRegional { std::array<std::array<uint8_t,4>,2> s{}; };
inline uint8_t saqr_regional_next(int local_e,int downstream_s) {
    // (local 4-bit + downstream 4-bit) / 2, both 0..15
    return uint8_t(((local_e>>2) + downstream_s) >> 1);
}

enum class SaqrVariant { Local, Regional, NoGate };
struct SaqrParams {
    SaqrVariant variant=SaqrVariant::Regional;
    ChrParams filter{};      // EWMA + hysteresis thresholds (A1 scaling)
    int margin=0;            // switch iff cost(A) + margin < cost(X)  (strict)
    int regional_shift=1;    // regional weight 2^-shift (w_r = 1/2)
    // Asymmetry test (pilot finding: uniform congestion is symmetric, transpose
    // congestion is not). When ratio_num > 0, switch iff
    //   costF(A) * ratio_num < costF(X) * ratio_den
    // on full-resolution costs (e in 0..60 plus scaled regional term), i.e. the
    // alternative must be less congested by the factor ratio_num/ratio_den.
    // ratio_num == 0 keeps the original additive-margin rule bit-for-bit.
    int ratio_num=0, ratio_den=1;
    // Class-selective adaptivity: bit c set = class c may adapt; others route
    // pure XY. Default 3 (both classes) keeps earlier behaviour bit-for-bit.
    int adapt_class_mask=3;
    // Two-tier (per-class) overrides. -1 = inherit the global setting, so the
    // defaults keep earlier behaviour bit-for-bit.
    //   cls_gate[c]:  0 = always compare (NoGate behaviour), 1 = require the
    //                 hysteresis gate on the XY port.
    //   cls_ratio_num/den[c]: per-class asymmetry ratio (same rule as ratio_num/den).
    std::array<int,2> cls_gate{{-1,-1}};
    std::array<int,2> cls_ratio_num{{-1,-1}}, cls_ratio_den{{-1,-1}};
    // Stall-triggered best effort (§15). be_stall < 0: off. Otherwise best
    // effort routes pure XY until its head flit has failed VC allocation for
    // be_stall cycles at this router; it is then re-routed with
    // saqr_stall_route(waited = true).
    int be_stall=-1;
    // Regime detector for best effort (§16). regime_on < 0: off. Otherwise best
    // effort may leave XY only at routers whose detector is on. The detector
    // compares long-horizon BE pressure on X ports pooled along the router's
    // row (x) with BE pressure on Y ports pooled along its column (y):
    //   turns on  when x > floor and 10*x > y*regime_on
    //   stays on  while x > floor and 10*x > y*regime_off   (hysteresis)
    // Ratios are in tenths (regime_on = 50 means 5.0). Requires off <= on.
    int regime_on=-1, regime_off=-1;
    long long regime_floor=0;   // minimum pooled X pressure (credits x 256)
    int regime_shift=8;         // slow EWMA weight 2^-shift per cycle
    // Soft O1TURN (§17): bit c set = class c follows a per-packet XY/YX plan
    // chosen obliviously at injection instead of the congestion rule.
    int o1turn_class_mask=0;
};

// Deterministic 50/50 plan bit from the packet id (oblivious, open loop).
inline bool o1turn_plan_yx(int pid) { return ((static_cast<unsigned>(pid)*2654435761u)>>16)&1u; }

// Soft O1TURN under CTY. A YX-planned packet that still has both dx and dy
// prefers the Y port on VC offset 1 (non-compliant) and is always offered the
// XY port over both VCs as escape. `yx` is false once the plan is abandoned.
inline RouteSet saqr_o1turn_route(int cur,int dst,int k,bool yx) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(!yx || a<0) { rs.add(x,0,1,0); return rs; }
    rs.add(a,1,1,1); rs.add(x,0,1,0); rs.switched=true; return rs;
}

// Strict O1TURN (Seo et al., ISCA 2005) comparator: two virtual subnetworks,
// VC offset 0 = XY, VC offset 1 = YX; each is dimension-ordered, so each is
// acyclic and the plan never changes. Not a CTY route (no XY escape on VC 1).
inline RouteSet o1turn_route(int cur,int dst,int k,bool yx) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int dx=dst%k-cur%k, dy=dst/k-cur/k;
    if(yx) rs.add(dy>0?S:dy<0?N:(dx>0?E:W),1,1,0);
    else   rs.add(dx>0?E:dx<0?W:(dy>0?S:N),0,0,0);
    return rs;
}

inline bool saqr_regime_next(bool on,long long x,long long y,const SaqrParams& p) {
    if(p.regime_on<0) return true;
    if(x<=p.regime_floor) return false;
    return x*10 > y*(on ? p.regime_off : p.regime_on);
}
// Slow per-port pressure in fixed point (scale 256), floor-shift EWMA.
inline long long saqr_slow_next(long long s,int used,int shift) {
    long long d=(static_cast<long long>(used)<<8)-s;
    return s + (d>=0 ? (d>>shift) : -((-d+(1LL<<shift)-1)>>shift));
}

// Stall-triggered route set (reactive, no congestion estimate). Before the
// wait threshold: XY over both class VCs. After it: XY still preferred
// (priority 1) with the other productive port as a fallback (priority 0),
// restricted to VC offset 1 when non-compliant (CTY). The XY port over both
// class VCs is always present, so the §2 safety argument is unchanged.
inline RouteSet saqr_stall_route(int cur,int dst,int k,bool waited) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(!waited || a<0) { rs.add(x,0,1,0); return rs; }
    rs.add(x,0,1,1); rs.add(a,non_compliant_hop(cur,dst,k,a)?1:0,1,0); rs.gated=true;
    return rs;
}

// cost inputs: e = local filtered pressure (0..60) of each output for class c;
// s_down[p] = downstream router's regional summary in direction p (0..15).
inline RouteSet saqr_route(int cur,int dst,int k,int cl,const ChrState& st,
                           const std::array<int,4>& s_down,const SaqrParams& prm) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(a<0 || !((prm.adapt_class_mask>>cl)&1)) { rs.add(x,0,1,0); return rs; }
    const bool always = prm.cls_gate[cl]>=0 ? prm.cls_gate[cl]==0 : prm.variant==SaqrVariant::NoGate;
    const int rnum = prm.cls_ratio_num[cl]>=0 ? prm.cls_ratio_num[cl] : prm.ratio_num;
    const int rden = prm.cls_ratio_den[cl]>=0 ? prm.cls_ratio_den[cl] : prm.ratio_den;
    rs.gated = always || st.h[cl][x]!=0;
    if(rs.gated) {
        auto cost=[&](int p){
            int c=st.e[cl][p]>>2;
            if(prm.variant!=SaqrVariant::Local) c+=s_down[p]>>prm.regional_shift;
            return c; };
        auto costF=[&](int p){
            int c=st.e[cl][p];
            if(prm.variant!=SaqrVariant::Local) c+=(s_down[p]<<2)>>prm.regional_shift;
            return c; };
        bool take = rnum>0 ? costF(a)*rnum < costF(x)*rden
                                    : cost(a)+prm.margin<cost(x);
        if(take) {
            int lo=non_compliant_hop(cur,dst,k,a) ? 1 : 0;
            rs.add(a,lo,1,1); rs.add(x,0,1,0); rs.switched=true; return rs;
        }
    }
    rs.add(x,0,1,0);
    return rs;
}

// ---- Comparators (same class partition, 2 VCs per class) ----------------

// Duato minimal adaptive with a DEDICATED escape VC per class (offset 0 = XY
// escape, offset 1 = adaptive). Packets already in the escape VC stay there
// (BookSim min_adapt behaviour). Adaptive options ranked by local pressure.
inline RouteSet duato_route(int cur,int dst,int k,int /*cl*/,int in_vc_offset,const ChrView& view,int cap) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(in_vc_offset==0) { rs.add(x,0,0,0); return rs; }          // escape stays escape
    int best=x;
    if(a>=0 && chr_quantize(view[a].used,cap)<chr_quantize(view[x].used,cap)) best=a;
    rs.add(best,1,1,1);                                           // adaptive VC on preferred port
    rs.add(x,0,0,0);                                              // escape VC on XY port
    rs.switched = best!=x;
    return rs;
}

// West-first adaptive (Glass & Ni turn model), both class VCs, local selection.
inline RouteSet westfirst_route(int cur,int dst,int k,const ChrView& view,int cap) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int dx=dst%k-cur%k, dy=dst/k-cur/k;
    if(dx<0) { rs.add(W,0,1,0); return rs; }                      // all westward motion first
    int x=xy(cur,dst,k), a=(dx>0 && dy!=0) ? (dy>0?S:N) : -1;
    int best=x;
    if(a>=0 && chr_quantize(view[a].used,cap)<chr_quantize(view[x].used,cap)) best=a;
    rs.add(best,0,1,0); rs.switched = best!=x;
    return rs;
}

// UFA: unrestricted fully adaptive minimal, both VCs. NOT deadlock-free; used
// only for the price-of-safety experiment, with a progress watchdog.
inline RouteSet ufa_route(int cur,int dst,int k,const ChrView& view,int cap) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    int best=x;
    if(a>=0 && chr_quantize(view[a].used,cap)<chr_quantize(view[x].used,cap)) best=a;
    rs.add(best,0,1,0); rs.switched = best!=x;
    return rs;
}

}
