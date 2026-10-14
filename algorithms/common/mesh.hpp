#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace noc {
// BookSim port convention: +X, -X, +Y, -Y, local.
enum Port { E=0, W=1, S=2, N=3, LOCAL=4 };
using Load = std::array<double,4>;
inline int neighbor(int id, int p, int k) {
    int x=id%k, y=id/k;
    if(p==E && x+1<k) return id+1;
    if(p==W && x>0) return id-1;
    if(p==S && y+1<k) return id+k;
    if(p==N && y>0) return id-k;
    return -1;
}
inline int distance(int a,int b,int k) {
    return std::abs(a%k-b%k)+std::abs(a/k-b/k);
}
// Minimal odd-even candidates, with the destination-column lookahead rule.
// That rule prevents entering a forbidden even-column E->N/S turn later.
inline std::vector<int> odd_even(int src,int cur,int dst,int k) {
    if(cur==dst) return {LOCAL};
    int x=cur%k, dx=dst%k-x, dy=dst/k-cur/k;
    int vertical=dy>0 ? S:N;
    std::vector<int> out;
    if(dx==0) out.push_back(vertical);
    else if(dx>0) {
        if(dy==0) out.push_back(E);
        else {
            if((dst%k)%2==1 || dx!=1) out.push_back(E);
            if(x%2==1 || x==src%k) out.push_back(vertical);
        }
    } else {
        out.push_back(W);
        if(x%2==0 && dy!=0) out.push_back(vertical);
    }
    if(out.empty()) throw std::logic_error("empty odd-even route");
    return out;
}
}
