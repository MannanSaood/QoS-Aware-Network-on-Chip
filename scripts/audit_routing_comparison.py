"""Controlled diagnostics in a separate build; never overwrite the primary study."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile

from run_experiments import ROOT, invoke

OUT = ROOT / 'results/routing_comparison_audit'
VARIANTS = ['xy', 'oe_fixed', 'dyad_default', 'dyad_early',
            'dyad_peak_trigger', 'oe_adaptive', 'topsis']


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--high-load', action='store_true', help='Separate uniform 0.5-load diagnostic')
    args = parser.parse_args()
    load = .5 if args.high_load else .3
    traffic_cases = ['uniform'] if args.high_load else ['uniform', 'transpose']
    total_runs = len(traffic_cases) * 3 * len(VARIANTS)
    if args.high_load:
        OUT = ROOT / 'results/routing_high_load_audit'
    OUT.mkdir(parents=True, exist_ok=True)
    study = ROOT / 'results/primary_grid'
    primary_hash = hashlib.sha256((study / 'metrics.csv').read_bytes()).hexdigest()
    manifest = json.loads((study / 'manifest.json').read_text())
    assert manifest['actual_rows'] == 2160 and not manifest['failed_cases']
    source_hashes = {}
    for path in (ROOT / 'algorithms').rglob('*.hpp'):
        relative = str(path.relative_to(ROOT))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == manifest['sources_sha256'][relative], relative
        copied = ROOT / '.deps/booksim2/src/noc_algorithms' / path.relative_to(ROOT / 'algorithms')
        assert path.read_bytes() == copied.read_bytes(), copied
        source_hashes[relative] = digest
    matched = 0
    for case in sorted((study / 'cases').iterdir()):
        configs = list((case / 'raw').glob('*.cfg'))
        assert len(configs) == 3, case
        normalized = [re.sub(r'routing_function\s*=\s*noc_\w+;', 'routing_function = ROUTE;', p.read_text()) for p in configs]
        assert len(set(normalized)) == 1, ('unequal configuration', case)
        matched += 1
    assert matched == 720
    print('PASS: 720 cases have identical configs except routing; source hashes match study', flush=True)
    with tempfile.TemporaryDirectory(prefix='noc-routing-audit-') as scratch:
        scratch = Path(scratch)
        src = scratch / 'src'
        shutil.copytree(ROOT / '.deps/booksim2/src', src)
        subprocess.run(['g++', '-std=c++17', '-O2', str(ROOT / 'tests/routing_test.cpp'),
                        '-o', str(scratch / 'routing_test')], check=True)
        routing_test = subprocess.check_output([str(scratch / 'routing_test')], text=True)
        (OUT / 'routing_test.log').write_text(routing_test)
        print(routing_test.strip(), flush=True)
        # Independently specified mathematical properties, including a hand-computed
        # conflicting-criteria example: closeness scores are .3 and .7.
        test = scratch / 'selector_properties.cpp'
        test.write_text('''#include "noc_algorithms/common/select.hpp"
#include <cassert>
#include <iostream>
#include <random>
int main() {
  noc::Load q={{.5,0,.25,0}}, peak={{.5,0,1,0}};
  assert(noc::topsis(0,0,5,4,q,peak)==noc::S);
  assert(noc::topsis(0,0,5,4,q,peak,{{.3,.7}})==noc::E);
  std::mt19937 rng(913);
  for(int i=0;i<10000;++i) {
    for(int p=0;p<4;++p) {
      int sum=0,maximum=0;
      for(int v=0;v<4;++v) { int used=rng()%9; sum+=used; maximum=std::max(maximum,used); }
      q[p]=sum/32.0; peak[p]=maximum/8.0;
    }
    int actual=noc::topsis(0,0,5,4,q,peak);
    if(q[0]<=q[2] && peak[0]<=peak[2] && (q[0]<q[2] || peak[0]<peak[2])) assert(actual==noc::E);
    if(q[2]<=q[0] && peak[2]<=peak[0] && (q[2]<q[0] || peak[2]<peak[0])) assert(actual==noc::S);
    auto scaled=q; for(auto &value:scaled) value*=.25;
    assert(actual==noc::topsis(0,0,5,4,scaled,peak));
    assert(noc::topsis(0,0,5,4,q,peak,{{1,0}})==noc::dyad(0,0,5,4,q,0));
  }
  std::cout<<"PASS: hand-calculated TOPSIS tradeoff and 10000 feasible credit-state properties\\n";
}''')
        subprocess.run(['g++', '-std=c++17', '-O2', '-I', str(src), str(test),
                        '-o', str(scratch / 'selector_properties')], check=True)
        properties = subprocess.check_output([str(scratch / 'selector_properties')], text=True)
        (OUT / 'selector_properties.log').write_text(properties)
        print(properties.strip(), flush=True)
        extension = src / 'noc_extension.cpp'
        code = extension.read_text()
        anchor = 'int p=noc::select(name,f->src,r->GetID(),f->dest,side,q,peak);'
        assert code.count(anchor) == 1
        code = code.replace('int vcs=4, depth=8, side=4;', '''int vcs=4, depth=8, side=4;
std::string audit_variant;
bool audit_window=false;
long long audit_choices=0, audit_triggered=0, audit_changed=0, audit_peak_only=0;''')
        code = code.replace(anchor, anchor + '''
    for(int port=0;port<4;++port) {
        if(q[port]<0 || q[port]>1 || peak[port]<q[port] || peak[port]>1)
            throw std::logic_error("Invalid credit pressure signal");
    }
    auto candidates=noc::odd_even(f->src,r->GetID(),f->dest,side);
    double aggregate=*std::max_element(q.begin(),q.end());
    double vc_peak=*std::max_element(peak.begin(),peak.end());
    double threshold=.6;
    if(audit_variant=="oe_fixed") threshold=2;
    if(audit_variant=="dyad_early") threshold=.2;
    if(audit_variant=="oe_adaptive") threshold=0;
    if(audit_variant=="dyad_peak_trigger") threshold=vc_peak>=.6 ? 0 : 2;
    if(name=="dyad") p=noc::dyad(f->src,r->GetID(),f->dest,side,q,threshold);
    if(audit_window && name!="xy" && candidates.size()>1) {
        ++audit_choices;
        audit_triggered+=(aggregate>=threshold);
        audit_peak_only+=(aggregate<.6 && vc_peak>=.6);
        audit_changed+=(p!=candidates[0]);
    }''')
        code = code.replace('vcs=config.GetInt("num_vcs");', '''audit_variant=std::getenv("NOC_AUDIT_VARIANT");
    vcs=config.GetInt("num_vcs");''')
        code = code.replace('if(!noc_fixed()) return;', '''if(!noc_fixed()) return;
    audit_window=time>=noc_warmup() && time<noc_warmup()+noc_measure();''')
        code = code.replace('std::sort(latencies.begin(),latencies.end());', '''std::ofstream audit(std::string(path)+".audit.json");
    audit<<"{\\"choices\\":"<<audit_choices<<",\\"triggered\\":"<<audit_triggered
         <<",\\"changed\\":"<<audit_changed<<",\\"peak_only\\":"<<audit_peak_only<<"}";
    std::sort(latencies.begin(),latencies.end());''')
        extension.write_text(code)
        (OUT / 'instrumented_extension.cpp').write_text(code)
        with (OUT / 'build.log').open('w') as log:
            subprocess.run(['make', '-j2'], cwd=src, check=True, stdout=log, stderr=subprocess.STDOUT)
        binary_hash = hashlib.sha256((src / 'booksim').read_bytes()).hexdigest()

        def run(case):
            traffic, seed, variant = case
            algorithm = variant if variant in ['xy', 'topsis'] else 'dyad'
            original = study / f'cases/k8_{traffic}_l{load}_s{seed}/raw'
            stem = f'booksim_{algorithm}_k8_{traffic}_l{load}_s{seed}'
            name = f'k8_{traffic}_l{load}_s{seed}_{variant}'
            cfg = OUT / (name + '.cfg')
            cfg.write_text((original / (stem + '.cfg')).read_text())
            metrics = OUT / (name + '.json')
            env = dict(os.environ, NOC_WARMUP='1000', NOC_MEASURE='3000', NOC_SKIP_DRAIN='1',
                       NOC_METRICS=str(metrics), NOC_AUDIT_VARIANT=variant)
            wall, status = invoke([str(src / 'booksim'), str(cfg)], OUT / (name + '.log'), env)
            assert status == 'ok', (name, status)
            measured = json.loads(metrics.read_text())
            if variant in ['xy', 'dyad_default', 'topsis']:
                primary_metrics = json.loads((original / (stem + '.metrics.json')).read_text())
                assert measured == primary_metrics, ('baseline reproduction mismatch', name)
            row = dict(traffic=traffic, seed=seed, variant=variant, mesh_k=8, load=load,
                       warmup_cycles=1000, measurement_cycles=3000, status=status, wall_seconds=wall)
            row.update(measured)
            row.update(json.loads(Path(str(metrics) + '.audit.json').read_text()))
            row['throughput'] = row['delivered_packets'] * 5 / (64 * 3000)
            return row

        rows = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for future in as_completed([pool.submit(run, case) for case in itertools.product(
                    traffic_cases, [1, 2, 3], VARIANTS)]):
                rows.append(future.result())
                print(f'{len(rows)}/{total_runs} diagnostic runs complete', flush=True)
        rows.sort(key=lambda r: (r['traffic'], r['variant'], r['seed']))
        (OUT / 'runs.json').write_text(json.dumps(rows, indent=2) + '\n')
        summary = []
        for traffic, variant in itertools.product(traffic_cases, VARIANTS):
            group = [r for r in rows if r['traffic'] == traffic and r['variant'] == variant]
            record = dict(traffic=traffic, load=load, variant=variant, seeds=len(group))
            for metric in ['throughput', 'latency_p99_cycles', 'congested_port_time_pct',
                           'choices', 'triggered', 'changed', 'peak_only']:
                record[metric] = statistics.mean(r[metric] for r in group)
            summary.append(record)
        with (OUT / 'summary.csv').open('w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=summary[0]); writer.writeheader(); writer.writerows(summary)
    assert hashlib.sha256((study / 'metrics.csv').read_bytes()).hexdigest() == primary_hash
    receipt = dict(config_groups_checked=matched, controlled_runs=len(rows),
                   reproduced_primary_runs=len(traffic_cases)*9, primary_csv_unchanged=True,
                   primary_csv_sha256=primary_hash, diagnostic_binary_sha256=binary_hash,
                   source_hashes=source_hashes, checks_passed=True)
    (OUT / 'validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    main()
