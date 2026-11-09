#pragma once
// DBAR-style comparator: Destination-Based Adaptive Routing (Ma, Enright Jerger and Wang, HPCA 2011).
//
// Minimal adaptive routing in the Duato framework used by the study's Duato
// comparator: class VC offset 0 is the XY escape VC (packets in it stay there),
// offset 1 is the adaptive VC on either productive port. DBAR's contribution is
// port selection: the congestion of a candidate direction is aggregated over
// the routers along that dimension, truncated at the destination's coordinate
// (only the part of the row/column the packet will actually traverse counts).
//
// This model is IDEALIZED in DBAR's favour: congestion is read from every
// router's previous-cycle state with no propagation delay and full resolution
// (the original uses a narrow side network with one hop of delay per router).
// It is therefore an upper bound on DBAR's adaptivity information.
#include "../saqr/routing.hpp"

namespace noc {

// occ(router, port): class-local used credits on that router's output port (previous cycle).
template <class Occ>
inline int dbar_cost(int cur,int dst,int k,int port,const Occ& occ) {
    int hops = (port==E||port==W) ? std::abs(dst%k-cur%k) : std::abs(dst/k-cur/k);
    int sum=0, r=cur;
    for(int j=0;j<hops && r>=0;++j) { sum+=occ(r,port); r=neighbor(r,port,k); }
    return sum;
}

template <class Occ>
inline RouteSet dbar_route(int cur,int dst,int k,int in_vc_offset,const Occ& occ) {
    RouteSet rs;
    if(cur==dst) { rs.add(LOCAL,0,1,0); return rs; }
    int x=xy(cur,dst,k), a=productive_other(cur,dst,k,x);
    if(in_vc_offset==0) { rs.add(x,0,0,0); return rs; }          // escape stays escape
    int best=x;
    if(a>=0 && dbar_cost(cur,dst,k,a,occ)<dbar_cost(cur,dst,k,x,occ)) best=a;
    rs.add(best,1,1,1);                                           // adaptive VC on preferred port
    rs.add(x,0,0,0);                                              // escape VC on XY port
    rs.switched = best!=x;
    return rs;
}

} // namespace noc
