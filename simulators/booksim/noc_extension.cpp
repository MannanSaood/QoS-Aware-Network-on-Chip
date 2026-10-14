#include "noc_extension.hpp"
#include "noc_algorithms/common/select.hpp"
#include "routefunc.hpp"
#include "globals.hpp"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <numeric>

namespace {
int vcs=4, depth=8, side=4;
long long samples=0, congested=0, port_samples=0;
double occupancy=0, hop_sum=0;
std::vector<double> latencies;
std::vector<double> half_latencies[2];
std::vector<long long> initial_activity, final_activity;
int env_int(const char* key,int fallback) {
    const char* value=std::getenv(key); return value ? std::stoi(value) : fallback;
}
void route(const std::string& name,const Router* r,const Flit* f,OutputSet* outputs,bool inject) {
    outputs->Clear();
    if(inject) { outputs->AddRange(-1,0,vcs-1); return; }
    noc::Load q={{0,0,0,0}}, peak=q;
    if(name!="xy" && r->GetID()!=f->dest) {
        auto used=r->UsedCredits();
        for(int p=0;p<4;++p) if(noc::neighbor(r->GetID(),p,side)>=0) {
            q[p]=double(r->GetUsedCredit(p))/(vcs*depth);
            for(int v=0;v<vcs;++v) peak[p]=std::max(peak[p],double(used[p*vcs+v])/depth);
        }
    }
    int p=noc::select(name,f->src,r->GetID(),f->dest,side,q,peak);
    outputs->AddRange(p,0,vcs-1);
}
void xy(const Router*r,const Flit*f,int,OutputSet*o,bool i){route("xy",r,f,o,i);}
void dyad(const Router*r,const Flit*f,int,OutputSet*o,bool i){route("dyad",r,f,o,i);}
void topsis(const Router*r,const Flit*f,int,OutputSet*o,bool i){route("topsis",r,f,o,i);}
std::vector<long long> activity(const std::vector<Network*>& nets) {
    std::vector<long long> result;
    for(auto net:nets) for(auto ch:net->GetChannels()) {
        // Exclude boundary dummy channels; count only physical mesh links.
        if(!ch->GetSource() || !ch->GetSink() ||
           noc::neighbor(ch->GetSource()->GetID(),ch->GetSourcePort(),side)<0) continue;
        auto a=ch->GetActivity();
        result.push_back(std::accumulate(a.begin(),a.end(),0LL));
    }
    return result;
}
}
bool noc_fixed(){return std::getenv("NOC_MEASURE")!=nullptr;}
int noc_warmup(){return env_int("NOC_WARMUP",1000);}
int noc_measure(){return env_int("NOC_MEASURE",5000);}
void noc_register(const Configuration& config) {
    vcs=config.GetInt("num_vcs"); depth=config.GetInt("vc_buf_size"); side=config.GetInt("k");
    if(config.GetStr("topology")!="mesh" || config.GetInt("n")!=2 || config.GetInt("classes")!=1)
        throw std::invalid_argument("NoC extension requires a 2D mesh and one traffic class");
    gRoutingFunctionMap["noc_xy_mesh"]=&xy;
    gRoutingFunctionMap["noc_dyad_mesh"]=&dyad;
    gRoutingFunctionMap["noc_topsis_mesh"]=&topsis;
}
void noc_sample(const std::vector<Network*>& nets,int time) {
    if(!noc_fixed()) return;
    if(time==noc_warmup()) initial_activity=activity(nets);
    if(time==noc_warmup()+noc_measure()) final_activity=activity(nets);
    if(time<noc_warmup() || time>=noc_warmup()+noc_measure()) return;
    ++samples;
    // Match NS-2's 10-cycle occupancy sampling; link activity still covers every cycle.
    if((time-noc_warmup())%10!=0) return;
    for(auto net:nets) for(auto r:net->GetRouters()) for(int p=0;p<4;++p) {
        if(noc::neighbor(r->GetID(),p,side)<0) continue;
        double q=double(r->GetBufferOccupancy(p))/(vcs*depth);
        occupancy+=q; congested+=(q>=0.6); ++port_samples;
    }
}
void noc_retire(int arrival,int created,int hops,int,int) {
    if(noc_fixed() && arrival>=noc_warmup() && arrival<noc_warmup()+noc_measure()) {
        latencies.push_back(arrival-created); hop_sum+=hops-1;
        half_latencies[(arrival-noc_warmup())>=noc_measure()/2].push_back(arrival-created);
    }
}
void noc_finish() {
    const char* path=std::getenv("NOC_METRICS"); if(!path) return;
    std::sort(latencies.begin(),latencies.end());
    auto percentile=[](double p){return latencies.empty()?0:latencies[std::min(latencies.size()-1,size_t(std::ceil(p*latencies.size())-1))];};
    long long traversals=0; double peak_util=0;
    for(size_t i=0;i<initial_activity.size();++i) {
        long long count=final_activity.at(i)-initial_activity[i]; traversals+=count;
        peak_util=std::max(peak_util,double(count)/samples);
    }
    std::ofstream out(path); out<<std::setprecision(12);
    double half_p99[2]={0,0};
    for(int h=0;h<2;++h) {
        auto &values=half_latencies[h]; std::sort(values.begin(),values.end());
        if(!values.empty()) half_p99[h]=values[size_t(std::ceil(.99*values.size())-1)];
    }
    out<<"{\"delivered_packets\":"<<latencies.size()
       <<",\"first_half_delivered_packets\":"<<half_latencies[0].size()
       <<",\"second_half_delivered_packets\":"<<half_latencies[1].size()
       <<",\"first_half_p99_cycles\":"<<half_p99[0]
       <<",\"second_half_p99_cycles\":"<<half_p99[1]
       <<",\"latency_mean_cycles\":"<<(latencies.empty()?0:std::accumulate(latencies.begin(),latencies.end(),0.0)/latencies.size())
       <<",\"latency_p50_cycles\":"<<percentile(.50)<<",\"latency_p90_cycles\":"<<percentile(.90)
       <<",\"latency_p95_cycles\":"<<percentile(.95)<<",\"latency_p99_cycles\":"<<percentile(.99)
       <<",\"mean_hops\":"<<(latencies.empty()?0:hop_sum/latencies.size())
       <<",\"buffer_occupancy_pct\":"<<100*occupancy/port_samples
       <<",\"congested_port_time_pct\":"<<100.0*congested/port_samples
       <<",\"link_utilization_pct\":"<<100.0*traversals/(samples*initial_activity.size())
       <<",\"peak_link_utilization_pct\":"<<100*peak_util
       <<",\"measurement_cycles\":"<<samples<<",\"physical_directed_links\":"<<initial_activity.size()<<"}\n";
}
