#include "../algorithms/common/select.hpp"
#include <cassert>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <random>
int main() {
    long long routes=0;
    // Explore EVERY reachable OE branch for all source/destination pairs.
    // Build the union channel-dependency graph and check it is acyclic.
    for(int k:{2,3,4,5,8}) {
        std::map<int,std::set<int>> edges;
        for(int src=0;src<k*k;++src) for(int dst=0;dst<k*k;++dst) {
            std::set<std::pair<int,int>> visited;
            std::function<void(int,int)> visit=[&](int cur,int incoming) {
                if(cur==dst || !visited.insert({cur,incoming}).second) return;
                auto ports=noc::odd_even(src,cur,dst,k);
                assert(!ports.empty());
                for(int p:ports) {
                    int next=noc::neighbor(cur,p,k); assert(next>=0);
                    assert(noc::distance(next,dst,k)==noc::distance(cur,dst,k)-1);
                    int channel=cur*4+p;
                    if(incoming>=0) edges[incoming].insert(channel);
                    visit(next,channel);
                }
            };
            visit(src,-1); ++routes;
        }
        std::map<int,int> color;
        std::function<void(int)> dfs=[&](int v){
            assert(color[v]!=1); if(color[v]==2) return;
            color[v]=1; for(int w:edges[v]) dfs(w); color[v]=2;
        };
        for(auto edge:edges) dfs(edge.first);
    }
    noc::Load q={{.8,0,.1,0}}, peak=q;
    assert(noc::xy(0,5,4)==noc::E);
    assert(noc::dyad(0,0,5,4,q)==noc::S);
    assert(noc::topsis(0,0,5,4,q,peak)==noc::S);
    q={{0,0,0,0}};
    assert(noc::dyad(0,0,5,4,q)==noc::E);
    assert(noc::topsis(0,0,5,4,q,q)==noc::E);
    // Fixed/seeded varied loads, large meshes, every selected step must be minimal.
    std::mt19937 rng(42); std::uniform_real_distribution<double> load(0,1);
    for(int k:{3,4,8,16,32}) for(int trial=0;trial<10000;++trial) {
        int s=rng()%(k*k),d=rng()%(k*k);
        for(auto name:{"xy","dyad","topsis"}) {
            int c=s,steps=0;
            while(c!=d) {
                for(int p=0;p<4;++p){q[p]=load(rng);peak[p]=load(rng);}
                int p=noc::select(name,s,c,d,k,q,peak), n=noc::neighbor(c,p,k);
                assert(n>=0 && noc::distance(n,d,k)+1==noc::distance(c,d,k));
                c=n; assert(++steps<=2*(k-1));
            }
        }
    }
    std::cout<<"PASS: "<<routes<<" exhaustive OE pairs, acyclic dependency graphs through 8x8, 150000 route trials through 32x32\n";
}
