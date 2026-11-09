"""Smoke test for the stall rule (§15): one 8x8 uniform overload case, W=32. Writes under results/saqr_study/smoke_stall."""
import json
from chr_common import STUDY, SAQR_STUDY, SAQR_BINARY, run
c='k8_uniform_l7_s101'; demand=STUDY/'pilot_k8'/'cases'/c/'demand.txt'
for name,env in [('stall_w32',{'NOC_SAQR_BE_STALL':32}),('xyref',{'NOC_SAQR_CLASS_MASK':0})]:
    r=run(SAQR_STUDY/'smoke_stall'/name,demand,8,'saqr_nogate',101,'weighted',chr_env=env,binary=SAQR_BINARY)
    s=r['saqr']['classes']; q=r['qos']['classes']
    thr=sum(x['ejected_flits'] for x in q)/(r['cycles']*64)
    print(name,'thr %.4f'%thr,'integrity',r['qos']['integrity_errors'],'reroutes',[x['stall_reroutes'] for x in s],
          'hops(n,mean) BE:',[(h['kind'],h['detoured'],h['n'],round(h['sum']/h['n'],1) if h['n'] else None) for h in s[1]['hops']])
