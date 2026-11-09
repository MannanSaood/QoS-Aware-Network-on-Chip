"""Hop-delay diagnostic summary for SAQR round 5 (§15). Mean cycles per hop by
class, hop kind and whether the packet had already detoured, pooled over
seeds (sum of delays / number of hops). Kinds: 0 X, 1 X after a Y->X turn,
2 compliant Y, 3 non-compliant (detour) Y on VC offset 1.
In stall_w* runs, hops taken after a stall re-route include the >= W cycles
waited before the re-route, so their kind-0/3 means are not comparable with
the other variants."""
import json
from collections import defaultdict
from chr_common import SAQR_STUDY
OUT=SAQR_STUDY/'pilot_k8_r5'
KIND=['X','X-after-turn','Y','Y-detour']
def main():
    proto=json.loads((OUT/'protocol.json').read_text())
    acc=defaultdict(lambda:[0,0])
    for c in proto['cases']:
        for v in proto['variants']:
            r=json.loads((OUT/'cases'/c['name']/f'weighted_{v}'/'result.json').read_text())
            for cl,x in enumerate(r['saqr']['classes']):
                for h in x['hops']:
                    a=acc[(c['traffic'],c['index'],v,cl,h['kind'],h['detoured'])]; a[0]+=h['n']; a[1]+=h['sum']
                if cl==1: acc[(c['traffic'],c['index'],v,cl,'reroutes',0)][0]+=x['stall_reroutes']
    lines=['# Round 5 hop-delay diagnostic (8x8, weighted, seeds 101-103 pooled)','',__doc__.split('\n',1)[1],'']
    for t in ('uniform','transpose'):
        for idx in (6,7,8):
            lines+=[f'## {t}, load index {idx}','','| variant | class | '+' | '.join(f'{k} (clean)' for k in KIND)+' | '+' | '.join(f'{k} (after detour)' for k in KIND)+' | detour hop share |','|---|---|'+'---:|'*9]
            for v in proto['variants']:
                for cl in (0,1):
                    cells=[]; tot=det=0
                    for d in (0,1):
                        for k in range(4):
                            n,s=acc[(t,idx,v,cl,k,d)]; tot+=n; det+= n if k==3 else 0
                            cells.append(f'{s/n:.1f}' if n else '—')
                    lines.append(f"| {v} | {'crit' if cl==0 else 'BE'} | "+' | '.join(cells)+f" | {100*det/tot:.1f}% |" if tot else '')
            lines.append('')
    (OUT/'HOPS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines))
if __name__=='__main__': main()
