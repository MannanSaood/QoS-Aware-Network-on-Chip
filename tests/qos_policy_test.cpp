#include "../simulators/booksim_qos/qos_policy.hpp"
#include <iostream>
int main() {
    qos::Schedule s;
    int hp=qos::priority(0,10,"weighted",4), lp=qos::priority(1,0,"weighted",4);
    int hp_wins=0,lp_wins=0;
    for(int i=0;i<10000;++i) {
        bool h=s.prefer(hp,lp); (h?hp_wins:lp_wins)++; s.grant(h?0:1);
    }
    assert(hp_wins==7500 && lp_wins==2500);
    // Failed/unaccepted arbitration must not advance the service schedule.
    assert(s.preferred()==0); for(int i=0;i<100;++i) assert(s.prefer(hp,lp));
    assert(s.preferred()==0);
    // Idle preferred class allows borrowing without losing its next turn.
    s.grant(1); assert(s.preferred()==0);
    assert(qos::priority(1,0,"aged",4)>qos::priority(0,33,"aged",4));
    assert(qos::priority(0,10000,"strict",4)>qos::priority(1,0,"strict",4));
    assert(qos::priority(0,100,"age",4)==qos::priority(1,100,"age",4));
    for(int cl=0;cl<2;++cl) for(int birth=0;birth<10000;++birth) {
        assert(qos::tagged_class(qos::priority(cl,birth,"weighted",32))==cl);
        assert(!s.prefer(qos::priority(cl,birth+1,"weighted",32),qos::priority(cl,birth,"weighted",32)));
    }
    std::cout<<"QoS policy: weighted service, borrowing, age, strict and 20,000 class/age checks PASS\n";
}
