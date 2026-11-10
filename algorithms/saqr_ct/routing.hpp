#pragma once
// SAQR-CT: SAQR-C column cue combined with the SAQR-H cue under a transit-evidence gate
// (docs/SAQR_SPEC_V2.md §23). Research candidate.
//
// Builds on algorithms/saqr_col/routing.hpp (included, not modified).
//
// G6 (§22.6) showed the two cues fail on opposite patterns:
//   * SAQR-C keeps a source on XY unless its row converges on one turn column. That is right
//     where XY is balanced (bit complement, tornado, random flows), but it misses patterns whose
//     X segments are too short to be seen as transit (butterfly: at most one column), where
//     SAQR-H's repeat/hotspot cue was right (best or tied at every butterfly point);
//   * SAQR-H marks every repeating source adaptive, which is wrong exactly where the router sees
//     plenty of transit traffic spread over many columns.
// SAQR-CT therefore uses SAQR-H's bit only where the router has little transit evidence:
//   * per router, a count of transit observations since the last packet injected there, folded
//     at every injection into an 8-bit EWMA r of transit head flits per injected packet
//     (x/32 per packet, count capped at 8, weight 2^-3);
//   * header bit = column bit OR (SAQR-H bit AND r < threshold).
// Every route set is still one of the two SAQR-SC sets (exact XY, soft O1TURN), so the §9
// deadlock argument is unchanged.
#include "../saqr_col/routing.hpp"
#include <algorithm>

namespace noc {

constexpr int CT_UNIT=32;   // r = 32 means one transit head flit per injected packet

struct CtParams {
    int thr=-1;      // evidence threshold on r (x/32 per injected packet); < 0 disables SAQR-CT
    void validate() const {
        if(thr<0) return;
        if(thr<1 || thr>8*CT_UNIT) throw std::invalid_argument("SAQR-CT threshold must be 1..256");
    }
};

// Per-router transit evidence: observations since the last injection, and the EWMA.
struct CtState { int cnt=0, r=0; };

inline void saqr_ct_transit(CtState& s) { if(s.cnt<255) ++s.cnt; }

// Fold the transit count at an injection; returns true when the router has evidence (r >= thr).
inline bool saqr_ct_inject(CtState& s,const CtParams& p) {
    const int x=std::min(s.cnt,8)*CT_UNIT;
    s.r += (x - s.r) >> 3;
    if(s.r<0) s.r=0;
    s.cnt=0;
    return s.r>=p.thr;
}

// Header bit: column bit OR (SAQR-H bit AND no transit evidence).
inline bool saqr_ct_classify(bool col_bit,bool h_bit,bool evidence) {
    return col_bit || (h_bit && !evidence);
}

} // namespace noc
