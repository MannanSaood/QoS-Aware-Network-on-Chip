// Mechanical deadlock search for SAQR's CTY rule (docs/SAQR_SPEC_V2.md §2, §6.2).
//
// Model: one traffic class, 2 VCs per directed mesh channel, VCT (a VC holds
// at most one whole packet, head at the front), ejection always drains.
// A deadlock is a non-empty set S of occupied VC slots such that every packet
// in S is blocked: for some route set the policy may produce at its router,
// every VC it may use lies in S. Blocking is monotone in S, so the greatest
// fixed point of "remove slots whose every possible occupant could move"
// is non-empty iff some deadlock configuration exists. This over-approximates
// reachable states (it ignores how a state was reached), which is the safe
// direction for a freedom check.
// Build: g++ -std=c++17 -O2 tests/saqr_deadlock_check.cpp -o saqr_deadlock_check
#include <cstdio>
#include <cstdlib>
#include <vector>

enum Dir { E=0, W=1, S=2, N=3 };
struct Mesh { int kx, ky; };

static int nb(const Mesh& m,int id,int d){ int x=id%m.kx,y=id/m.kx;
    if(d==E) return x+1<m.kx?id+1:-1; if(d==W) return x>0?id-1:-1;
    if(d==S) return y+1<m.ky?id+m.kx:-1; return y>0?id-m.kx:-1; }
static bool productive(const Mesh& m,int at,int dst,int d){ int dx=dst%m.kx-at%m.kx, dy=dst/m.kx-at/m.kx;
    return (d==E&&dx>0)||(d==W&&dx<0)||(d==S&&dy>0)||(d==N&&dy<0); }
static int xy(const Mesh& m,int at,int dst){ int dx=dst%m.kx-at%m.kx, dy=dst/m.kx-at/m.kx;
    if(dx>0) return E; if(dx<0) return W; if(dy>0) return S; if(dy<0) return N; return -1; }

enum class Policy { XY, SAQR, UFA, CTY_NO_ESCAPE, DUATO_DEDICATED, O1TURN, O1TURN_SHARED };
static int yx(const Mesh& m,int at,int dst){ int dx=dst%m.kx-at%m.kx, dy=dst/m.kx-at/m.kx;
    if(dy>0) return S; if(dy<0) return N; if(dx>0) return E; if(dx<0) return W; return -1; }
static const char* name(Policy p){ switch(p){case Policy::XY:return "XY";case Policy::SAQR:return "SAQR (CTY + XY escape offer)";
    case Policy::UFA:return "UFA (unrestricted fully adaptive)";case Policy::CTY_NO_ESCAPE:return "CTY without escape offer";
    case Policy::O1TURN:return "O1TURN (VC0=XY, VC1=YX subnets)";case Policy::O1TURN_SHARED:return "O1TURN with shared VCs";
    default:return "Duato dedicated escape VC";} }

