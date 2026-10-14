#pragma once
#include "config_utils.hpp"
#include "network.hpp"
void noc_register(const Configuration&);
bool noc_fixed();
int noc_warmup();
int noc_measure();
void noc_sample(const std::vector<Network*>&,int);
void noc_retire(int,int,int,int,int);
void noc_finish();
