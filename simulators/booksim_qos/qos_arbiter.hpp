#pragma once
#include "arbiter.hpp"
#include "qos_runtime.hpp"
// Class-weighted service, oldest first within class, rotating exact ties.
// State advances only after a grant is accepted by the allocator.
class QosWeightedArbiter : public Arbiter {
    int pointer=0;
public:
    QosWeightedArbiter(Module *p,const std::string& n,int s):Arbiter(p,n,s) {}
    void PrintState() const override {}
    int Arbitrate(int *id=nullptr,int *pri=nullptr) override {
        _selected=-1;
        for(int offset=0;offset<_size;++offset) {
            int i=(pointer+offset)%_size;
            if(!_request[i].valid) continue;
            if(_selected<0 || qos_prefers(FullName(),_request[i].pri,_request[_selected].pri)) _selected=i;
        }
        return Arbiter::Arbitrate(id,pri);
    }
    void UpdateState() override {
        if(_selected>=0) {
            qos_grant(FullName(),_request[_selected].pri);
            pointer=(_selected+1)%_size;
        }
    }
};
