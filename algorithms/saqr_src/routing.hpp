#pragma once
// SAQR-SC: source-classified SAQR (docs/SAQR_SPEC_V2.md §19). Research candidate.
//
// Builds on algorithms/saqr/routing.hpp (included, not modified; the frozen G4
// candidates keep using it unchanged).
//
// Idea: in-network congestion signals are distorted by the routing itself (§16:
// adapting removes the imbalance the detector looks for). The destinations a
// source chooses are not changed by routing. Each network interface keeps its
// last M destinations and an EWMA of how often a new packet repeats one of them.
//   * spread destinations (uniform, bursty, the uniform part of hotspot):
//     XY already balances; the packet is marked deterministic and routes
//     exact XY over both class VCs;
//   * repeating destinations (persistent flows, e.g. permutations): the packet
//     is marked adaptive and uses the soft-O1TURN SAQR route set (§17).
// The mark is one header bit fixed at injection. Every route set used is a
// subset of the CTY-safe SAQR sets, so the deadlock argument is unchanged.
#include "../saqr/routing.hpp"

namespace noc {

struct SrcParams {
    int on=-1;       // EWMA threshold (x/256) to switch a source to adaptive; < 0 disables SAQR-SC
    int off=-1;      // threshold to switch back (hysteresis), 0 <= off <= on
    int hist=4;      // M, destinations remembered per source (1..8)
    int shift=4;     // EWMA weight 2^-shift per injected packet (1..8)
    void validate() const {
        if(on<0) return;
        if(off<0 || off>on || on>256) throw std::invalid_argument("SAQR-SC thresholds need 0 <= off <= on <= 256");
        if(hist<1 || hist>8) throw std::invalid_argument("SAQR-SC history must be 1..8");
        if(shift<1 || shift>8) throw std::invalid_argument("SAQR-SC shift must be 1..8");
    }
};

// Per-source (network interface) state: M destination registers, an 8.8-bit
// EWMA of the repeat rate (0..256) and one hysteresis bit.
struct SrcState { std::array<int,8> dst{{-1,-1,-1,-1,-1,-1,-1,-1}}; int fill=0, head=0, ewma=0; bool adaptive=false; };

// Observe one injected packet's destination; returns the header bit (true = adaptive).
inline bool saqr_src_observe(SrcState& s,int dest,const SrcParams& p) {
    bool hit=false;
    for(int i=0;i<s.fill;++i) hit |= (s.dst[i]==dest);
    s.ewma += ((hit?256:0) - s.ewma) >> p.shift;
    if(s.ewma<0) s.ewma=0;                         // arithmetic shift of a negative step can undershoot by 1
    if(!s.adaptive && s.ewma>=p.on) s.adaptive=true;
    else if(s.adaptive && s.ewma<p.off) s.adaptive=false;
    s.dst[s.head]=dest; s.head=(s.head+1)%p.hist; if(s.fill<p.hist) ++s.fill;
    return s.adaptive;
}

// Route set for a packet given its header bit. Deterministic packets: exact XY
// over both class VCs (identical to the frozen XY route). Adaptive packets: the
// soft-O1TURN SAQR set (plan from the packet id, sticky as in §17).
inline RouteSet saqr_src_route(int cur,int dst,int k,bool adaptive,bool yx_plan) {
    if(adaptive) return saqr_o1turn_route(cur,dst,k,yx_plan);
    RouteSet rs; rs.add(xy(cur,dst,k),0,1,0); return rs;
}

} // namespace noc
