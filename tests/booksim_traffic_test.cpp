// Exercise upstream parsing and generators, not a Python reimplementation.
#include "booksim_config.hpp"
#include "traffic.hpp"
#include "injection.hpp"
#include "random_utils.hpp"
#include <iostream>
#include <memory>
#include <vector>

int main(int argc,char **argv) {
  if(argc!=2) return 2;
  BookSimConfig config;
  config.ParseFile(argv[1]);
  int k=config.GetInt("k"), nodes=k*k;
  auto patterns=config.GetStrArray("traffic");
  auto processes=config.GetStrArray("injection_process");
  if(patterns.size()!=1 || processes.size()!=1) return 3;
  RandomSeed(123);
  std::unique_ptr<TrafficPattern> traffic(TrafficPattern::New(patterns[0],nodes,&config));
  const int samples=200000;
  std::vector<int> histogram(nodes,0);
  for(int i=0;i<samples;++i) ++histogram[traffic->dest(i%nodes)];
  RandomSeed(456);
  std::unique_ptr<InjectionProcess> injection(InjectionProcess::New(processes[0],nodes,config.GetFloat("injection_rate"),&config));
  long accepted=0, consecutive=0;
  std::vector<int> previous(nodes,0);
  for(int cycle=0;cycle<10000;++cycle)
    for(int node=0;node<nodes;++node) {
      bool event=injection->test(node);
      accepted+=event; consecutive+=event && previous[node]; previous[node]=event;
    }
  std::cout << "{\"destinations\":[";
  for(int i=0;i<nodes;++i) std::cout << (i?",":"") << histogram[i];
  std::cout << "],\"samples\":" << samples << ",\"injection_rate\":"
            << double(accepted)/(10000*nodes) << ",\"consecutive_probability\":"
            << double(consecutive)/(9999*nodes) << "}" << std::endl;
}
