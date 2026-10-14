"""Prepare one focused, measured BookSim/NS-2 model-constraint comparison."""
import csv
import itertools
import json
import math
import numpy as np
from scipy.stats import t
from run_experiments import ROOT,execution_profile

source=ROOT/'results/scaling/metrics.csv'
with source.open() as f:
    rows=[r for r in csv.DictReader(f) if r['traffic']=='hotspot' and r['algorithm']=='xy'
          and float(r['offered_flits_per_node_cycle'])==.3]
expected=set(itertools.product(['booksim','ns2'],[4,8,16,32],[1,2,3])); actual=set()
for r in rows:
    key=(r['simulator'],int(r['mesh_k']),int(r['seed']))
    assert key not in actual; actual.add(key)
    assert r['status']=='ok' and r['execution_profile']==execution_profile(r['simulator'],'hotspot')
    assert int(r['warmup_cycles'])==500 and int(r['measurement_cycles'])==1000
    assert int(r['packet_flits'])==5
    if r['simulator']=='booksim':
        assert float(r['throughput_flits_per_node_cycle'])*int(r['nodes'])<=1.005+1e-9
assert actual==expected,('Incomplete selected model comparison',len(actual),len(expected))
series=[]
for engine,label in [('booksim','BookSim'),('ns2','NS-2 packet model')]:
    means=[]; cis=[]
    for k in [4,8,16,32]:
        values=np.array([float(r['throughput_flits_per_node_cycle'])*k*k for r in rows
                         if r['simulator']==engine and int(r['mesh_k'])==k])
        assert len(values)==3 and all(math.isfinite(v) for v in values)
        means.append(float(values.mean())); cis.append(float(t.ppf(.975,2)*values.std(ddof=1)/np.sqrt(3)))
    series.append(dict(label=label,mean=means,ci95=cis))
out=ROOT/'results/model_comparison'; out.mkdir(parents=True,exist_ok=True)
with (out/'measured_runs.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
(out/'figure_data.json').write_text(json.dumps(dict(meshes=[4,8,16,32],series=series),indent=2)+'\n')
(out/'README.md').write_text('''# Shared destination-capacity diagnostic

One metric, one line chart, 24 actual runs: XY, all-to-one center hotspot,
four mesh sizes, two simulators, three seeds, offered injection 0.3 flits/node/cycle.
This separate diagnostic uses 500 warm-up and 1000 observation cycles.
The y-axis is aggregate delivered throughput (flits/cycle), not per-node throughput.
BookSim has a shared one-flit/cycle destination ejection interface. The current
NS-2 adapter has separate ingress links and no shared ejection server. It can
therefore exceed that NoC constraint. This demonstrates a specific modeling
omission, not an accuracy percentage or a general defect in NS-2.
The experiment is separate from the main 20%-mixed-hotspot workload.
''',encoding='utf-8')
print('PASS: 24 measured runs for the focused simulator-model comparison')
