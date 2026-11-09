#pragma once
// SAQR-H: SAQR-SC plus a hot-destination tracker (docs/SAQR_SPEC_V2.md §20). Research candidate.
//
// Builds on algorithms/saqr_src/routing.hpp (included, not modified).
//
// SAQR-SC marks a source adaptive only when it keeps repeating recent
// destinations (permutation flows). Hotspot sources send a fixed share of
// their packets to one node and the rest uniformly, so their repeat rate stays
// low and SAQR-SC routes them as XY, which loses to adaptive routes near the
// hot sink (§19.6). SAQR-H adds one open-loop signal per source: the share of
// its packets that go to its single most frequent recent destination.
//   * candidate: one destination register plus a 12-bit EWMA share f (x/4096);
//   * f rises when a packet goes to the candidate and decays otherwise;
//   * when f falls below `floor`, the candidate is replaced, but only by a
//     destination that also repeats one of the source's last M destinations
//     (so a spread source keeps replacing it with chance repeats and f never builds up);
//   * hysteresis on f (on / off) gives a second header bit; the packet is adaptive
//     if either the SAQR-SC bit or this bit is set.
// The signal depends only on destinations the source chose, never on routing,
// and every route set used is the SAQR-SC set (CTY-safe), so the §9 deadlock
// argument is unchanged.
#include "../saqr_src/routing.hpp"

namespace noc {

constexpr int HOT_SCALE=4096;

struct HotParams {
    int on=-1;       // share threshold (x/4096) to mark adaptive; < 0 disables the tracker
    int off=-1;      // hysteresis: unmark below this, 0 <= off <= on
    int floor=-1;    // candidate is replaceable while f < floor
    int init=-1;     // f assigned to a newly adopted candidate, floor <= init <= on
    int shift=4;     // EWMA weight 2^-shift per injected packet (1..8)
    void validate() const {
        if(on<0) return;
        if(off<0 || off>on || on>HOT_SCALE) throw std::invalid_argument("SAQR-H needs 0 <= off <= on <= 4096");
        if(floor<1 || init<floor || init>on) throw std::invalid_argument("SAQR-H needs 1 <= floor <= init <= on");
        if(shift<1 || shift>8) throw std::invalid_argument("SAQR-H shift must be 1..8");
    }
};

// Per-source state: one destination register, a 12-bit share and a hysteresis bit.
struct HotState { int cand=-1, f=0; bool adaptive=false; };

// Does `dest` repeat one of the last M destinations (SAQR-SC history, before it records `dest`)?
inline bool saqr_hot_history_hit(const SrcState& s,int dest) {
    bool hit=false;
    for(int i=0;i<s.fill;++i) hit |= (s.dst[i]==dest);
    return hit;
}

// Observe one injected packet; returns the tracker's bit.
inline bool saqr_hot_observe(HotState& h,int dest,bool history_hit,const HotParams& p) {
    if(dest==h.cand) h.f += (HOT_SCALE-h.f) >> p.shift;
    else             h.f -= h.f >> p.shift;
    if(h.f<p.floor && history_hit && dest!=h.cand) { h.cand=dest; h.f=p.init; }
    if(!h.adaptive && h.f>=p.on) h.adaptive=true;
    else if(h.adaptive && h.f<p.off) h.adaptive=false;
    return h.adaptive;
}

// Header bit for one injected packet: SAQR-SC classifier OR hot tracker.
inline bool saqr_hot_classify(SrcState& s,HotState& h,int dest,const SrcParams& sp,const HotParams& hp) {
    const bool hit=saqr_hot_history_hit(s,dest);          // before the SAQR-SC history records dest
    const bool hot = hp.on>=0 ? saqr_hot_observe(h,dest,hit,hp) : false;
    const bool rep = saqr_src_observe(s,dest,sp);
    return rep || hot;
}

} // namespace noc
