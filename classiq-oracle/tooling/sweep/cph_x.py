"""CP-H x side, hand ordered.  Outputs land on wires already holding other
values and are read out by differential cz pairs (cz before and after the
product), so nothing is uncomputed inside the forward stream.

Required x-function per y-label (from cph_terms pairing):
  P      [2..26]          Q     [27..61]        Y1721  {32,48}
  Y1523  [33..47]         Y13r  [34..46]        Y12r   [36..44]
  Y36r   [51..59]         Y11r  [38..42]        Y35r   [53..57]
  Y37r   [50..60]
"""
from cpae_core import ops_to_qc, real_depth
from cph_terms import rng, setof, bit

X5, X4, B3, B2, B1, B0, A1, A2, A3 = 5, 4, 3, 2, 1, 0, 12, 13, 14
ALL = (1 << 64) - 1
REQ = {'P': rng(2, 26), 'Q': rng(27, 61), 'Y1721': setof(32, 48),
       'Y1523': rng(33, 47), 'Y13r': rng(34, 46), 'Y12r': rng(36, 44),
       'Y36r': rng(51, 59), 'Y11r': rng(38, 42), 'Y35r': rng(53, 57),
       'Y37r': rng(50, 60)}


def sset(*vals):
    """x's whose |s| (after the maps) is in vals, all blocks."""
    out = 0
    for x in range(64):
        t = (x & 15) ^ (15 if (x >> 4) & 1 else 0)
        s = (t & 7) if t & 8 else (8 - t) & 7
        if s in vals:
            out |= 1 << x
    return out


class XB:
    def __init__(self):
        self.ops = []
        self.T = {w: 0 for w in (X5, X4, B3, B2, B1, B0, A1, A2, A3)}
        for k in range(6):
            self.T[k] = bit(k)
        self.acc = {k: 0 for k in REQ}

    def x(self, t):
        self.ops.append(('x', t)); self.T[t] ^= ALL

    def cx(self, c, t):
        self.ops.append(('cx', c, t)); self.T[t] ^= self.T[c]

    def ccx(self, a, b, t):
        assert len({a, b, t}) == 3
        self.ops.append(('ccx', a, b, t)); self.T[t] ^= self.T[a] & self.T[b]

    def cz(self, w, *labels):
        self.ops.append(('czl', w, labels))
        for L in labels:
            self.acc[L] ^= self.T[w]

    def out(self, a, b, t, *labels):
        self.cz(t, *labels); self.ccx(a, b, t); self.cz(t, *labels)

    def is_(self, w, tab, name=''):
        assert self.T[w] == tab, f'wire {w} != {name}'

    def depth(self):
        ops = [op if op[0] != 'czl' else ('cz', op[1], 15) for op in self.ops]
        return real_depth(ops_to_qc(ops))

    def report(self):
        return [k for k in REQ if self.acc[k] != REQ[k]]


