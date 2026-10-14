"""Directed simulator checks and independent event-log accounting."""
import csv
import json
import subprocess
from qos_common import ROOT, BINARY, sha, run, trace

OUT=ROOT/'results/qos_validation'
OUT.mkdir(parents=True,exist_ok=True)
subprocess.run(['g++','-std=c++11','-O2',str(ROOT/'tests/qos_policy_test.cpp'),'-o',str(ROOT/'build/qos_policy_test')],check=True)
subprocess.run([str(ROOT/'build/qos_policy_test')],check=True)
receipts=[]

def checked(name,lines,k=4,**kwargs):
    folder=OUT/name; folder.mkdir(exist_ok=True)
    demand=folder/'trace.txt'; demand.write_text(lines)
    result=run(folder,demand,k,events=True,**kwargs)
    events=list(csv.reader((folder/'events.csv').open()))
    g={int(pid):(int(t),int(cl)) for kind,pid,t,cl in events if kind=='G'}
    d={int(pid):int(t) for kind,pid,t,cl in events if kind=='D'}
    assert len(g)==len(lines.splitlines())==result['qos']['trace_packets']
    start=result['warm']; end=start+result['cycles']; deadline=16*k
    for cl,row in enumerate(result['qos']['classes']):
        measured=sorted(t-g[pid][0] for pid,t in d.items() if start<=t<end and g[pid][1]==cl)
        assert len(measured)==row['delivered_packets']
        if measured:
            import math
            assert measured[math.ceil(.99*len(measured))-1]==row['latency_p99_cycles']
        eligible=[pid for pid,(t,c) in g.items() if c==cl and start<=t<end and t+deadline<end]
        assert len(eligible)==row['target_eligible_packets']
        assert sum(pid in d and d[pid]<=g[pid][0]+deadline for pid in eligible)==row['target_on_time_packets']
        assert sum(pid not in d for pid,(_,c) in g.items() if c==cl)==row['pending_end']
    receipts.append(dict(name=name,packets=len(g),binary_sha256=result['binary_sha256'],event_checks='pass'))
    print(name,'PASS',flush=True)
    return result

for algorithm in ['xy','dyad','topsis']:
    result=checked('single_'+algorithm,'0 0 15 0\n0 15 0 1\n',algorithm=algorithm,warm=0,cycles=100)
    assert all(c['delivered_packets']==1 and c['pending_end']==0 for c in result['qos']['classes'])
    assert result['qos']['payload_checks']==10
checked('single_class','0 0 15 0\n',classes=1,mode='age',warm=0,cycles=100)
# Exact deadline boundary and overload: maturity uses strict t+deadline<end.
lines=''.join(f'{t} {s} 15 {s%2}\n' for t in range(100) for s in range(15))
for mode in ['age','weighted','aged','strict']:
    checked('contention_'+mode,lines,mode=mode,warm=10,cycles=90)
checked('depth4',lines,depth=4,mode='weighted',warm=10,cycles=90)
# Two equally distant, independently saturated inputs compete at one ejection
# port. The ratio must emerge at the router, not just in the policy unit test.
service=''.join(f'{t} {s} 1 {cl}\n' for t in range(6000) for s,cl in [(0,0),(2,1)])
weighted=checked('router_service_weighted',service,mode='weighted',warm=1000,cycles=5000)
control=checked('router_service_age',service,mode='age',warm=1000,cycles=5000)
def share(result):
    cs=result['qos']['classes']; return cs[0]['ejected_flits']/sum(c['ejected_flits'] for c in cs)
assert .70<share(weighted)<.80,share(weighted)
assert .45<share(control)<.55,share(control)
# 10,240 XY packets, all source/destination pairs repeated, both classes.
vectors=''.join(f'{(r*16+s)*60} {s} {d} {(r+s+d)%2}\n' for r in range(40) for s in range(16) for d in range(16))
r=checked('xy_all_pairs_10240',vectors,warm=0,cycles=40*16*60+500)
assert sum(c['pending_end'] for c in r['qos']['classes'])==0
# Replay determinism includes both classes and both non-XY algorithms.
path=OUT/'random_trace.txt'; trace(path,4,.3,73,'bursty',100,1500)
for algorithm in ['xy','dyad','topsis']:
    a=checked('replay_'+algorithm,path.read_text(),algorithm=algorithm,warm=100,cycles=1500)
    b=checked('repeat_'+algorithm,path.read_text(),algorithm=algorithm,warm=100,cycles=1500)
    assert a['qos']==b['qos'] and a['aggregate']==b['aggregate']
(OUT/'validation.json').write_text(json.dumps(dict(status='pass',binary_sha256=sha(BINARY),checks=receipts),indent=2)+'\n')
print('All QoS validation checks passed',flush=True)
