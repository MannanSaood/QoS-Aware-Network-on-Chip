#pragma once
#include "../xy/routing.hpp"
#include "../dyad/routing.hpp"
#include "../topsis/routing.hpp"
#include <string>
namespace noc {
inline int select(const std::string& name,int src,int cur,int dst,int k,
                  const Load& q,const Load& peak) {
    if(name=="xy") return xy(cur,dst,k);
    if(name=="dyad") return dyad(src,cur,dst,k,q,peak);
    if(name=="topsis") return topsis(src,cur,dst,k,q,peak);
    throw std::invalid_argument("unknown algorithm: "+name);
}
}