// Slot index: (router*4 + incoming-direction-of-travel)*2 + vc. A slot is the
// input VC at router `v` for packets that arrived travelling in direction d.
struct Checker {
    Mesh m; Policy pol; std::vector<char> in;
    int slot(int v,int d,int vc) const { return (v*4+d)*2+vc; }
    bool exists(int v,int d) const { int opp[4]={W,E,N,S}; return nb(m,v,opp[d])>=0; }
    bool compliant(int v,int d,int dst) const { return d==E||d==W||dst%m.kx==v%m.kx; }
    // May packet with destination dst legally sit in slot (v,d,vc)?
    bool placeable(int v,int d,int vc,int dst) const {
        int opp[4]={W,E,N,S}; int u=nb(m,v,opp[d]);
        if(u<0 || dst==v || !productive(m,u,dst,d)) return false;   // at dst it would eject
        switch(pol) {
        case Policy::XY: return xy(m,u,dst)==d;                      // only XY hops exist
        case Policy::SAQR: case Policy::CTY_NO_ESCAPE: return vc==1 || compliant(v,d,dst);
        case Policy::DUATO_DEDICATED: return vc==1 || xy(m,u,dst)==d; // VC0 = escape, entered by XY hops only
        case Policy::O1TURN: return vc==0 ? xy(m,u,dst)==d : yx(m,u,dst)==d;
        case Policy::O1TURN_SHARED: return xy(m,u,dst)==d || yx(m,u,dst)==d;
        default: return true;
        }
    }
    // All VCs of channel (v -> dir) in S?  'vcs' bitmask selects which VCs count.
    bool full(int v,int dir,int vcs) const { int w=nb(m,v,dir); if(w<0) return false;
        for(int vc=0;vc<2;++vc) if((vcs>>vc)&1 && !in[slot(w,dir,vc)]) return false; return true; }
    // Can the adversary pick a route set at v for dst under which every usable VC is in S?
    bool blocked(int v,int dst,int vc) const {
        int x=xy(m,v,dst);
        switch(pol) {
        case Policy::O1TURN: return vc==0 ? full(v,x,1) : full(v,yx(m,v,dst),2);   // each subnet stays on its VC
        case Policy::O1TURN_SHARED: return full(v,x,3) || full(v,yx(m,v,dst),3);   // adversary picks either plan
        case Policy::XY: return full(v,x,3);
        case Policy::SAQR: return full(v,x,3);             // the XY entry (all VCs) is always offered
        case Policy::DUATO_DEDICATED: return full(v,x,3);  // escape VC0 on XY port + adaptive VC1: same XY port has both
        case Policy::UFA: for(int d=0;d<4;++d) if(productive(m,v,dst,d) && full(v,d,3)) return true; return false;
        case Policy::CTY_NO_ESCAPE:
            for(int d=0;d<4;++d) if(productive(m,v,dst,d)) {
                bool nc=(d==S||d==N) && dst%m.kx!=v%m.kx;      // next hop non-compliant -> designated VC1 only
                if(full(v,d,nc?2:3)) return true;
            }
            return false;
        }
        return false;
    }
    // Greatest fixed point; returns size of the maximal deadlock set.
    int run() {
        int R=m.kx*m.ky; in.assign(R*8,0);
        for(int v=0;v<R;++v) for(int d=0;d<4;++d) if(exists(v,d)) for(int vc=0;vc<2;++vc) in[slot(v,d,vc)]=1;
        for(bool changed=true;changed;) {
            changed=false;
            for(int v=0;v<R;++v) for(int d=0;d<4;++d) for(int vc=0;vc<2;++vc) {
                int s=slot(v,d,vc); if(!in[s]) continue;
                bool some_blocked_occupant=false;
                for(int dst=0;dst<R && !some_blocked_occupant;++dst)
                    if(placeable(v,d,vc,dst) && blocked(v,dst,vc)) some_blocked_occupant=true;
                if(!some_blocked_occupant) { in[s]=0; changed=true; }
            }
        }
        int n=0; for(char c:in) n+=c; return n;
    }
};

int main() {
    int failures=0;
    const Mesh meshes[]={{2,2},{2,3},{3,3},{4,4},{5,5},{8,8}};
    struct Expect { Policy p; bool deadlock_possible; };
    const Expect cases[]={{Policy::XY,false},{Policy::SAQR,false},{Policy::DUATO_DEDICATED,false},
                          {Policy::UFA,true},{Policy::CTY_NO_ESCAPE,true},{Policy::O1TURN,false},{Policy::O1TURN_SHARED,true}};
    for(auto m:meshes) for(auto c:cases) {
        Checker ch{m,c.p,{}}; int size=ch.run();
        bool found=size>0;
        // CTY without the escape offer needs a turn cycle that 2- and 3-wide meshes
        // cannot fill (hand-traced on 2x2: the closing S hop would need a compliant
        // VC0 occupant, which would already be at its destination). Expect it from 4x4.
        bool expect=c.deadlock_possible && !(c.p==Policy::CTY_NO_ESCAPE && (m.kx<4 || m.ky<4));
        bool ok=found==expect;
        // 2-wide meshes: a 2x2 turn cycle exists, so negative controls should already fail there.
        std::printf("%dx%d  %-38s maximal deadlock set: %4d slots  -> %s%s\n",m.kx,m.ky,name(c.p),size,
                    found?"DEADLOCK POSSIBLE":"deadlock-free",ok?"":"   <-- UNEXPECTED");
        failures+=!ok;
    }
    std::printf(failures?"saqr_deadlock_check: FAIL (%d unexpected)\n":"saqr_deadlock_check: PASS\n",failures);
    return failures?1:0;
}