def build():
    b = XB()
    # ------------------------------------------------ setup: maps and hosts
    for t in (B3, B2, B1, B0):
        b.cx(X4, t)
    b.x(B3)
    b.ccx(B3, B0, B1)            # b1'
    b.ccx(B1, B0, A1)            # A1 = m10' = [3,7]
    b.cx(B1, B0); b.cx(A1, B0)   # B0 = b1'|b0
    b.ccx(B3, B0, B2)            # b2'
    b.x(B3)
    b.cx(A1, B0); b.cx(B1, B0)   # B0 = b0
    b.ccx(X5, X4, A3)            # m54
    b.cx(A3, X5)                 # X5 = x5~x4
    b.cx(A3, X4)                 # X4 = ~x5x4
    b.is_(A1, sset(3, 7), 'm10')
    # ---------------- stage A: {0,1}*P  host ~x5~x4 on X5, temp V on B1, out on B0
    b.cx(B1, B2); b.cx(B0, B1); b.x(B2); b.x(B1)
    b.ccx(B2, B1, A2)                                 # A2 = [0,7]
    b.x(B1); b.x(B2); b.cx(B0, B1); b.cx(B1, B2)
    b.is_(A2, sset(0, 7), '[0,7]')
    b.cx(A3, X5); b.x(X5); b.cz(X5, 'P')              # ~x5 * P
    b.cx(X4, X5)                                      # X5 = ~x5~x4
    b.x(B3); b.ccx(B3, A2, B1); b.x(B3)               # B1 = b1' ^ V
    b.out(X5, B1, B0, 'P')
    b.x(B3); b.ccx(B3, A2, B1); b.x(B3)               # B1 = b1'
    b.out(X5, B1, B0, 'P')
    b.cx(X4, X5); b.x(X5); b.cx(A3, X5)               # X5 = x5~x4
    b.cz(X5, 'Y1523', 'Q')                            # [32..47]*(Y1523^Q)
    # ---------------- stage C: chain -> [0]; {32}; [27..31]
    b.ccx(B2, A1, A2)                                 # A2 = [0]
    b.is_(A2, sset(0), '[0]')
    b.x(B3); b.ccx(B3, A2, A3); b.x(B3)               # A3 = m54 ^ Z
    b.out(X5, A3, X4, 'Y1721', 'Y1523')               # {32}
    b.x(B3); b.ccx(B3, A2, A3); b.x(B3)               # A3 = m54
    b.x(B3); b.ccx(B3, A2, X5); b.ccx(B3, B2, X5); b.x(B3)   # X5 = x5~x4 ^ Z ^ T
    b.out(X4, X5, B0, 'P', 'Q')                       # [27..31]
    b.x(B3); b.ccx(B3, B2, X5); b.x(B3)               # X5 = x5~x4 ^ Z
    # ---------------- stage D: chain -> [7]; [48]; offset
    b.cx(B1, B2); b.cx(B0, B1); b.x(B2); b.x(B1)
    b.ccx(B2, B1, A2)                                 # A2 = [7]
    b.x(B1); b.x(B2); b.cx(B0, B1); b.cx(B1, B2)
    # (A2 = [7] up to junk on dead columns)
    b.ccx(B3, A2, X4)                                 # X4 = ~x5x4 ^ {32} ^ E15
    b.out(A3, X4, B3, 'Y1721', 'Q')                   # [48]
    b.ccx(B3, A2, X4)                                 # X4 = ~x5x4 ^ {32} ^ {48}
    b.cx(X5, A2); b.cx(A3, A2)                        # A2 = [7] ^ Z ^ x5
    # ({31} garbage is already cancelled by the B0 junk on the chain)
    # ---------------- stage E: ring chain, outputs on B3 (x5~x4) and X4 (m54)
    b.out(X5, A2, B3, 'Y13r')
    b.out(A3, A2, X4, 'Q')
    b.cx(A1, B1); b.ccx(B2, B1, A2); b.cx(A1, B1)     # + [6] -> [6,7]
    b.out(A3, A2, X4, 'Y37r')
    b.cx(A1, B0); b.ccx(B2, B0, A2); b.cx(A1, B0)     # + [5] -> [5,6,7]
    b.out(X5, A2, B3, 'Y12r')
    b.out(A3, A2, X4, 'Y36r')
    b.cx(B1, B2); b.cx(B0, B1); b.x(B1)               # B2 = b2'^b1', B1 = ~(b1'^b0)
    b.ccx(B2, B1, A2)                                 # + [3,4] -> [3..7]
    b.x(B1); b.cx(B0, B1); b.cx(B1, B2)
    b.out(X5, A2, B3, 'Y11r')
    b.out(A3, A2, X4, 'Y35r')
    return b


if __name__ == "__main__":
    b = build()
    bad = b.report()
    print("bad labels", bad)
    for k in bad:
        d = b.acc[k] ^ REQ[k]
        print("  ", k, "wrong at x =", [x for x in range(64) if (d >> x) & 1])
    print("depth", b.depth(), "rccx", sum(1 for o in b.ops if o[0]=="ccx"))
