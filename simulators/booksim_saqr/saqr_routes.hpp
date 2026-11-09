#pragma once
#include <vector>
#include "config_utils.hpp"
#include "network.hpp"
// SAQR study routes for the isolated SAQR build (docs/SAQR_SPEC_V2.md).
// Registers noc_saqr, noc_saqr_local, noc_saqr_nogate, noc_duato,
// noc_westfirst and noc_ufa. Never changes noc_xy, noc_dyad or noc_topsis.
void saqr_register(const Configuration&);
void saqr_tick(const std::vector<Network*>&,int time);
void saqr_finish();
