"""Statistical sanity checks for spatial hotspot mixtures and on/off arrivals."""
import random
import sys
from pathlib import Path
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_experiments import destinations,hotspot_node,arrivals
for pattern,node in [('hotspot_corner',0),('hotspot_edge',4),('hotspot_center',36)]:
    assert hotspot_node(8,pattern)==node
    rng=random.Random(55)
    observed=sum(destinations(rng,3,8,pattern)==node for _ in range(100000))/100000
    assert abs(observed-(.2+.8/64))<.007, (pattern,observed)
with tempfile.TemporaryDirectory() as d:
    f=Path(d)/'arrivals.tcl'
    arrivals(f,4,.3,1,'bursty',0,20000,5)
    counts=[0]*20000
    for line in f.read_text().splitlines():
        cycle=int(float(line.split()[2])*1e6)
        counts[cycle]+=1
    rate=sum(counts)/(20000*16)
    assert abs(rate-.3/5)<.004,rate
print('PASS: three hotspot locations, destination probabilities and bursty mean injection.')
