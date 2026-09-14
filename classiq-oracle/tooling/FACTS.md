# Facts and attempts (numbers only; details in RECORD_FULL.md and cp??_results.txt)

## Standings (Sep 14)
Board: 1st 142 depth / 557 CX; 2nd 166 / 348. Ours (uploaded): 270 / 516,
submission22.qasm + submission22.qmod (= cpdp_best.qasm).

## Target structure (verified on all 4096 inputs)
- F = R1 ^ R2t ^ D1 ^ D2, disjoint: R1 = [2,26]x[29,53]; R2t = [27,48]x[39,43];
  D1 = disk (x-55)^2+(y-41)^2 <= 42 (137 px); D2 = disk (x-40)^2+(y-19)^2 <= 72
  (225 px). GF(2) rank of F = 10. LEFT = R1^R2t^D1 = [|y-41| <= r(x)].
  F = [bL(y) <= aL(x)] ^ [bD(y) <= aD(x)] on 3-bit codes (cpdq_codes.py).
- Walsh support 4095/4096. ANF over raw bits: 886 monomials, max degree 12.
  Every element of the rank-10 column/row spaces has ANF degree 5 or 6.

## Measured primitive costs (u3/cx, opt2 = opt3)
Margolus/RCCX 7 layers / 3 CX (slot a read at layer 4, +1 per extra reader;
slot b at layers 2 and 6, +5; same-target chain +5). RC3X 13/6. CCX 11/6.
CZ 3/1 (disjoint CZs in parallel). CCZ 10/6. C3Z 27/14. C4Z 65/36. CX 1/1.
X merges into u3. Margolus relative phase is diagonal (cancels when the same
gate is undone around a diagonal middle). A 6-literal AND tree: forward 17.
Mirror block C;phase;C^-1 = 2*forward + 1 + phase.

## Metric / verifier
qc.depth() after transpile to u3/cx; opt_level >= 2 (depth unchanged by
transpile, CX reduced). Verifier: err < 1e-10, ancillas end |0>, QASM 2.0
single register, u3/cx only. QASM drops global phase; check strict err.

## Attempts (assumption -> result)
- Parity network (CX+Rz diagonal, 18 wires): 713 depth; model floor 682.
- Four serial mirror blocks, hosting on data wires (shipped): R2t 39/71,
  D1 71/142, D2 125/239, R1 43/73; spliced 270/516. All 12 ordered block
  pairs interleaved: best 270. 120 transpiler seeds, 56 control swaps: 270.
- Time-shifted phase hosting, LEFT only, 3 ancillas/side (cpeb): 579/418
  exact; same ops without the 20 CZs: 114.
- Depth-first block trees (cpec): AND-depth-2 D2 form found, 33 nonlinear
  gates, 16 peak live values; shipped-width emission 274 (1 carrier/side),
  224 (2/side), 149 (39 scratch registers).
- Makespan pebbling of that D2 form (cped): K = 6..12 registers no schedule
  found; K = 14 551; 16 403; 20 353; 26 294. Extra ancillas (24/30/36 wires)
  applied to the shipped four blocks: interleave exact only at 18, depth 270.
- Direct synthesis from the truth table (cpee): best affine input basis
  216 ANF monomials (from 886), max degree 12 in every basis; cofactor cut
  at k=6 is 11x11 in every basis (4 code bits per half); SAT XAGs for the 8
  code bits 41 ANDs at AND-depth 3, or 12 shared per half at depth 8-10;
  phase stage on 8 code wires 61 depth / 49 CX; exact builds 327 at 48
  wires, 227 at 92, 173 at 143. At 18 wires with one phase instant:
  8 code dims + 10 separating dims = 18, 0 registers free. Phase gates at
  separate instants: widest instant reads 4 forms (dim >= 12). Build routes
  for one code value with <= 2 clean wires: read-once chain residual 1
  (never 0), two-register program residual 6, mask-directed greedy 640,
  hosted depth-3 XAG infeasible without duplicate gates. Strictly
  increasing AND levels: high-half bit 1 = 4-gate XAG, lookback 2, all
  operands hostable; other bits lookback 3-4 or 300 s SAT cap. Full sweep
  over all 8 bits, k <= 8: running.
