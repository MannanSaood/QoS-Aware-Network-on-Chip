"""Fetch a pinned BookSim, apply checked instrumentation, build both adapters (Linux/WSL)."""
import argparse
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
REVISION = "28f43299f1706a3160ffac721ca461d74eb6e618"

def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)

def patch(path, old, new):
    data = path.read_text()
    if new in data:
        return
    if data.count(old) != 1:
        raise RuntimeError(f"Expected exactly one patch anchor in {path}: {old[:70]}")
    path.write_text(data.replace(old, new))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    repo = ROOT / ".deps/booksim2"
    if not repo.exists():
        run("git", "clone", "https://github.com/booksim/booksim2.git", str(repo))
        run("git", "-C", str(repo), "checkout", REVISION)
    rev = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if rev != REVISION:
        raise RuntimeError(f"Expected BookSim {REVISION}; found {rev}. Use a separate dependency checkout.")
    src = repo / "src"
    shutil.copytree(ROOT / "algorithms", src / "noc_algorithms", dirs_exist_ok=True)
    for file in (ROOT / "simulators/booksim").glob("noc_extension.*"):
        shutil.copyfile(file, src / file.name)
    patch(src / "routefunc.cpp", '#include "routefunc.hpp"', '#include "routefunc.hpp"\n#include "noc_extension.hpp"')
    patch(src / "routefunc.cpp", 'void InitializeRoutingMap( const Configuration & config )\n{',
          'void InitializeRoutingMap( const Configuration & config )\n{\n  noc_register(config);')
    tm = src / "trafficmanager.cpp"
    # Upstream returns -1 on SUCCESS; normalize for standard subprocess tooling.
    patch(src / "main.cpp", 'return result ? -1 : 0;', 'return result ? 0 : 1;')
    patch(tm, '#include "trafficmanager.hpp"', '#include "trafficmanager.hpp"\n#include "noc_extension.hpp"')
    patch(tm, 'void TrafficManager::_Step( )\n{', 'void TrafficManager::_Step( )\n{\n    noc_sample(_net,_time);')
    patch(tm, '        //code the source of request, look carefully, its tricky ;)',
          '        noc_retire(f->atime,head->ctime,f->hops,head->src,dest);\n        //code the source of request, look carefully, its tricky ;)')
    patch(tm, 'bool TrafficManager::_SingleSim( )\n{', '''bool TrafficManager::_SingleSim( )
{
    // Optional reproducible finite observation window; ordinary BookSim unchanged without env.
    if(noc_fixed()) {
        for(int i=0;i<noc_warmup();++i) _Step();
        _sim_state=running;
        _ClearStats();
        for(int i=0;i<noc_measure();++i) _Step();
        noc_sample(_net,_time);
        _sim_state=draining;
        _drain_time=_time;
        noc_finish();
        return true;
    }''')
    patch(tm, '        // Empty any remaining packets', '''        // Fixed-window metrics are already finalized; draining cannot change them.
        if(noc_fixed() && std::getenv("NOC_SKIP_DRAIN")) return true;
        // Empty any remaining packets''')
    run("make", f"-j{args.jobs}", cwd=src)
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    run("g++", "-std=c++17", "-O3", "-fPIC", "-shared", "-I/usr/include/tcl8.6",
        str(ROOT / "simulators/ns2/routing_tcl.cpp"), "-ltcl8.6", "-o", str(build / "nocroute.so"))
    run("g++", "-std=c++17", "-O2", str(ROOT / "tests/routing_test.cpp"), "-o", str(build / "routing_test"))
    run(str(build / "routing_test"))
    run("g++", "-std=c++17", "-O2", str(ROOT / "tests/selector_properties.cpp"), "-o", str(build / "selector_properties"))
    run(str(build / "selector_properties"))

if __name__ == "__main__":
    main()
