#pragma once
#include <vector>
#include "config_utils.hpp"
#include "network.hpp"
// CHR-OE study routes for the isolated CHR build (docs/CHR_OE_CANDIDATE_SPEC.md).
// Registers noc_oefixed, noc_chr, noc_chr_cls, noc_chr_hyst and noc_chr_nofv.
// It never changes the behaviour of noc_xy, noc_dyad or noc_topsis.
void chr_register(const Configuration&);
void chr_tick(const std::vector<Network*>&,int time);
void chr_finish();
