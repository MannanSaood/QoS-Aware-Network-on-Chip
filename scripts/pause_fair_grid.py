"""Explicit user-requested pause: preserve completed evidence and in-flight files.

No simulator checkpoint is available. Incomplete attempts are archived, and the
unchanged grid runner can later resume from its existing successful receipts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import time
from change_qos_workers import process

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/fair_comparison'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def children(pid):
    return [r for p in Path('/proc').iterdir() if p.name.isdigit()
            if (r:=process(int(p.name))) and r['ppid']==pid and not r['state'].startswith('Z')]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--rebalance-pid',type=int,required=True)
    args=parser.parse_args()
    spec=json.loads((OUT/'protocol.json').read_text())
    assert sha(ROOT/'.deps/booksim2/src/booksim')==spec['binary_sha256']
    assert all(sha(ROOT/p)==h for p,h in spec['sources_sha256'].items())
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
    archive=OUT/'interrupted_attempts'/('pause_'+stamp)
    archive.mkdir(parents=True,exist_ok=False)
    audit=dict(reason='User requested pausing the old single-class sweep to prioritize QoS',
               started_utc=stamp,status='preparing',coordinator_pid=args.pid,
               rebalance_pid=args.rebalance_pid,processes=[],active_cases=[],complete=False)
    audit_path=archive/'administration.json'
    def save(): audit_path.write_text(json.dumps(audit,indent=2)+'\n')
    save()
    handles={}; stopped=[]; killed=set()
    def bind(pid,validator):
        handle=os.pidfd_open(pid)
        handles[pid]=handle
        record=process(pid)
        assert record and validator(record),record
        return record
    def freeze(pid):
        signal.pidfd_send_signal(handles[pid],signal.SIGSTOP)
        stopped.append(pid)
        for _ in range(200):
            ts=[process(int(p.name)) for p in (Path('/proc')/str(pid)/'task').iterdir()]
            if ts and all(t and t['state'].startswith('T') for t in ts): return
            time.sleep(.05)
        raise RuntimeError(f'Process {pid} did not stop')
    try:
        parent=bind(args.pid,lambda r:r['cwd']==ROOT and 'scripts/run_fair_grid.py' in r['args'])
        rebalance=bind(args.rebalance_pid,lambda r:r['cwd']==ROOT and 'build/rebalance_after_fair.py' in r['args'])
        assert not children(args.rebalance_pid),'Automatic rebalancer already started a handoff'
        # Disable the waiting handoff before changing the two sweep states.
        signal.pidfd_send_signal(handles[args.rebalance_pid],signal.SIGTERM)
        killed.add(args.rebalance_pid)
        (ROOT/'build/rebalance_after_fair.json').write_text(json.dumps(dict(
            status='cancelled_by_user_priority_change',reason=audit['reason'],audit=str(audit_path)),indent=2)+'\n')
        freeze(args.pid)
        runners=children(args.pid)
        for runner in runners:
            pid=runner['pid']
            def valid(r):
                return (str(ROOT/'scripts/run_experiments.py') in r['args'] and r['cwd']==ROOT
                    and '--output' in r['args'] and Path(r['args'][r['args'].index('--output')+1]).resolve().is_relative_to((OUT/'cases').resolve()))
            bind(pid,valid); freeze(pid)
        simulators=[]
        for runner in runners:
            for child in children(runner['pid']):
                bind(child['pid'],lambda r:Path(r['args'][0]).resolve()==(ROOT/'.deps/booksim2/src/booksim').resolve()
                     and Path(r['args'][1]).resolve().is_relative_to((OUT/'cases').resolve()))
                freeze(child['pid']); simulators.append(child)
        audit['status']='frozen_preserving'
        audit['processes']=[dict(pid=r['pid'],args=r['args']) for r in [parent,*runners,*simulators]]
        save()
        print(f'Old sweep frozen: {len(runners)} case runners and {len(simulators)} simulators; preserving evidence.',flush=True)
        hashes={}; receipt_count=0
        for path in (OUT/'cases').glob('*/raw/booksim_*.json'):
            if path.name.endswith('.metrics.json'): continue
            try: row=json.loads(path.read_text())
            except json.JSONDecodeError: continue
            if row.get('status')!='ok': continue
            assert row['binary_sha256']==spec['binary_sha256']
            assert row['warmup_cycles']==5000 and row['measurement_cycles']==20000
            receipt_count+=1
            for suffix in ['.json','.cfg','.log','.metrics.json']:
                evidence=path.with_suffix(suffix)
                assert evidence.is_file(),evidence
                hashes[str(evidence.relative_to(OUT))]=sha(evidence)
        (archive/'preserved_evidence_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
        for name in ['protocol.json','progress.json','metrics.json','metrics.csv']:
            source=OUT/name
            if source.exists(): shutil.copy2(source,archive/name)
        for runner in runners:
            source=Path(runner['args'][runner['args'].index('--output')+1]).resolve()
            target=(archive/'active_cases'/source.name).resolve()
            assert source.is_relative_to((OUT/'cases').resolve()) and target.is_relative_to(archive.resolve())
            shutil.copytree(source,target)
            audit['active_cases'].append(str(source.relative_to(OUT)))
        audit['archive_file_hashes']={str(p.relative_to(archive)):sha(p) for p in (archive/'active_cases').rglob('*') if p.is_file()}
        audit['preserved_successful_receipts']=receipt_count
        audit['status']='preserved_stopping'; save()
        # All writers are stopped. Ending children first cannot make their paused
        # parents record an administrative interruption as a simulation failure.
        for record in [*simulators,*runners,parent]:
            signal.pidfd_send_signal(handles[record['pid']],signal.SIGKILL)
            killed.add(record['pid'])
        assert all(sha(OUT/p)==h for p,h in hashes.items()),'Completed evidence changed during pause'
        audit.update(status='paused',complete=True,preservation_checks_passed=True,
                     resume_command='python3 scripts/resume_fair_grid.py --jobs 4',
                     unfinished_attempt_policy='Preserved separately; rerun from the start with unchanged configuration. No new seeds and no completed results discarded.')
        save()
        (OUT/'pause.json').write_text(json.dumps(dict(paused=True,audit=str(audit_path),
            preserved_successful_receipts=receipt_count,reason=audit['reason']),indent=2)+'\n')
        progress=json.loads((archive/'progress.json').read_text())
        progress.update(paused=True,state='paused_by_user')
        (OUT/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
        print(json.dumps(dict(status='paused',preserved_receipts=receipt_count,
            active_cases_archived=len(runners),audit=str(audit_path),checks_passed=True)),flush=True)
    finally:
        for pid in stopped:
            if pid not in killed:
                try: signal.pidfd_send_signal(handles[pid],signal.SIGCONT)
                except ProcessLookupError: pass
        for fd in handles.values(): os.close(fd)

if __name__=='__main__': main()
