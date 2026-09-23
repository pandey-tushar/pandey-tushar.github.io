# Status: forward-only comparator design (checkpoint)

Best verified submission: `../cpev_best.qasm`, depth 249 / 520 CX.
Passes the official check style (random product-phase inputs, err ~1e-16).

## Rules this design follows

One forward stream, one mirror. No uncompute before the mirror; garbage stays
on the wires; phases are read with cz (differential around an RCCX when the
item is a fresh product). RCCX relative phases cancel under the single mirror.

## Verified exact decomposition (0 mismatches, all 4096 inputs)

    F = x5 ~x4 [d <= W2(y)]  ^  x5 x4 [d <= W1(y)]
      ^ P(x) [29<=y<=53]  ^  M(x) [39<=y<=43]  ^  [x=48] [17<=y<=21]

    P = [2,26], M = [27,48]
    x fold (4 CX, no Toffoli): c_i = x_i ^ ~x3 (i<3), s = x3 ^ x4,
    d = c + ~s = |x-40| on [32,47] and |x-55| on [48,63].

W2 / W1 are the half-widths of the two disks per row (W = 8 on rows 17..21).

## Disk core = one comparator (cptb_core.py)

    m  = x4 ^ y5 (cross CX, taken first)
    E4 = x5 ~m,  E3 = E4 V3,  E2 = E3 ~d2,  E1 = E2 ~d1,  E0 = E2 ~d1 ~d0
    delta_i = c_i ^ W_i  (cross CX onto the W wires)
    phase = E4 W3 + E3 ~c2 + E2 (c1^c2) + E1 (c0^c1) + E0 (1^c0^s)

Formula check: 0 mismatches.  Gate-level check (cptb_csim.py, exact classical
phase simulation with the y targets on 5 extra wires): 0 mismatches.

## Open problem: the y prep

The y side must hold V3 (exact), W3 (exact, or read differentially), W2, W1,
W0 (on V3 rows only) on 9 wires.  Measured:

- SAT (cptb_ysat.py / cptb_ystage.py): 2 levels UNSAT; 3..5 levels, G 3..4,
  L 2..3: every run timed out (25..60 min), also with y5 freed.
- Greedy SOP: ~22-24 cubes for all targets; binary width labels are already
  the cheapest relabelling (cptb_relabel.py).
- Recoding y (add 4 or 7 by half, fold) keeps the tables at ~22 cubes.

Next: hand-build the y prep from the formulas, then measure the disk core.

## Other results in this folder

- cpta_tensor.py: relaxed readout rule f in sum_r A_r (x) B_r; the old
  24-round hand x design still needs all 24 rounds under it.
- cpta_deg.py / cpta_setsearch2.py / cpta_prod2.py: degree <= 2 after 6-Toffoli
  setups covers 8/11 (x) and 6/10 (y) functions, but reading them needs
  25-30 products, so degree is the wrong proxy.
- x|y is the minimum-rank 6|6 bit split (rank 10; all others >= 12).
