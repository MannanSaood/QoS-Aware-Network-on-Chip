#pragma once
#include <string>
#include "config_utils.hpp"
#include "flit.hpp"
struct QosEvent { int time, source, dest, cl; };
void qos_initialize(const Configuration&);
bool qos_enabled();
int qos_classes();
bool qos_next_event(int, QosEvent&);
int qos_destination();
int qos_priority(int cl,int born);
bool qos_prefers(const std::string&,int incoming,int incumbent);
void qos_grant(const std::string&,int priority);
void qos_generated(int pid,int source,int dest,int cl,int born,int size);
void qos_flit_created(Flit*);
void qos_vc_check(const Flit*);
void qos_injected(const Flit*,int);
void qos_retired(Flit*,int);
void qos_finish();
std::string qos_source_key(int);
std::string qos_output_key(const std::string&,int);
