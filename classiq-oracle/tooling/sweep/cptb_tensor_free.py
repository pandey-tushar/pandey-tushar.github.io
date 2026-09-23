"""is a 64-entry table affine in the 6 input bits?"""
from cpri_round import bit
ALL = (1 << 64) - 1
def affine(T):
    rows = []
    for v in [ALL] + [bit(i) for i in range(6)]:
        for r in rows:
            if v >> (r.bit_length() - 1) & 1: v ^= r
        if v: rows.append(v); rows.sort(reverse=True)
    for r in rows:
        if T >> (r.bit_length() - 1) & 1: T ^= r
    return T == 0
