"""Additional original-depth/VC-count checks; leaves sweep provenance untouched."""
import json
from qos_common import ROOT, BINARY, run, sha

out=ROOT/'results/fr_coverage'; out.mkdir(parents=True,exist_ok=True)
demand=ROOT/'results/qos_validation/xy_all_pairs_10240/trace.txt'
r=run(out/'two_vc_depth4',demand,4,mode='weighted',warm=0,cycles=38900,vcs=2,depth=4)
assert r['qos']['trace_packets']==10240
assert sum(c['pending_end'] for c in r['qos']['classes'])==0
assert r['qos']['payload_checks']==51200
assert r['qos']['integrity_errors']==0
receipt=dict(binary_sha256=sha(BINARY),FR1=dict(packets=10240,delivered=10240,scope='4x4 all 256 source/destination pairs, 40 repetitions, both classes'),
             FR2=dict(vcs_per_input=2,depth_per_vc=4,payload_tags_checked=51200,integrity_errors=0),
             FR3=dict(status='Requirement revised to weighted service by user policy choice; not a strict-priority compliance claim',
                      evidence='../qos_validation/router_service_weighted/classes.json'),
             scope='BookSim behavioral model only, not RTL verification or synthesis')
(out/'coverage.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
