#pragma once
#include "../common/mesh.hpp"
namespace noc {
// Full vector-normalized TOPSIS. Both criteria are costs:
// total occupancy and maximum individual-VC occupancy (queue pressure).
// Path length is deliberately omitted: it is identical for minimal candidates.
inline int topsis(int src,int cur,int dst,int k,const Load& q,const Load& peak,
                  std::array<double,2> weights={{0.7,0.3}}) {
    auto ports=odd_even(src,cur,dst,k);
    if(ports.size()==1) return ports[0];
    if(weights[0]<0 || weights[1]<0 || weights[0]+weights[1]<=0)
        throw std::invalid_argument("TOPSIS weights must be nonnegative with positive sum");
    double sum=weights[0]+weights[1];
    for(auto &w:weights) w/=sum;
    std::vector<std::array<double,2>> values;
    for(int p:ports) values.push_back({{q[p],peak[p]}});
    for(int j=0;j<2;++j) {
        double norm=0;
        for(auto v:values) norm+=v[j]*v[j];
        norm=std::sqrt(norm);
        for(auto &v:values) v[j]=norm>0 ? weights[j]*v[j]/norm : 0;
    }
    std::array<double,2> best=values[0], worst=values[0];
    for(auto v:values) for(int j=0;j<2;++j) {
        best[j]=std::min(best[j],v[j]); worst[j]=std::max(worst[j],v[j]);
    }
    int winner=ports[0]; double score=-1;
    for(size_t i=0;i<ports.size();++i) {
        double db=0,dw=0;
        for(int j=0;j<2;++j) {
            db+=std::pow(values[i][j]-best[j],2);
            dw+=std::pow(values[i][j]-worst[j],2);
        }
        db=std::sqrt(db); dw=std::sqrt(dw);
        double c=db+dw>0 ? dw/(db+dw) : 0.5;
        if(c>score) {score=c; winner=ports[i];}
    }
    return winner;
}
}
