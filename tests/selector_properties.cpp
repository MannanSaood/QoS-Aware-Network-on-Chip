#include "../algorithms/common/select.hpp"
#include <cassert>
#include <iostream>
#include <random>
int main() {
    // A full VC and three empty VCs: aggregate .25 must not suppress the flag.
    noc::Load q={{.25,0,.125,0}}, peak={{1,0,.5,0}};
    assert(noc::dyad(0,0,5,4,q)==noc::E); // legacy diluted signal
    assert(noc::select("dyad",0,0,5,4,q,peak)==noc::S);
    peak[0]=.599;
    assert(noc::select("dyad",0,0,5,4,q,peak)==noc::E);
    peak[0]=.6;
    assert(noc::select("dyad",0,0,5,4,q,peak)==noc::S);
    // A boundary dummy port cannot trigger adaptation.
    peak={{.5,1,.5,1}};
    assert(noc::select("dyad",0,0,5,4,q,peak)==noc::E);
    // Independently calculated TOPSIS closeness .3 (E), .7 (S).
    q={{.5,0,.25,0}}; peak={{.5,0,1,0}};
    assert(noc::topsis(0,0,5,4,q,peak)==noc::S);
    assert(noc::topsis(0,0,5,4,q,peak,{{.3,.7}})==noc::E);
    q={{0,0,0,0}};
    assert(noc::topsis(0,0,5,4,q,q)==noc::E);
    bool rejected=false;
    try { noc::topsis(0,0,5,4,q,q,{{0,0}}); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    std::mt19937 rng(913);
    for(int i=0;i<10000;++i) {
        for(int p=0;p<4;++p) {
            int sum=0,maximum=0;
            for(int v=0;v<4;++v) { int used=rng()%9; sum+=used; maximum=std::max(maximum,used); }
            q[p]=sum/32.0; peak[p]=maximum/8.0;
        }
        int actual=noc::topsis(0,0,5,4,q,peak);
        if(q[0]<=q[2] && peak[0]<=peak[2] && (q[0]<q[2] || peak[0]<peak[2])) assert(actual==noc::E);
        if(q[2]<=q[0] && peak[2]<=peak[0] && (q[2]<q[0] || peak[2]<peak[0])) assert(actual==noc::S);
        auto scaled=q; for(auto &value:scaled) value*=.25;
        assert(actual==noc::topsis(0,0,5,4,scaled,peak));
        assert(noc::topsis(0,0,5,4,q,peak,{{1,0}})==noc::dyad(0,0,5,4,q,0));
        assert(actual==noc::topsis(0,0,5,4,q,peak,{{7,3}}));
    }
    std::cout<<"PASS: DyAD dilution/threshold/boundary regressions; TOPSIS tradeoffs, ties, invalid weights and 10000 feasible credit-state properties\n";
}
