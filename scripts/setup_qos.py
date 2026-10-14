"""Build QoS in a separate BookSim tree; never mutate the active baseline build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from setup import patch

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=2); a=p.parse_args()
    baseline=ROOT/'.deps/booksim2/src'
    src=ROOT/'.deps/booksim2_qos/src'
    original=hashlib.sha256((baseline/'booksim').read_bytes()).hexdigest()
    if not src.exists():
        shutil.copytree(baseline,src,ignore=shutil.ignore_patterns('*.o','*.d','booksim','*.log'))
        (src.parent/'baseline.json').write_text(json.dumps(dict(binary_sha256=original,
            upstream_revision=subprocess.check_output(['git','-C',str(baseline.parent),'rev-parse','HEAD'],text=True).strip()),indent=2)+'\n')
    for file in (ROOT/'simulators/booksim_qos').glob('*.*'):
        if file.suffix in ('.hpp','.cpp'): shutil.copyfile(file,src/file.name)
    ext=src/'noc_extension.cpp'
    shutil.copyfile(baseline/'noc_extension.cpp',ext)
    patch(ext,'#include "noc_extension.hpp"','#include "noc_extension.hpp"\n#include "qos_runtime.hpp"')
    patch(ext,'if(inject) { outputs->AddRange(-1,0,vcs-1); return; }',
        'const int first=f->cl*(vcs/2), last=first+vcs/2-1;\n    if(inject) { outputs->AddRange(-1,first,last); return; }')
    patch(ext,'outputs->AddRange(p,0,vcs-1);','outputs->AddRange(p,first,last);')
    patch(ext,'const int first=f->cl*(vcs/2), last=first+vcs/2-1;',
        'const int first=f->cl*(vcs/qos_classes()), last=first+vcs/qos_classes()-1;')
    patch(ext,'config.GetInt("classes")!=1','config.GetInt("classes")!=2')
    patch(ext,'throw std::invalid_argument("NoC extension requires a 2D mesh and one traffic class");',
        'throw std::invalid_argument("QoS extension requires a 2D mesh and two traffic classes");\n    qos_initialize(config);')
    patch(ext,'config.GetInt("classes")!=2','(config.GetInt("classes")!=1 && config.GetInt("classes")!=2)')
    tm=src/'trafficmanager.cpp'
    patch(tm,'#include "noc_extension.hpp"','#include "noc_extension.hpp"\n#include "qos_runtime.hpp"')
    patch(tm,'void TrafficManager::_Inject(){','''void TrafficManager::_Inject(){
    if(qos_enabled()) {
        QosEvent event;
        while(qos_next_event(_time,event)) _GeneratePacket(event.source,1,event.cl,event.time);
        return;
    }''')
    patch(tm,'int packet_destination = _traffic_pattern[cl]->dest(source);',
        'int packet_destination = qos_enabled() ? qos_destination() : _traffic_pattern[cl]->dest(source);')
    patch(tm,'    for ( int i = 0; i < size; ++i ) {\n        Flit * f  = Flit::New();',
        '    qos_generated(pid,source,packet_destination,cl,time,size);\n    for ( int i = 0; i < size; ++i ) {\n        Flit * f  = Flit::New();')
    patch(tm,'        _partial_packets[source][cl].push_back( f );',
        '        qos_flit_created(f);\n        _partial_packets[source][cl].push_back( f );')
    patch(tm,'if(f && (f->pri >= cf->pri)) {',
        'if(f && !qos_prefers(qos_source_key(n),cf->pri,f->pri)) {')
    patch(tm,'                f->itime = _time;','                f->itime = _time;\n                qos_injected(f,_time);')
    patch(tm,'void TrafficManager::_RetireFlit( Flit *f, int dest )\n{',
        'void TrafficManager::_RetireFlit( Flit *f, int dest )\n{\n    qos_retired(f,dest);')
    patch(tm,'        noc_finish();','        noc_finish();\n        qos_finish();')
    arb=src/'arbiters/arbiter.cpp'
    patch(arb,'#include "arbiter.hpp"','#include "arbiter.hpp"\n#include "qos_arbiter.hpp"')
    patch(arb,'  if(arb_type == "round_robin") {',
        '  if(arb_type == "qos_weighted") {\n    a = new QosWeightedArbiter(parent,name,size);\n  } else if(arb_type == "round_robin") {')
    # Stable hierarchical names let the coalescing step consult the SAME output
    # scheduler state as the actual arbiter. This changes names, not allocations.
    sep=src/'allocators/separable.cpp'
    patch(sep,'ostringstream arb_name("arb_i");\n    arb_name << i;',
        'ostringstream arb_name;\n    arb_name << "arb_i" << i;')
    patch(sep,'ostringstream arb_name("arb_o");\n    arb_name << i;',
        'ostringstream arb_name;\n    arb_name << "arb_o" << i;')
    router=src/'routers/iq_router.cpp'
    patch(router,'#include "iq_router.hpp"','#include "iq_router.hpp"\n#include "qos_runtime.hpp"')
    patch(router,'    cur_buf->AddFlit(vc, f);','    qos_vc_check(f);\n    cur_buf->AddFlit(vc, f);')
    old='''if(RoundRobinArbiter::Supersedes(vc, prio, req.label, req.in_pri, 
				       _sw_rr_offset[expanded_input], _vcs)) {'''
    new='''if(qos_prefers(qos_output_key(FullName(),output),prio,req.in_pri) ||
         (prio==req.in_pri && RoundRobinArbiter::Supersedes(vc,prio,req.label,req.in_pri,
                                                        _sw_rr_offset[expanded_input],_vcs))) {'''
    patch(router,old,new)
    subprocess.run(['make',f'-j{a.jobs}'],cwd=src,check=True)
    require=hashlib.sha256((baseline/'booksim').read_bytes()).hexdigest()==original
    assert require,'Active baseline binary changed'
    provenance=dict(baseline_binary_sha256=original,qos_binary_sha256=hashlib.sha256((src/'booksim').read_bytes()).hexdigest(),
        sources_sha256={str(f.relative_to(src)):hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in src.rglob('*') if f.suffix in ('.cpp','.hpp','.l','.y')},
        note='Independent build with native BookSim timing, external demand replay and class-aware scheduling.')
    (src.parent/'build_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in provenance.items() if k!='sources_sha256'},indent=2))

if __name__=='__main__': main()
