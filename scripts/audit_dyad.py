"""Diagnostic only: instrument a separate BookSim build; leave study binary unchanged."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from run_experiments import ROOT, invoke

def main():
    output=ROOT/'results/dyad_audit'; output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='noc-audit-') as scratch:
        src=Path(scratch)/'src'
        shutil.copytree(ROOT/'.deps/booksim2/src',src)
        extension=src/'noc_extension.cpp'
        code=extension.read_text().replace('int vcs=4, depth=8, side=4;', '''int vcs=4, depth=8, side=4;
bool audit_window=false;
long long audit_choices=0, audit_triggered=0, audit_changed=0, audit_peak_only=0;
double audit_threshold=.6;''')
        code=code.replace('int p=noc::select(name,f->src,r->GetID(),f->dest,side,q,peak);', '''int p=noc::select(name,f->src,r->GetID(),f->dest,side,q,peak);
    if(name=="dyad") {
        p=noc::dyad(f->src,r->GetID(),f->dest,side,q,audit_threshold);
        auto candidates=noc::odd_even(f->src,r->GetID(),f->dest,side);
        if(audit_window && candidates.size()>1) {
            ++audit_choices;
            double aggregate=*std::max_element(q.begin(),q.end());
            double vc_peak=*std::max_element(peak.begin(),peak.end());
            audit_triggered+=(aggregate>=audit_threshold);
            audit_peak_only+=(aggregate<audit_threshold && vc_peak>=audit_threshold);
            audit_changed+=(p!=candidates[0]);
        }
    }''')
        code=code.replace('vcs=config.GetInt("num_vcs");', '''if(std::getenv("NOC_DYAD_THRESHOLD")) audit_threshold=std::stod(std::getenv("NOC_DYAD_THRESHOLD"));
    vcs=config.GetInt("num_vcs");''')
        code=code.replace('if(!noc_fixed()) return;', '''if(!noc_fixed()) return;
    audit_window=time>=noc_warmup() && time<noc_warmup()+noc_measure();''')
        code=code.replace('std::sort(latencies.begin(),latencies.end());', '''std::ofstream audit(std::string(path)+".audit.json");
    audit<<"{\\"choices\\":"<<audit_choices<<",\\"triggered\\":"<<audit_triggered
         <<",\\"changed\\":"<<audit_changed<<",\\"peak_only\\":"<<audit_peak_only<<"}";
    std::sort(latencies.begin(),latencies.end());''')
        extension.write_text(code)
        subprocess.run(['make','-j2'],cwd=src,check=True,stdout=(output/'build.log').open('w'),stderr=subprocess.STDOUT)
        rows=[]
        for traffic in ['uniform','transpose']:
            for threshold in [.6,.2,0.0]:
                stem=f'{traffic}_threshold{threshold}'
                config=output/(stem+'.cfg')
                original=ROOT/'results/scaling/cases/k8_uniform_l0.3_s1/raw/booksim_dyad_k8_uniform_l0.3_s1.cfg'
                config.write_text(original.read_text().replace('traffic = uniform;',f'traffic = {traffic};'))
                metrics=output/(stem+'.json')
                env=dict(os.environ,NOC_WARMUP='1000',NOC_MEASURE='3000',NOC_METRICS=str(metrics),NOC_DYAD_THRESHOLD=str(threshold))
                wall,status=invoke([str(src/'booksim'),str(config)],output/(stem+'.log'),env)
                row=dict(traffic=traffic,threshold=threshold,seed=1,status=status,wall_seconds=wall)
                if status=='ok':
                    row.update(json.loads(metrics.read_text())); row.update(json.loads(Path(str(metrics)+'.audit.json').read_text()))
                rows.append(row); print(row,flush=True)
        (output/'audit.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__': main()
