# Brief for a fresh Cowork session: Classiq logo phase oracle, get to the top of the board

Repo: pandey-tushar/pandey-tushar.github.io, branch claude/classiq-challenge-repo-77k6q6,
folder classiq-oracle/tooling (read FACTS.md first, then sweep/cptr_results.txt tail).
Deadline: Sep 30, 2026. You are on my machine: the Classiq SDK (authenticated) and qiskit
are available here. Work in Python, plan first, run after I approve, measure everything.

## The problem
Exact phase oracle U|x,y> = (-1)^F(x,y)|x,y> for the 64x64 Classiq logo (F has 1097 ones
of 4096). x = qubits 0-5, y = qubits 6-11, six clean ancillas 12-17 that must return to
|0>. Width <= 18. Score = depth after transpile to u3/cx (opt 3), CX count as tiebreak.
Verifier: statevector on all 4096 inputs, |phase error| < 1e-10, zero leakage into ancillas.
Submission = a .qmod plus the matching .qasm (QASM 2.0, one register, u3/cx).

Truth table: `from cpae_core import SHAPES, fvec; f = fvec(SHAPES['LOGO'])` (index = x + 64 y).
Verified closed form (FACTS.md): F = R1 ^ R2t ^ D1 ^ D2, all four disjoint, with
  R1 = [2 <= x <= 26] & [29 <= y <= 53]
  R2t = [27 <= x <= 48] & [39 <= y <= 43]
  D1 = (x-55)^2 + (y-41)^2 <= 42
  D2 = (x-40)^2 + (y-19)^2 <= 72
Equivalent: F = [bL(y) <= aL(x)] ^ [bD(y) <= aD(x)] on 3-bit codes (cpdq_codes.py), and a
joint 4+4-bit code whose phase stage is 4 gates (C3Z, CCZ, CZ, C3Z), measured 63 depth / 47 CX.

## Where things stand
Ours: 249 depth / 520 CX (cpev_best.qasm = submission24). Board (Sep 27): 106/279, 109/503,
111/558, 114/497, 120/543, 121/324, 128/363, 128/405, 138/393, 148/670. Read of the top:
279 CX = 93 relative-phase Toffolis (3 CX each) = 46 forward + 46 mirrored + readout; depth
106 = two passes of ~50 = 7 levels of 6-7 Toffolis covering all 18 wires, nearly no CX.
The 503-558 CX entries are the same thing with full 6-CX Toffolis, i.e. what a synthesis
engine emits. Conclusion: the leaders compute the logo predicate in place with ~46
Toffolis and mirror once; several of them very likely let the Classiq engine do it.

## Priority 1 (do this first, it needs the SDK and has never been run): Classiq engine on the arithmetic form
Build qmods with QNum x, y (6 bits, unsigned) and let Classiq synthesize the predicate:
  a) `phase(expr, pi)` where expr is the boolean F written arithmetically as above
     (try: squared distances; rectangles as range checks; LEFT as |y-41| <= r(x);
     the 3-bit-code comparator form; ESOP over bits as in cpub_classiq.py).
  b) kickback: aux in |->, `aux ^= expr` inside within_apply (cpub_classiq.py has the skeleton).
  c) also try expressing the two disks/rectangles as separate boolean QBits computed
     into ancillas and XORed, and letting the engine choose.
Constraints(max_width=18, optimization_parameter='depth'); also try max_width 17 and 16
(the engine sometimes finds shallower circuits with a tighter width), and the
preferences / optimization level knobs. For each result: export QASM2, transpile with
qiskit to u3/cx opt 3, print width / depth / CX, run the 4096-input statevector check
(cpub_classiq.measure does all of that; data = q0-11 or the last 12, check both).
Log every (formulation, constraints) -> (depth, CX, pass/fail) line in a results file.
Expected: full-Toffoli circuits around 110-150 depth / 500 CX. That alone is top 5.

## Priority 2: cut the CX of any engine circuit in half without changing depth
In a compute; phase; uncompute circuit the Toffolis come in mirrored pairs around a
diagonal middle, so each CCX can be replaced by RCCX (Margolus, 3 CX, 7 depth) and its
mirror by RCCX^-1: the relative phases cancel exactly (FACTS.md). Do the replacement on the
exported circuit (qiskit), re-verify by statevector, re-transpile. This is how 503 -> ~280.
Then re-time: RCCX is also shallower than CCX (7 vs 11), so depth should drop too.

## Priority 3 (no SDK needed): the in-place code transform already in the repo
sweep/cpuc_inplace.py anneals a 9-wire (6 data + 3 clean) Toffoli-level circuit that
overwrites x in place until 4 wires hold the 4-bit x-code (targets in cpuc_code810.pkl);
same for y; sweep/cpuc_assemble.py glues T_x || T_y, the measured 4-gate phase stage and one
global mirror, verifies and reports. Pipeline measured 205 depth / 311 CX on inexact
checkpoints; the searches plateau 14-17 bits (of 256) from exact at 65-81 forward depth.
Levers not yet tried: free code labelling (objective = pairs of inputs from different
classes sharing a code word, then re-derive the phase stage with cpee's degree solver),
and hand-built reversible ripples (subtract constant, |.| with a sign wire, compare against
a 3-bit code) instead of annealing.

## Do not repeat (all measured, see FACTS.md / RECORD_FULL.md / sweep/cptr_results.txt)
SAT synthesis of whole-F XAGs (15 days, nothing below 249); 18-wire Toffoli-level
annealing (deficiency floors 83-113); mapping our 41-66-AND XAGs onto 18 wires (they need
17-33 live values); monomial-by-monomial CZ/CCZ emission (stalls at 172 monomials); the
wide code route with x, y kept intact (needs 12 clean wires); width annealing of XAGs;
Classiq DEPTH optimisation on literal gate lists (no-op); parity networks (713).

## Working rules
Plan, then run after approval. Reduced test first, then the full run. Long jobs print a
progress line every 10 s and checkpoint. Every circuit claimed must pass the 4096-input
statevector check with ancillas back to |0>. Report measured numbers only, no estimates
presented as results. Log results as you go (append to a results file), commit and push
to the branch above. Never say "nothing works": say which constraint bound, with the number.