- Single-pass identity for both disks via G_i = x_i^x3, a3 = x3^y5,
  a4 = x4^y5 (cpef, before the no-decomposition directive): one comparator
  object 239 / 206 CX exact at 18 wires (D1+D2 shipped over the same
  pixels: 196 / 381); y-bit reads 37, +5 per extra slot-b reader.
- Direct synthesis (cpef): F has 11 distinct subfunctions with y fixed
  and 11 with x fixed; best BDD order 105 nodes, max width 17. ESOP: 83
  cubes / 790 literals exact (>= 707 two-input ANDs; forward >= 589 at 6
  ancillas). BDD profile shrinks at four levels (in-place update not
  injective; per-node registers 105). 4-bit class code: not hostable on
  data wires (odd class sizes; no 2-colourable flip-mask class graph);
  residual after the code 42-49 cubes / 342-404 literals. Fan-out on 4
  functions of 6 wires: 69 reads 202 forward, 37 reads 111; with a copy
  per read 86 and 52; 202 at 18 wires = 202 at 22 wires.
- Register-minimising SAT sweep (cpee E): every code bit has a k=5 XAG with
  lookback <= 2 (four bits lookback 1); one phase instant built exact at 18
  wires: 503 depth / 447 CX (same design at 143 wires: 173 / 889).
- Off-the-shelf tools on F (cpeg): tweedledum PKRM 27150, PPRM 65138,
  xag_synth 1644 @ 102 wires; qiskit PhaseOracle 28955; Diagonal 8170 /
  4094 CX; 83-cube MCX 13411 @ 18. Best BDD of F: 96 nodes.
- Whole-F XAG + reversible pebbling (cpeh): XAGs 41 / 47 / 48 / 78-96 ANDs,
  peak live 26 / 33 / 38 / 19-36. Pebbling K = 6..37: no schedule; K = 38
  (width 50) 2183; no-recompute at 38 registers 757 / 1130 CX exact.
  Undo needs both children live: 36 registers without recomputation, 13
  registers at 46085 AND executions. Irreversible register need: 5.
- Affine automorphisms of F (cpei): group order 1 (exhaustive); best partial
  automorphism agrees on 4072/4096; best translation 4006/4096. Best affine
  basis BDD 85 nodes. Largest all-balanced subspace of the rank-10 x-space:
  dim 1. Walsh support 4096/4096.
- Interleaved whole-image stream at 18 wires (cpei), exact machinery (sv err
  1e-15, leak 1e-32): n Margolus with r CX each -> 25/1: 124; 20/3: 142;
  41/2: 191; 41/1: 223; 41/3: 233; 41/6: 304; 41/9: 352. Known whole-F
  XAGs: 41 ANDs at 38 live (~9 CX/AND), 78-96 ANDs at 19 live.
- u3/CX commutation optimiser on cpdp_best.qasm (cpej): 259 / 516 CX exact
  (cpej_best.qasm; sv err 3.1e-13, leak 4.9e-30; CP-SAT: 258 infeasible for
  the split gate set). Critical path 259 = 143 cx + 116 u3; 142 of 1251 1q
  rotations crossed a CX. Blockers: Rz on CX-target wires (218 of 274 steps).
- Fusion census of the 259 stream (cpel): 152 value instances, 97 distinct
  non-raw masks; nonlinear values shared across the four segments 0; cross-
  segment recompute pairs 2 (affine, 0-2 layers). Nonlinear wires at the
  phase instants 7 / 16 / 12-18 / 8; sum if overlapped 49. Seam DP + 720
  ancilla perms per seam: 259 unchanged. Register-lean segment forms:
  R2t 44/70 at 3-4 ancillas (shipped 39/71), R1 51-60 at 3-4 (shipped 43/73).
