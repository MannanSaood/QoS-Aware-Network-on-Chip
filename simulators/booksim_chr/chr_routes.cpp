#include "chr_routes.hpp"
#include "noc_algorithms/chr/routing.hpp"
#include "noc_algorithms/oefixed/routing.hpp"
#include "noc_extension.hpp"
#include "qos_runtime.hpp"
#include "routefunc.hpp"
#include "globals.hpp"
#include "iq_router.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>

namespace {
int vcs=4, depth=8, side=4, classes=2, packet_flits=5;
bool stateful=false;               // an EWMA/hysteresis route is active
noc::ChrParams params;
std::string active;
std::vector<noc::ChrState> states;
struct Counters { long long single=0, dual=0, pressured=0, switched=0, h_on=0, h_samples=0, h_transitions=0; };
Counters counters[noc::CHR_CLASSES];

int env_int(const char* key,int fallback) { const char* v=std::getenv(key); return v ? std::stoi(v) : fallback; }
bool in_window(int t) { return noc_fixed() && t>=noc_warmup() && t<noc_warmup()+noc_measure(); }
int per_class() { return vcs/classes; }
// Reachable class occupancy. With wait_for_tail_credit=1 a VC holds flits of at
// most one packet, so each VC peaks at min(depth, packet length) flits.
int class_capacity() { return per_class()*std::min(depth,packet_flits); }

void read_view(const Router* r,int cl,noc::ChrView& view) {
    auto used=r->UsedCredits();
    auto iq=dynamic_cast<const IQRouter*>(r);
    if(!iq) throw std::logic_error("CHR routes require the iq router");
    const int first=cl*per_class();
    for(int p=0;p<noc::CHR_DIRS;++p) {
        view[p]=noc::ChrPort{};
        if(noc::neighbor(r->GetID(),p,side)<0) continue;
        for(int v=first;v<first+per_class();++v) {
            int u=used[p*vcs+v];
            view[p].used+=u; view[p].peak=std::max(view[p].peak,u);
            view[p].free_vcs+=iq->ChrOutputVCFree(p,v) ? 1 : 0;
        }
    }
}

void route(const Router* r,const Flit* f,OutputSet* outputs,bool inject) {
    outputs->Clear();
    const int first=f->cl*per_class(), last=first+per_class()-1;
    if(inject) { outputs->AddRange(-1,first,last); return; }
    const int cur=r->GetID();
    int port;
    if(active=="oefixed") port=noc::oefixed(f->src,cur,f->dest,side);
    else {
        noc::ChrView view; read_view(r,f->cl,view);
        auto d=noc::chr_decide(f->src,cur,f->dest,side,f->cl,states.at(cur),params,view,class_capacity(),depth);
        port=d.port;
        if(in_window(GetSimTime()) && cur!=f->dest) {
            Counters& c=counters[f->cl];
            if(d.candidates==1) ++c.single; else ++c.dual;
            c.pressured+=d.pressured; c.switched+=d.switched;
        }
    }
    outputs->AddRange(port,first,last);
}
void oefixed(const Router*r,const Flit*f,int,OutputSet*o,bool i){route(r,f,o,i);}
void chr(const Router*r,const Flit*f,int,OutputSet*o,bool i){route(r,f,o,i);}
}

void chr_register(const Configuration& config) {
    vcs=config.GetInt("num_vcs"); depth=config.GetInt("vc_buf_size"); side=config.GetInt("k");
    classes=config.GetInt("classes"); packet_flits=config.GetInt("packet_size");
    if(config.GetInt("wait_for_tail_credit")!=1) throw std::invalid_argument("CHR capacity model assumes wait_for_tail_credit=1");
    if(classes<1 || classes>noc::CHR_CLASSES || vcs%classes) throw std::invalid_argument("CHR: invalid class/VC partition");
    gRoutingFunctionMap["noc_oefixed_mesh"]=&oefixed;
    for(auto name:{"chr","chr_cls","chr_hyst","chr_nofv"}) gRoutingFunctionMap[std::string("noc_")+name+"_mesh"]=&chr;
    std::string fn=config.GetStr("routing_function");
    active = fn.rfind("noc_",0)==0 ? fn.substr(4) : fn;
    if(active=="chr_cls") params.variant=noc::ChrVariant::Cls;
    else if(active=="chr_hyst") { params.variant=noc::ChrVariant::Hyst; params.margin=0; params.free_penalty=0; }
    else if(active=="chr_nofv") { params.variant=noc::ChrVariant::Full; params.free_penalty=0; }
    else if(active=="chr") params.variant=noc::ChrVariant::Full;
    // Tuning overrides (spec section 3.1 ranges); recorded by the runner.
    params.alpha_shift=env_int("NOC_CHR_ALPHA_SHIFT",params.alpha_shift);
    params.t_on=env_int("NOC_CHR_T_ON",params.t_on);
    params.t_off=env_int("NOC_CHR_T_OFF",params.t_off);
    if(active=="chr" || active=="chr_nofv") params.margin=env_int("NOC_CHR_MARGIN",params.margin);
    if(active=="chr") params.free_penalty=env_int("NOC_CHR_FREE_PENALTY",params.free_penalty);
    params.validate();
    stateful = active=="chr" || active=="chr_hyst" || active=="chr_nofv";
    states.assign(side*side,noc::ChrState{});
}

// Called at the start of every cycle, before routers step. A route decision in
// cycle t therefore reads filter state registered from credits up to t-1.
void chr_tick(const std::vector<Network*>& nets,int time) {
    if(!stateful) return;
    if(nets.size()!=1) throw std::logic_error("CHR expects one subnet");
    const bool count=in_window(time);
    for(auto r:nets[0]->GetRouters()) {
        auto used=r->UsedCredits();
        auto& st=states.at(r->GetID());
        for(int cl=0;cl<classes;++cl) for(int p=0;p<noc::CHR_DIRS;++p) {
            if(noc::neighbor(r->GetID(),p,side)<0) continue;
            int sum=0; for(int v=cl*per_class();v<(cl+1)*per_class();++v) sum+=used[p*vcs+v];
            int before=st.h[cl][p];
            noc::chr_update(st,params,cl,p,noc::chr_quantize(sum,class_capacity()));
            if(count) {
                Counters& c=counters[cl];
                ++c.h_samples; c.h_on+=st.h[cl][p]; c.h_transitions+=(st.h[cl][p]!=before);
            }
        }
    }
}

void chr_finish() {
    const char* path=std::getenv("NOC_CHR_METRICS"); if(!path) return;
    std::ofstream out(path);
    out<<"{\"route\":\""<<active<<"\",\"params\":{\"alpha_shift\":"<<params.alpha_shift<<",\"t_on\":"<<params.t_on
       <<",\"t_off\":"<<params.t_off<<",\"margin\":"<<params.margin<<",\"free_penalty\":"<<params.free_penalty
       <<",\"variant\":"<<int(params.variant)<<"},\"classes\":[";
    for(int cl=0;cl<classes;++cl) {
        const Counters& c=counters[cl];
        if(cl) out<<',';
        out<<"{\"class_id\":"<<cl<<",\"single_candidate_decisions\":"<<c.single<<",\"dual_candidate_decisions\":"<<c.dual
           <<",\"pressured_decisions\":"<<c.pressured<<",\"switched_decisions\":"<<c.switched
           <<",\"hysteresis_on_samples\":"<<c.h_on<<",\"hysteresis_samples\":"<<c.h_samples
           <<",\"hysteresis_transitions\":"<<c.h_transitions<<'}';
    }
    out<<"]}\n";
}
