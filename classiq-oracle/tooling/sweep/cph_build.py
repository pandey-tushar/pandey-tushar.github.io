"""CP-H builder: hand-written gate lists with per-wire truth-table bookkeeping.

Wires are the checker's qubits: x_k = k, y_k = 6+k, ancillas 12..17.
Each wire holds a 4096-entry truth table (python int, bit i = x + 64*y).
"""
import numpy as np

from cpae_core import ops_to_qc, real_depth, mirror, sv_check

N = 4096
ALL = (1 << N) - 1


def inp(q):
    """truth table of data qubit q (0..11)."""
    return sum(1 << i for i in range(N) if (i >> q) & 1)


def lift_x(tx):
    """64-entry x-side table -> 4096-entry table."""
    return sum(1 << i for i in range(N) if (tx >> (i & 63)) & 1)


def lift_y(ty):
    return sum(1 << i for i in range(N) if (ty >> (i >> 6)) & 1)


class Builder:
    def __init__(self):
        self.ops = []
        self.T = [inp(q) if q < 12 else 0 for q in range(18)]
        self.phase = 0            # accumulated diagonal (cz/ccz) as table

    def x(self, t):
        self.ops.append(('x', t))
        self.T[t] ^= ALL

    def cx(self, c, t):
        assert c != t
        self.ops.append(('cx', c, t))
        self.T[t] ^= self.T[c]

    def ccx(self, a, b, t):
        assert len({a, b, t}) == 3
        self.ops.append(('ccx', a, b, t))
        self.T[t] ^= self.T[a] & self.T[b]

    def cz(self, a, b):
        self.ops.append(('cz', a, b))
        self.phase ^= self.T[a] & self.T[b]

    def ccz(self, a, b, c):
        self.ops.append(('ccz', a, b, c))
        self.phase ^= self.T[a] & self.T[b] & self.T[c]

    def is_(self, w, table, name=''):
        assert self.T[w] == table, f'wire {w} is not {name}'

    def depth(self, ops=None):
        return real_depth(ops_to_qc(ops if ops is not None else self.ops))

    def full(self):
        """forward + mirror op list."""
        fwd = [op for op in self.ops if op[0] not in ('cz', 'ccz')]
        return self.ops + mirror(fwd)

    def check_full(self, shape='LOGO'):
        return sv_check(ops_to_qc(self.full()), shape)
