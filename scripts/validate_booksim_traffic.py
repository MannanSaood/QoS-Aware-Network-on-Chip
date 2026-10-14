"""Validate intended distributions through the actual upstream BookSim parser."""
import json
import subprocess
from run_experiments import ROOT,booksim_traffic_config,hotspot_node

src=ROOT/'.deps/booksim2/src'
exe=ROOT/'build/booksim_traffic_test'
objects=['traffic','injection','config_utils','booksim_config','lex.yy','y.tab','random_utils','rng_wrapper','rng_double_wrapper']
subprocess.run(['g++','-std=c++17','-O2','-I'+str(src),str(ROOT/'tests/booksim_traffic_test.cpp'),
                *[str(src/(x+'.o')) for x in objects],'-o',str(exe)],check=True)
out=ROOT/'results/validation/booksim_traffic'; out.mkdir(parents=True,exist_ok=True)
checks=[]
for k in [4,8,16,32]:
    for traffic in ['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']:
        for load in ([.1,1.] if traffic=='bursty' else [.3]):
            pattern,injection=booksim_traffic_config(k,traffic)
            cfg=out/f'k{k}_{traffic}_{load}.cfg'
            cfg.write_text(f'k={k}; traffic={pattern}; injection_process={injection}; injection_rate={load/5};\n')
            result=subprocess.check_output([str(exe),str(cfg)],text=True)
            data=json.loads(result[result.index('{"destinations"'):])
            observed=data['injection_rate']; expected=load/5
            assert abs(observed-expected)<.006,(k,traffic,observed,expected)
            if traffic=='bursty':
                # 50% ON, P(stay ON)=.98, ON injection=2*mean rate.
                expected_joint=.5*.98*(2*expected)**2
                assert abs(data['consecutive_probability']-expected_joint)<.004,(k,load,data)
            counts=data['destinations']; total=data['samples']
            if traffic.startswith('hotspot_'):
                hot=hotspot_node(k,traffic); probability=.2+.8/(k*k)
                assert abs(counts[hot]/total-probability)<.007,(k,traffic,counts[hot]/total)
                assert counts.index(max(counts))==hot
            elif traffic=='transpose':
                # Cycling every source should yield the permutation's balanced marginal.
                assert max(counts)-min(counts)<=1
            else:
                assert max(abs(c/total-1/(k*k)) for c in counts)<.004
            checks.append(dict(mesh_k=k,traffic=traffic,load=load,observed_packet_injection=observed,
                               expected_packet_injection=expected,status='passed'))
(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(f'PASS: {len(checks)} upstream BookSim parser/generator distribution checks')
