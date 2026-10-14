#pragma once
#include <cassert>
#include <string>

namespace qos {
constexpr int CLASS_TAG = 1 << 29;
constexpr int AGE_BASE = 1 << 28;
// The tag is metadata for the weighted arbiter and strict priority for the
// ordinary priority arbiter. Lower birth time wins within a traffic class.
inline int priority(int cl, int born, const std::string &mode, int k) {
    assert(cl >= 0 && cl < 2 && born >= 0 && born < AGE_BASE);
    int p = AGE_BASE - born;
    if ((mode == "weighted" || mode == "strict") && cl == 0) p += CLASS_TAG;
    if (mode == "aged" && cl == 0) p += 8*k;
    return p;
}
inline int tagged_class(int p) { return p >= CLASS_TAG ? 0 : 1; }
struct Schedule {
    int phase = 0;
    int preferred() const { return phase < 3 ? 0 : 1; }
    // Borrow an idle class's slot without consuming its next preference.
    void grant(int cl) { if (cl == preferred()) phase = (phase + 1) % 4; }
    bool prefer(int incoming, int incumbent) const {
        int a=tagged_class(incoming), b=tagged_class(incumbent);
        if(a != b) return a == preferred();
        return incoming > incumbent;
    }
};
}
