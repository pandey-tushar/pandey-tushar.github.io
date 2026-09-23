"""phase 1 of the y prep (one local uncompute, approved): from raw y build V3
on wire 17; build W3 and read E4*W3 (A1 = 12 must hold E4); then uncompute W3
and all temporaries (13, 14, 15, 16 back to 0).  Physical wires:
y0..y5 = 6..11, y ancillas 15 16 17, x ancillas 12 (E4) 13 14 (temps here)."""
Y0, Y1, Y2, Y3, Y4, Y5 = 6, 7, 8, 9, 10, 11
T1, T2, V3W = 15, 16, 17
T3, T4 = 13, 14
A1 = 12

def X(*ws): return [('x', w) for w in ws]

def temps():
    """T1 = y1 y0 ; T2 = ~q ; T3 = y4 ~y5 ; T4 = ~r = [C in {0,6,7}]"""
    ops = [('ccx', Y1, Y0, T1)]
    ops += X(Y2, T1) + [('ccx', Y2, T1, T2)] + X(Y2, T1)            # ~y2 ~p
    ops += X(Y5) + [('ccx', Y4, Y5, T3)] + X(Y5)                     # y4 ~y5
    ops += [('ccx', Y2, Y1, T4)]                                     # y2 y1
    ops += X(Y2, Y1, Y0) + [('c3x', Y2, Y1, Y0, T4)] + X(Y2, Y1, Y0) # ~y2~y1~y0
    return ops

def v3_terms():
    ops = []
    # A: ~y4 q  (q = ~T2)
    ops += X(Y4, T2) + [('ccx', Y4, T2, V3W)] + X(Y4, T2)
    # B: ~y4 (y5^q)(y3^q):  Y5,Y3 ^= T2 -> hold y5^~q ; controls read their complements
    ops += [('cx', T2, Y5), ('cx', T2, Y3)]
    ops += X(Y4, Y5, Y3) + [('c3x', Y4, Y5, Y3, V3W)] + X(Y4, Y5, Y3)
    ops += [('cx', T2, Y5), ('cx', T2, Y3)]
    # C1: y4 ~y5 y3 ~y2
    ops += X(Y2) + [('c3x', T3, Y3, Y2, V3W)] + X(Y2)
    # C2: y4 ~y5 ~y3 ~r
    ops += X(Y3) + [('c3x', T3, Y3, T4, V3W)] + X(Y3)
    return ops

def w3_readout():
    """W3 = y4 ~y5 ~y3 r on T1 (after T1,T2 are cleared); cz with E4; clear."""
    w = X(Y3, T4) + [('c3x', T3, Y3, T4, T1)] + X(Y3, T4)
    return w + [('cz', A1, T1)] + w

def phase1():
    t = temps()
    t12 = t[:6]                      # T1, T2 construction (with their X wrappers)
    ops = t + v3_terms()
    ops += [inv(o) for o in reversed(t12)]          # clear T2, T1
    ops += w3_readout()
    ops += [inv(o) for o in reversed(t[6:])]        # clear T3, T4
    return ops

def inv(o):
    m = {'ccx': 'ccx_dg', 'c3x': 'c3x_dg'}
    return (m.get(o[0], o[0]),) + tuple(o[1:])
