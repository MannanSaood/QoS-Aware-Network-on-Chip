#pragma once
// SAQR-C: turn-column convergence cue (docs/SAQR_SPEC_V2.md §22). Research candidate.
//
// Builds on algorithms/saqr_hot/routing.hpp (included, not modified).
//
// G5 (§21.6) showed that the SAQR-SC repeat cue fires on every permutation,
// but splitting XY/YX only pays off when XY concentrates load: XY overloads a
// row's links when many sources of that row turn into the same column (transpose,
// bit reversal: the destination column is a function of the source row). When
// row-mates turn at different columns (bit complement, tornado, random flows) XY
// already meets the bisection bound and the adaptive route set only costs VC capacity.
//
// SAQR-C measures exactly that convergence, locally, at every router:
//   * each router watches the destination column of every head flit that passes
//     through it (arrives from a neighbour) and still has an X distance to cover;
//   * one candidate-column register plus a 12-bit EWMA share f (x/4096), updated per
//     observed head flit: f rises when the column equals the candidate, decays otherwise;
//     while f < floor the candidate is replaced by the observed column (f = init);
//   * hysteresis on f gives a per-router "converging" bit (on / off).
// A packet injected at that router is marked adaptive when the router is converging
// and the packet's destination column is the convergent column (and differs from the
// source column). Optional mode 1 also marks hotspot-like sources: SAQR-H tracker bit
// set while the SAQR-SC repeat bit is clear (a source that favours one destination
// without being a pure permutation flow).
// The cue only chooses between the two SAQR-SC route sets (exact XY, soft O1TURN), both
// CTY-safe, so the §9 deadlock argument is unchanged.
#include "../saqr_hot/routing.hpp"

namespace noc {

struct ColParams {
    int on=-1;       // share threshold (x/4096) for the converging bit; < 0 disables SAQR-C
    int off=-1;      // hysteresis: clear below this
    int floor=-1;    // candidate replaceable while f < floor
    int init=-1;     // f assigned to a newly adopted candidate
    int shift=5;     // EWMA weight 2^-shift per observed head flit (1..8)
    int mode=0;      // 0: column cue only; 1: column cue OR (SAQR-H bit AND NOT SAQR-SC bit)
    void validate() const {
        if(on<0) return;
        if(off<0 || off>on || on>HOT_SCALE) throw std::invalid_argument("SAQR-C needs 0 <= off <= on <= 4096");
        if(floor<1 || init<floor || init>=off) throw std::invalid_argument("SAQR-C needs 1 <= floor <= init < off");
        if(shift<1 || shift>8) throw std::invalid_argument("SAQR-C shift must be 1..8");
        if(mode<0 || mode>1) throw std::invalid_argument("SAQR-C mode must be 0 or 1");
    }
};

// Per-router state: one column register, a 12-bit share, the converging bit.
struct ColState { int cand=-1, f=0; bool conv=false; };

// Observe the destination column of one transit head flit.
inline void saqr_col_observe(ColState& c,int col,const ColParams& p) {
    if(col==c.cand) c.f += (HOT_SCALE-c.f) >> p.shift;
    else            c.f -= c.f >> p.shift;
    if(c.f<p.floor && col!=c.cand) { c.cand=col; c.f=p.init; }
    if(!c.conv && c.f>=p.on) c.conv=true;
    else if(c.conv && c.f<p.off) c.conv=false;
}

// Column-cue bit for a packet injected at a router with column `src_col`.
inline bool saqr_col_bit(const ColState& c,int src_col,int dst_col) {
    return c.conv && dst_col==c.cand && dst_col!=src_col;
}

// Header bit. rep = SAQR-SC repeat bit, hot = SAQR-H tracker bit (both already computed).
inline bool saqr_col_classify(bool col_bit,bool rep,bool hot,const ColParams& p) {
    return p.mode==0 ? col_bit : (col_bit || (hot && !rep));
}

} // namespace noc
