#pragma once
// CHR-OE: class-aware hysteretic routing on the odd-even legal set.
// Specification: docs/CHR_OE_CANDIDATE_SPEC.md (sections 3 and 6).
// Research candidate, not a validated or benchmarked algorithm.
//
// Safety invariant: every variant returns a member of noc::odd_even(), so
// legality and deadlock reasoning are inherited from the OE candidate set.
// Pure integer logic with fixed-size state and no BookSim types.
#include "../common/mesh.hpp"
#include <array>
#include <cstdint>
#include <stdexcept>

namespace noc {

enum class ChrVariant { Cls, Hyst, Full };

struct ChrParams {
    ChrVariant variant = ChrVariant::Full;
    int alpha_shift = 2;    // EWMA weight 2^-alpha_shift
    int t_on = 38;          // enter pressured state (e scale 0..60)
    int t_off = 23;         // leave pressured state
    int margin = 2;         // switching margin M (cost units 0..15)
    int free_penalty = 4;   // F_PEN, cost when no class VC is free downstream
    void validate() const {
        if(alpha_shift<1 || alpha_shift>3) throw std::invalid_argument("CHR alpha_shift must be 1..3");
        if(t_off<0 || t_on>60 || t_off>=t_on) throw std::invalid_argument("CHR requires 0<=t_off<t_on<=60");
        if(margin<0 || margin>15) throw std::invalid_argument("CHR margin must be 0..15");
        if(free_penalty<0 || free_penalty>15) throw std::invalid_argument("CHR free_penalty must be 0..15");
    }
};

constexpr int CHR_CLASSES = 2;
constexpr int CHR_DIRS = 4;   // E, W, S, N; the local port is never ranked

// Per-router state: 2 classes x 4 outputs x (6-bit e + 1-bit h) = 56 bits.
struct ChrState {
    std::array<std::array<uint8_t,CHR_DIRS>,CHR_CLASSES> e{};
    std::array<std::array<uint8_t,CHR_DIRS>,CHR_CLASSES> h{};
};

// Class-local downstream view of one output port, as a router reads it from
// its own credit and VC-allocation state.
struct ChrPort {
    int used = 0;       // used credits summed over the class's VCs
    int peak = 0;       // largest single class-VC occupancy (flits)
    int free_vcs = 0;   // unallocated class VCs downstream
};
using ChrView = std::array<ChrPort,CHR_DIRS>;

// 4-bit quantization of class-local occupancy: floor(used*15/capacity).
inline int chr_quantize(int used,int capacity) {
    if(capacity<=0 || used<0 || used>capacity) throw std::invalid_argument("CHR occupancy out of range");
    return used*15/capacity;
}

// Floor division by 2^s for signed steps (portable, unlike >> on negatives).
inline int chr_floor_shift(int d,int s) {
    return d>=0 ? (d>>s) : -((-d+(1<<s)-1)>>s);
}

// One cycle of the filter and hysteresis for one (class, output).
// The new value is used by route decisions in the next cycle.
inline void chr_update(ChrState& st,const ChrParams& prm,int cl,int port,int u) {
    if(cl<0 || cl>=CHR_CLASSES || port<0 || port>=CHR_DIRS || u<0 || u>15)
        throw std::invalid_argument("CHR update out of range");
    int e=st.e[cl][port];
    e+=chr_floor_shift((u<<2)-e,prm.alpha_shift);
    st.e[cl][port]=uint8_t(e);
    if(e>=prm.t_on) st.h[cl][port]=1;
    else if(e<=prm.t_off) st.h[cl][port]=0;
}

struct ChrDecision {
    int port = -1;
    int candidates = 0;
    bool pressured = false;   // default port's trigger was on
    bool switched = false;    // chose the non-default candidate
};

inline ChrDecision chr_decide(int src,int cur,int dst,int k,int cl,const ChrState& st,
                              const ChrParams& prm,const ChrView& view,int class_capacity,int depth) {
    if(cl<0 || cl>=CHR_CLASSES) throw std::invalid_argument("CHR class out of range");
    ChrDecision d;
    auto ports=odd_even(src,cur,dst,k);
    d.candidates=int(ports.size());
    if(ports.size()==1) { d.port=ports[0]; return d; }
    if(ports.size()!=2) throw std::logic_error("minimal OE produced more than two candidates");
    const int p0=ports[0], p1=ports[1];
    switch(prm.variant) {
    case ChrVariant::Cls:
        // DyAD's 0.6 peak trigger, restricted to the default port and own class.
        d.pressured = 10*view[p0].peak >= 6*depth;
        if(d.pressured)
            d.switched = chr_quantize(view[p1].used,class_capacity) < chr_quantize(view[p0].used,class_capacity);
        break;
    case ChrVariant::Hyst:
        d.pressured = st.h[cl][p0]!=0;
        if(d.pressured) d.switched = st.e[cl][p1] < st.e[cl][p0];
        break;
    case ChrVariant::Full: {
        d.pressured = st.h[cl][p0]!=0;
        if(d.pressured) {
            auto cost=[&](int p){ return (view[p].free_vcs==0 ? prm.free_penalty : 0) + (st.e[cl][p]>>2); };
            d.switched = cost(p1)+prm.margin <= cost(p0);
        }
        break;
    }
    }
    d.port = d.switched ? p1 : p0;
    return d;
}

}
