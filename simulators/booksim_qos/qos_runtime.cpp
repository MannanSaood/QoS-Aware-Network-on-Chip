#include "qos_runtime.hpp"
#include "qos_policy.hpp"
#include "noc_extension.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace {
struct Packet { int born,src,dst,cl,size,inject=-1,arrive=-1,retired=0; };
struct Payload { uint64_t value; int id,pid,cl; };
std::vector<QosEvent> events;
std::vector<Packet> packets;
std::unordered_map<std::string,qos::Schedule> schedules;
std::vector<int> latency[2], halves[2][2];
long long ejected[2]={0,0}, injected_flits[2]={0,0}, payload_checks=0, vc_checks=0;
size_t cursor=0;
int next_destination=-1, k=0, vcs=0, target=0, classes=2;
std::string mode;
std::ofstream event_log;
void require(bool condition,const char* message) { if(!condition) throw std::runtime_error(message); }
bool window(int t) { return t>=noc_warmup() && t<noc_warmup()+noc_measure(); }
uint64_t tag(int id,int pid,int cl) {
    uint64_t x=uint64_t(id+1)*0x9e3779b97f4a7c15ULL ^ uint64_t(pid+1)*0xbf58476d1ce4e5b9ULL ^ uint64_t(cl);
    x^=x>>30; x*=0xbf58476d1ce4e5b9ULL; x^=x>>27; x*=0x94d049bb133111ebULL; return x^(x>>31);
}
void log(char type,int pid,int time,int cl) { if(event_log) event_log<<type<<','<<pid<<','<<time<<','<<cl<<'\n'; }
double mean(const std::vector<int>& v) { return v.empty()?0:std::accumulate(v.begin(),v.end(),0.0)/v.size(); }
int percentile(const std::vector<int>& sorted,double p) { return sorted.empty()?0:sorted[size_t(std::ceil(sorted.size()*p))-1]; }
}
bool qos_enabled() { return std::getenv("NOC_TRACE")!=nullptr; }
int qos_classes() { return classes; }
void qos_initialize(const Configuration& config) {
    require(qos_enabled(),"QoS build requires NOC_TRACE");
    k=config.GetInt("k"); vcs=config.GetInt("num_vcs"); target=16*k;
    classes=config.GetInt("classes");
    require((classes==1 || classes==2) && vcs>=classes && vcs%classes==0,"Invalid class/VC partition");
    require(config.GetInt("subnets")==1 && config.GetInt("hold_switch_for_packet")==0,"QoS requires one subnet and no packet switch hold");
    require(config.GetStr("priority")=="class","Replay priority must propagate into router VCs (priority=class)");
    mode=std::getenv("NOC_QOS_MODE")?std::getenv("NOC_QOS_MODE"):"weighted";
    require(classes==2 || mode=="age","Single-class calibration requires age mode");
    require(mode=="weighted" || mode=="age" || mode=="aged" || mode=="strict","Unknown QoS scheduling mode");
    require((config.GetStr("arb_type")=="qos_weighted")== (mode=="weighted"),"Arbiter and QoS policy mismatch");
    std::ifstream in(std::getenv("NOC_TRACE")); require(bool(in),"Cannot read demand trace");
    QosEvent e; int last=-1;
    while(in>>e.time>>e.source>>e.dest>>e.cl) {
        require(e.time>=last && e.time>=0 && e.time<noc_warmup()+noc_measure(),"Trace time/order error");
        require(e.source>=0 && e.source<k*k && e.dest>=0 && e.dest<k*k && e.cl>=0 && e.cl<classes,"Invalid trace event");
        events.push_back(e); last=e.time;
    }
    require(in.eof(),"Malformed trace");
    if(const char* path=std::getenv("NOC_QOS_EVENTS")) { event_log.open(path); require(bool(event_log),"Cannot write event log"); }
}
bool qos_next_event(int time,QosEvent& e) {
    if(cursor==events.size() || events[cursor].time>time) return false;
    require(events[cursor].time==time,"Skipped demand event");
    e=events[cursor++]; next_destination=e.dest; return true;
}
int qos_destination() { return next_destination; }
int qos_priority(int cl,int born) { return qos::priority(cl,born,mode,k); }
bool qos_prefers(const std::string& key,int a,int b) {
    return mode=="weighted" ? schedules[key].prefer(a,b) : a>b;
}
void qos_grant(const std::string& key,int p) { if(mode=="weighted") schedules[key].grant(qos::tagged_class(p)); }
std::string qos_source_key(int source) { return "source/"+std::to_string(source); }
std::string qos_output_key(const std::string& router,int output) {
    return router+"/sw_allocator/arb_o"+std::to_string(output);
}
void qos_generated(int pid,int source,int dest,int cl,int born,int size) {
    require(pid==int(packets.size()),"Packet IDs are not contiguous");
    Packet p; p.born=born; p.src=source; p.dst=dest; p.cl=cl; p.size=size; packets.push_back(p);
    log('G',pid,born,cl);
}
void qos_flit_created(Flit* f) {
    f->pri=qos_priority(f->cl,f->ctime);
    f->data=new Payload{tag(f->id,f->pid,f->cl),f->id,f->pid,f->cl};
}
void qos_vc_check(const Flit* f) {
    require(f->vc>=f->cl*(vcs/classes) && f->vc<(f->cl+1)*(vcs/classes),"Flit crossed its class VC partition"); ++vc_checks;
}
void qos_injected(const Flit* f,int time) {
    qos_vc_check(f);
    qos_grant(qos_source_key(f->src),f->pri);
    if(window(time)) ++injected_flits[f->cl];
    if(f->head) {
        Packet& p=packets.at(f->pid); require(p.inject<0,"Duplicate head injection"); p.inject=time;
        log('I',f->pid,time,f->cl);
    }
}
void qos_retired(Flit* f,int dest) {
    qos_vc_check(f);
    Packet& p=packets.at(f->pid);
    require(p.src==f->src && p.dst==dest && p.cl==f->cl && p.born==f->ctime,"Flit identity/destination mismatch");
    Payload* payload=static_cast<Payload*>(f->data);
    require(payload && payload->id==f->id && payload->pid==f->pid && payload->cl==f->cl && payload->value==tag(f->id,f->pid,f->cl),"Payload tag corruption");
    delete payload; f->data=nullptr; ++payload_checks;
    require(++p.retired<=p.size,"Duplicate flit retirement");
    if(window(f->atime)) ++ejected[f->cl];
    if(f->tail) {
        require(p.retired==p.size && p.arrive<0 && p.inject>=0,"Incomplete/duplicate packet retirement");
        p.arrive=f->atime; log('D',f->pid,f->atime,f->cl);
        if(window(f->atime)) {
            latency[f->cl].push_back(f->atime-f->ctime);
            halves[f->cl][(f->atime-noc_warmup())>=noc_measure()/2].push_back(f->atime-f->ctime);
        }
    }
}
void qos_finish() {
    require(cursor==events.size() && packets.size()==events.size(),"Trace not fully generated");
    const char* path=std::getenv("NOC_QOS_METRICS"); require(path,"Missing QoS metric output");
    std::ofstream out(path); require(bool(out),"Cannot write QoS metrics"); out<<std::setprecision(12);
    const int end=noc_warmup()+noc_measure();
    out<<"{\"mode\":\""<<mode<<"\",\"trace_packets\":"<<events.size()<<",\"payload_checks\":"<<payload_checks
       <<",\"vc_checks\":"<<vc_checks<<",\"integrity_errors\":0,\"classes\":[";
    for(int cl=0;cl<2;++cl) {
        long long gen=0,inj=0,del=0,start=0,pending=0,source=0,eligible=0,on_time=0,censored=0,cohort_delivered=0;
        int oldest=0; std::vector<long long> demand(k*k,0),served(k*k,0);
        for(const Packet& p:packets) if(p.cl==cl) {
            if(window(p.born)) {
                ++gen;
                if(p.arrive>=0) ++cohort_delivered;
                if(p.born+target<end) {
                    ++eligible; ++demand[p.src];
                    if(p.arrive>=0) ++served[p.src];
                    if(p.arrive>=0 && p.arrive<=p.born+target) ++on_time;
                } else ++censored;
            }
            if(window(p.inject)) ++inj;
            if(window(p.arrive)) ++del;
            if(p.born<noc_warmup() && (p.arrive<0 || p.arrive>=noc_warmup())) ++start;
            if(p.arrive<0) { ++pending; source+=(p.inject<0); oldest=std::max(oldest,end-1-p.born); }
        }
        require(gen+start==del+pending,"Window packet conservation failure");
        require(del==static_cast<long long>(latency[cl].size()),"Latency population mismatch");
        double sum=0,squares=0; int flows=0;
        for(int src=0;src<k*k;++src) if(demand[src]) { double r=double(served[src])/demand[src]; sum+=r; squares+=r*r; ++flows; }
        std::sort(latency[cl].begin(),latency[cl].end());
        for(int h=0;h<2;++h) std::sort(halves[cl][h].begin(),halves[cl][h].end());
        if(cl) out<<',';
        out<<"{\"class_id\":"<<cl<<",\"generated_packets\":"<<gen<<",\"injected_packets\":"<<inj
           <<",\"delivered_packets\":"<<del<<",\"pending_start\":"<<start<<",\"pending_end\":"<<pending
           <<",\"pending_at_source\":"<<source<<",\"pending_in_network\":"<<pending-source
           <<",\"oldest_pending_age_cycles\":"<<oldest<<",\"cohort_delivered_packets\":"<<cohort_delivered
           <<",\"target_cycles\":"<<target<<",\"target_eligible_packets\":"<<eligible
           <<",\"target_on_time_packets\":"<<on_time<<",\"target_missed_packets\":"<<eligible-on_time
           <<",\"target_censored_packets\":"<<censored<<",\"target_is_deadline\":"<<(cl==0?"true":"false")
           <<",\"ejected_flits\":"<<ejected[cl]<<",\"injected_flits\":"<<injected_flits[cl]
           <<",\"latency_mean_cycles\":"<<mean(latency[cl])<<",\"latency_p50_cycles\":"<<percentile(latency[cl],.5)
           <<",\"latency_p90_cycles\":"<<percentile(latency[cl],.9)<<",\"latency_p99_cycles\":"<<percentile(latency[cl],.99)
           <<",\"first_half_delivered\":"<<halves[cl][0].size()<<",\"second_half_delivered\":"<<halves[cl][1].size()
           <<",\"first_half_p99_cycles\":"<<percentile(halves[cl][0],.99)<<",\"second_half_p99_cycles\":"<<percentile(halves[cl][1],.99)
           <<",\"within_class_delivery_fairness\":";
        if(flows && squares>0) out<<sum*sum/(flows*squares); else out<<"null";
        out<<",\"fairness_active_sources\":"<<flows<<'}';
    }
    out<<"]}\n";
}
