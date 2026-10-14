#pragma once
#include "../common/mesh.hpp"
namespace noc {
inline int dyad(int src,int cur,int dst,int k,const Load& q,const Load& peak,double threshold=0.6) {
    auto ports=odd_even(src,cur,dst,k);
    if(ports.size()==1) return ports[0];
    bool congested=false;
    for(int p=0;p<4;++p)
        if(neighbor(cur,p,k)>=0 && peak[p]>=threshold) congested=true;
    // Trigger on the busiest downstream VC, then rank legal ports by total use.
    // Averaging over VCs would hide a full FIFO behind other empty FIFOs.
    // Both modes are subsets of OE; XY+OE switching is not deadlock safe.
    if(!congested) return ports[0];
    return *std::min_element(ports.begin(),ports.end(),
        [&](int a,int b){ return q[a]<q[b]; });
}
// Single-FIFO compatibility (and explicit legacy aggregate-signal experiments).
inline int dyad(int src,int cur,int dst,int k,const Load& q,double threshold=0.6) {
    return dyad(src,cur,dst,k,q,q,threshold);
}
}
