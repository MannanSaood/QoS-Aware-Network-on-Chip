#pragma once
#include "../common/mesh.hpp"
namespace noc {
// D0 control (docs/CHR_OE_CANDIDATE_SPEC.md): always the first legal odd-even
// candidate. This is DyAD-OE's uncongested mode with adaptation removed. It
// differs from XY only on some final-column eastbound hops.
inline int oefixed(int src,int cur,int dst,int k) {
    return odd_even(src,cur,dst,k)[0];
}
}
