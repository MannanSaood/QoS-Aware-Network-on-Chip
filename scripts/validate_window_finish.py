"""Prove skipping post-observation draining preserves every measured metric."""
import json
import os
import subprocess
from run_experiments import ROOT

out=ROOT/'results/validation/window_finish'; out.mkdir(parents=True,exist_ok=True)
checks=[]
for k,traffic,load in [(8,'uniform',.3),(32,'hotspot',.05)]:
    for alg in ['xy','dyad','topsis']:
        stem=f'booksim_{alg}_k{k}_{traffic}_l{load}_s1'
        raw=ROOT/f'results/scaling/cases/k{k}_{traffic}_l{load}_s1/raw'
        before=json.loads((raw/(stem+'.metrics.json')).read_text())
        target=out/(stem+'.json')
        env=dict(os.environ,NOC_WARMUP='500',NOC_MEASURE='1000',NOC_METRICS=str(target),NOC_SKIP_DRAIN='1')
        with (out/(stem+'.log')).open('w') as f:
            subprocess.run([str(ROOT/'.deps/booksim2/src/booksim'),str(raw/(stem+'.cfg'))],env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
        after=json.loads(target.read_text())
        assert before==after, (stem,before,after)
        checks.append(dict(case=stem,all_metrics_identical=True))
(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PASS: all metrics identical for six old/new fixed-window runs, including 32x32 hotspot.')
