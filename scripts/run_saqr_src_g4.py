"""SAQR-SC held-out evaluation (docs/SAQR_SPEC_V2.md §19).

Same held-out matrix as the G4 run (seeds 201-205, six traffic cases, frozen
load grids, both modes) and the same traces: only the frozen SAQR-SC candidate
is run here, on the SAQR-SC binary. Comparator receipts are copied from
results/saqr_study/g4 once that mesh is complete there, then scored with the
unchanged pre-registered evaluator (scripts/evaluate_saqr_g4.py).

The candidate is the one chosen by the tuning-pilot selection rule
(results/saqr_study/src/pilot/selection.json). The protocol is written before
the first held-out SAQR-SC run and must match on resume. Meshes run in tiers.
"""
import argparse
import concurrent.futures
import json
import shutil
from saqr_src_common import ROOT, SAQR_STUDY, SRC_BINARY, SRC_STUDY, sha, run
import run_saqr_g4 as g4
from run_saqr_src_pilot import SC

OUT=SRC_STUDY/'g4'
NAME='saqr_sc'

def protocol():
    sel=json.loads((SRC_STUDY/'pilot/selection.json').read_text())['selected']
    assert sel and sel!='sc_never','no SAQR-SC variant was selected on tuning data'
    env={'NOC_SAQR_O1TURN_MASK':3,**SC[sel]}   # adaptive packets use the soft-O1TURN set for both classes
    gp=json.loads((g4.OUT/'protocol.json').read_text())
    return dict(stage='saqr_src_heldout',candidate=NAME,selected_variant=sel,algorithm='saqr_nogate',env=env,
                cases=gp['cases'],seeds=gp['seeds'],meshes=gp['meshes'],modes=gp['modes'],
                comparators=[r for r in gp['variants'] if r not in gp['candidates']],
                g4_protocol_sha256=sha(g4.OUT/'protocol.json'),src_binary_sha256=sha(SRC_BINARY),
                source_sha256={s:sha(ROOT/s) for s in ['algorithms/saqr_src/routing.hpp','simulators/booksim_saqr_src/saqr_routes.cpp',
                               'scripts/setup_saqr_src.py','scripts/saqr_src_common.py','scripts/run_saqr_src_g4.py','scripts/evaluate_saqr_g4.py',
                               'scripts/run_saqr_src_pilot.py']},
                gate_receipt_sha256=sha(SRC_STUDY/'r0/r0_receipt.json'),
                pilot_selection_sha256=sha(SRC_STUDY/'pilot/selection.json'))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8)
    p.add_argument('--meshes',type=int,nargs='+',required=True)
    p.add_argument('--collect',action='store_true',help='copy comparator receipts from the G4 run and write the evaluator protocol')
    a=p.parse_args()
    gate=json.loads((SRC_STUDY/'r0/r0_receipt.json').read_text())
    assert gate['status']=='pass' and gate['binary_sha256']==sha(SRC_BINARY)
    OUT.mkdir(parents=True,exist_ok=True)
    proto=protocol(); pp=OUT/'protocol_src.json'
    if pp.exists(): assert json.loads(pp.read_text())==proto,'SAQR-SC held-out protocol mismatch'
    else: pp.write_text(json.dumps(proto,indent=2)+'\n')
    todo=sorted([c for c in proto['cases'] if c['k'] in a.meshes],key=lambda c:(c['k'],-c['index'],c['traffic'],c['seed']))
    if a.collect:
        # Comparator receipts: only from meshes complete in the G4 run.
        for c in todo:
            for mode in proto['modes']:
                for r in proto['comparators']:
                    src=g4.OUT/'cases'/c['name']/f'{mode}_{r}'/'result.json'; dst=OUT/'cases'/c['name']/f'{mode}_{r}'/'result.json'
                    assert src.exists(),f'G4 comparator receipt missing: {src} (wait for the G4 tier)'
                    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
        ev=dict(variants={**{r:list(g4.VARIANTS[r]) for r in proto['comparators']},NAME:[proto['algorithm'],proto['env']]},
                candidates=[NAME],seeds=proto['seeds'],modes=proto['modes'],meshes=sorted(a.meshes),
                cases=[c for c in proto['cases'] if c['k'] in a.meshes],saqr_binary_sha256=proto['src_binary_sha256'])
        (OUT/'protocol.json').write_text(json.dumps(ev,indent=2)+'\n')
        print('collected comparator receipts and wrote evaluator protocol for meshes',a.meshes); return
    jobs=[(c,mode) for c in todo for mode in proto['modes']]
    def work(job):
        c,mode=job
        demand=g4.OUT/'cases'/c['name']/'demand.txt'; assert demand.exists(),'G4 trace missing'
        d=OUT/'cases'/c['name']/f'{mode}_{NAME}'
        if (d/'result.json').exists():
            r=json.loads((d/'result.json').read_text()); assert r['binary_sha256']==proto['src_binary_sha256'] and r['trace_sha256']==sha(demand); return 1
        r=run(d,demand,c['k'],proto['algorithm'],c['seed'],mode,chr_env=proto['env'],binary=SRC_BINARY)
        if r['qos']['integrity_errors']: raise RuntimeError('integrity errors')
        return 1
    done=0; fails=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        fut={pool.submit(work,j):j for j in jobs}
        for f in concurrent.futures.as_completed(fut):
            try: done+=f.result()
            except Exception as exc: fails.append(dict(case=fut[f][0]['name'],mode=fut[f][1],error=repr(exc))); print('FAILED',fut[f][0]['name'],fut[f][1],repr(exc),flush=True)
    prog=json.loads((OUT/'progress.json').read_text()) if (OUT/'progress.json').exists() else {}
    prog[f'k{"_".join(map(str,a.meshes))}']=dict(expected=len(jobs),completed=done,failures=fails)
    (OUT/'progress.json').write_text(json.dumps(prog,indent=2)+'\n')
    print(f'SAQR-SC HELD-OUT {a.meshes}: {done}/{len(jobs)} runs, {len(fails)} failures',flush=True)

if __name__=='__main__': main()
