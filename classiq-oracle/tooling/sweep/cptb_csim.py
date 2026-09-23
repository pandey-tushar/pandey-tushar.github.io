"""exact classical phase simulation of an op list (x/cx/ccx/c3x/mcx/cz/z) on
basis inputs |x,y,0..0>: returns the 64x64 phase table of the forward stream.
(valid for forward + mirror since RCCX relative phases cancel under the mirror)"""
import numpy as np

def phase_table(ops, n):
    tab = np.zeros((64, 64), dtype=np.int8)
    for x in range(64):
        for y in range(64):
            b = [0] * n
            for i in range(6): b[i] = (x >> i) & 1; b[6 + i] = (y >> i) & 1
            ph = 0
            for op in ops:
                k, q = op[0], op[1:]
                if k == 'x': b[q[0]] ^= 1
                elif k == 'cx': b[q[1]] ^= b[q[0]]
                elif k == 'ccx': b[q[2]] ^= b[q[0]] & b[q[1]]
                elif k == 'c3x': b[q[3]] ^= b[q[0]] & b[q[1]] & b[q[2]]
                elif k == 'mcx': b[q[-1]] ^= int(all(b[c] for c in q[:-1]))
                elif k == 'cz': ph ^= b[q[0]] & b[q[1]]
                elif k == 'z': ph ^= b[q[0]]
            tab[x, y] = ph
    return tab
