"""Administrative drain/resume; preserve receipts and archive unfinished attempts.

Linux/WSL only. This changes host concurrency, never simulated configuration.
Do not use for a failed experiment or to replace a completed measurement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/qos_comparison'

def process(pid):
    p=Path('/proc')/str(pid)
    try:
        status=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
        return dict(pid=int(pid),ppid=int(status['PPid']),state=status['State'].strip(),
                    args=(p/'cmdline').read_bytes().decode().strip('\0').split('\0'),cwd=(p/'cwd').resolve())
    except (FileNotFoundError,ProcessLookupError,PermissionError): return None

def valid_receipt(path):
    try:
        row=json.loads(path.read_text())
        return all(key in row for key in ['aggregate','qos','binary_sha256','trace_sha256','config_sha256'])
    except (FileNotFoundError,json.JSONDecodeError): return False

def receipts():
    return {str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (OUT/'cases').glob('*/*/result.json') if valid_receipt(p)}

def main():
    a=argparse.ArgumentParser(); a.add_argument('--pid',type=int,required=True); a.add_argument('--jobs',type=int,required=True)
    args=a.parse_args(); assert 1<=args.jobs<=8
    assert not json.loads((OUT/'progress.json').read_text())['failed_cases'],'Handle failures explicitly first'
    parent_handle=os.pidfd_open(args.pid) # Never signal a different process after PID reuse.
    def send(sig): signal.pidfd_send_signal(parent_handle,sig)
    parent=process(args.pid)
    assert parent and parent['cwd']==ROOT and 'scripts/run_qos_grid.py' in parent['args'],parent
    assert parent['args'][0].endswith('python3'),parent
    previous=int(parent['args'][parent['args'].index('--jobs')+1])
    assert previous!=args.jobs
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
    archive=OUT/'interrupted_attempts'/stamp; archive.mkdir(parents=True,exist_ok=False)
    audit=dict(reason='Host worker-count change; simulated protocol unchanged',old_pid=args.pid,
               old_jobs=previous,new_jobs=args.jobs,started_utc=stamp,archived=[],locations=[],complete=False,phase='draining')
    audit_path=archive/'administration.json'
    def save(): audit_path.write_text(json.dumps(audit,indent=2)+'\n')
    save()
    stopped=False
    try:
        send(signal.SIGSTOP); stopped=True
        for _ in range(100):
            threads=[process(int(p.name)) for p in (Path('/proc')/str(args.pid)/'task').iterdir()]
            if threads and all(t and t['state'].startswith('T') for t in threads): break
            time.sleep(.05)
        else: raise RuntimeError('Runner did not stop; no worker change made')
        children=[r for p in Path('/proc').iterdir() if p.name.isdigit()
                  if (r:=process(int(p.name))) and r['ppid']==args.pid]
        binary=(ROOT/'.deps/booksim2_qos/src/booksim').resolve()
        for child in children:
            assert Path(child['args'][0]).resolve()==binary,child
            assert Path(child['args'][1]).resolve().is_relative_to((OUT/'cases').resolve()),child
        audit['drained_children']=[dict(pid=c['pid'],config=c['args'][1]) for c in children]; save()
        print(f'Draining {len(children)} existing simulator processes before worker change.',flush=True)
        deadline=time.monotonic()+3700
        while any((p:=process(c['pid'])) and not p['state'].startswith('Z') for c in children):
            assert time.monotonic()<deadline,'Drain timeout: resume original runner without changing workers'
            time.sleep(5)
        audit['drained_exit_status']={}
        for c in children:
            stat=(Path('/proc')/str(c['pid'])/'stat').read_text()
            status=int(stat.rsplit(')',1)[1].split()[49]) # Linux /proc stat field 52.
            audit['drained_exit_status'][str(c['pid'])]=status
            save()
            assert status==0,'Simulator failed during drain; resume original runner to record the failure'
        # The paused runner cannot commit a new receipt or start another process.
        before=receipts()
        audit['phase']='resuming'; save()
        send(signal.SIGKILL); stopped=False
        def preserve_unfinished(directory):
            source=directory.resolve(); target=(archive/directory.relative_to(OUT/'cases')).resolve()
            assert source.is_relative_to((OUT/'cases').resolve()) and target.is_relative_to(archive.resolve())
            target.parent.mkdir(parents=True,exist_ok=True); source.rename(target)
            audit['archived'].append(str(target.relative_to(OUT)))
            audit['locations'].append(dict(source=str(source.relative_to(OUT)),archive=str(target.relative_to(OUT))))
        for case_directory in sorted((OUT/'cases').iterdir()):
            if not case_directory.is_dir(): continue
            if not any(valid_receipt(p) for p in case_directory.glob('*/result.json')):
                # Trace creation may itself have been paused halfway through.
                # With no completed receipt, preserve the whole case and regenerate
                # its deterministic demand rather than trusting an unfinished file.
                preserve_unfinished(case_directory)
                continue
            for directory in sorted(case_directory.iterdir()):
                if directory.is_dir() and (directory/'config.cfg').exists() and not valid_receipt(directory/'result.json'):
                    preserve_unfinished(directory)
        assert receipts()==before,'Completed receipts changed during administration'
        audit['preserved_receipt_count']=len(before)
        (archive/'preserved_receipt_hashes.json').write_text(json.dumps(before,indent=2)+'\n')
        audit['resume_log']=str(ROOT/'build'/f'qos_grid_resume_{stamp}.log'); save()
        print(f'Preserved {len(before)} completed receipts; archived {len(audit["archived"])} unfinished folders. Resuming with {args.jobs} workers.',flush=True)
        with Path(audit['resume_log']).open('w') as log:
            child=subprocess.Popen([sys.executable,'scripts/run_qos_grid.py','--jobs',str(args.jobs)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            audit['new_pid']=child.pid; audit['complete']=True; audit['phase']='running'; save()
            returncode=child.wait()
        audit['runner_exit_code']=returncode; save()
        if returncode==-signal.SIGKILL:
            # A later worker adjustment can supersede this supervisor. The last
            # supervisor checks preservation and repeats for the entire history.
            for _ in range(30):
                successors=[]
                for path in (OUT/'interrupted_attempts').glob('*/administration.json'):
                    if path.parent.name<=stamp: continue
                    try: other=json.loads(path.read_text())
                    except json.JSONDecodeError: continue
                    if other['old_pid']==child.pid and other.get('phase') in ['resuming','running','finished']:
                        successors.append(path)
                if successors:
                    assert len(successors)==1
                    audit['superseded_by']=str(successors[0].relative_to(OUT)); audit['phase']='superseded'; save()
                    print('Worker supervision handed to the next recorded adjustment.',flush=True)
                    return
                time.sleep(.1)
        assert returncode==0,f'Resumed sweep failed: see {audit["resume_log"]}'
        after=receipts()
        for path in (OUT/'interrupted_attempts').glob('*/administration.json'):
            saved=path.parent/'preserved_receipt_hashes.json'
            if not saved.exists(): continue
            history=json.loads(path.read_text()); hashes=json.loads(saved.read_text())
            assert all(after.get(k)==v for k,v in hashes.items()),'A preserved result changed after resume'
            repeated=[]
            for location in history['locations']:
                old=OUT/location['archive']; new=OUT/location['source']
                for name in ['classes.json','aggregate.json']:
                    for metric in old.rglob(name):
                        target=new/metric.relative_to(old)
                        assert json.loads(metric.read_text())==json.loads(target.read_text()),f'Repeat mismatch: {target}'
                        repeated.append(str(target.relative_to(OUT)))
            history['repeated_metric_files_equal']=repeated; history['final_preservation_check_passed']=True
            if path==audit_path: history['phase']='finished'
            path.write_text(json.dumps(history,indent=2)+'\n')
    finally:
        if stopped:
            try: send(signal.SIGCONT)
            except ProcessLookupError: pass
        os.close(parent_handle)

if __name__=='__main__': main()
