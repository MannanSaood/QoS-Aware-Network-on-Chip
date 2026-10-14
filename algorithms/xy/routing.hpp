#pragma once
#include "../common/mesh.hpp"
namespace noc {
inline int xy(int cur,int dst,int k) {
    if(cur%k<dst%k) return E;
    if(cur%k>dst%k) return W;
    if(cur/k<dst/k) return S;
    if(cur/k>dst/k) return N;
    return LOCAL;
}
}
