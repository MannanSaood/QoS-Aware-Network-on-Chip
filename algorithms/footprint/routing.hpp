#pragma once
// Footprint-style comparator (Fu and Kim, "Footprint: Regulating Routing
// Adaptiveness in Networks-on-Chip", HPCA 2017).
//
// Minimal adaptive routing in the same Duato framework as the study's Duato
// comparator: class VC offset 0 = XY escape VC (packets in it stay there),
// offset 1 = adaptive VC on either productive port. Footprint's idea is to
// regulate adaptiveness under congestion: when no productive port has a free
// adaptive VC, a packet follows the "footprint" of earlier packets to the same
// destination (the port whose adaptive VC currently holds such a packet)
// instead of spreading over every congested path, which confines congestion
// trees. With a free adaptive VC available it behaves like Duato (least local
// occupancy).
//
// Model notes: one adaptive VC per class per port, so the footprint VC is that
// VC; the footprint of a port is the destination of the last packet that
// entered its adaptive VC, valid while that VC is occupied.
#include "../saqr/routing.hpp"

namespace noc {

struct FootprintPort {
    int used=0;          // class-local used credits on the port (both class VCs)
    int adaptive_used=0; // used credits of the adaptive VC (offset 1)
    int fp_dest=-1;      // footprint: destination of the packet holding the adaptive VC
};
using FootprintView = std::array<FootprintPort,4>;

inline RouteSet footprint_route(int cur,int dst,int k,int in_vc_offset,const FootprintView& v,int cap) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(in_vc_offset==0) { rs.add(x,0,0,0); return rs; }          // escape stays escape
    int best=x;
    if(a>=0) {
        const bool fx = v[x].adaptive_used==0, fa = v[a].adaptive_used==0;
        if(fx || fa) {                                           // a free adaptive VC exists: Duato selection
            if(fx && fa) best = chr_quantize(v[a].used,cap)<chr_quantize(v[x].used,cap) ? a : x;
            else best = fa ? a : x;
        } else {                                                 // congested: follow the footprint
            const bool px = v[x].fp_dest==dst, pa = v[a].fp_dest==dst;
            if(pa && !px) best=a;
            else if(px) best=x;
            else best = chr_quantize(v[a].used,cap)<chr_quantize(v[x].used,cap) ? a : x;
        }
    }
    rs.add(best,1,1,1);
    rs.add(x,0,0,0);
    rs.switched = best!=x;
    return rs;
}

} // namespace noc
