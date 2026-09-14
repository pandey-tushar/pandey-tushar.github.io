# Classiq Quantum Circuit Challenge (Aug 28 - Sep 30, 2026)

## Task
Exact phase oracle U|x,y> = (-1)^F(x,y)|x,y>, F = 64x64 Classiq logo (1,097 px),
12 data qubits (x = qubits 0-5, y = 6-11, little-endian) + up to 6 clean
ancillas (12-17, must end in |0>), width <= 18. Ranked by DEPTH after transpile
to u3/cx (all-to-all), CX count tiebreaker. Submission = .qmod + matching .qasm,
hourly. Deadline Sep 30. Top 5 win.

## DIRECTIVE: THE IMAGE IS ONE OBJECT -- NO DECOMPOSITION OF ANY KIND
- F is ONE Boolean function of 12 bits (one 4096-entry truth table). Do not
  decompose it into rectangles, disks, LEFT/D2 halves, comparators, class
  codes, rank-1 terms, staircases, or any other geometric or algebraic
  parts. Do not build, measure or discuss per-part circuits. Do not use
  the words "shape", "block", "leg", "R1", "R2t", "D1", "D2".
- Synthesize the oracle for F directly from the whole truth table: e.g.
  ESOP / XAG / BDD / SAT-based synthesis of the 12-input function with a
  depth objective on 18 wires, phase gates applied on the values the
  synthesis produces, ancillas and data wires recycled as the synthesis
  dictates. The synthesis may exploit F's structure only as a property of
  the truth table (symmetries, don't-cares, variable ordering), never as
  a human-chosen partition into parts.
- Data wires are computational resources: in-place affine changes and
  hosting values on data wires are allowed anywhere, subject to exact
  restoration at the end.
- Compute/phase/uncompute may be interleaved freely (phase gates fire as
  soon as their operands exist, registers are freed and reused); a single
  global mirror is allowed but not required.
- "Nothing works" is not a result; a measured binding constraint of the
  direct synthesis is.

## Tooling (reuse, do not rewrite)
- `logo.py`: logo_pixel, build_logo, challenge_metrics (the depth metric).
- `cpae_core.py`: check(qc, shape) exact 4096-input replay; sv_check(qc, shape)
  18-qubit statevector (err, ancilla leak); real_depth; ops_to_qc/qc_to_ops.
- `cpdh_core.py`: `.prog` text format (X, CX, AND = Margolus, ~ = complement,
  AND3, CZ, CCZ, C3Z; regs x0..x5 y0..y5 s0..s5), parse, replay, check_block,
  measure(ops, order, lvl, shape, sv); want_mask(shape).
- `verify18.py`: verify_fast / verify_sv18. `score18*.py`: staged scorer.
- Packaging: qmod_build3.py style -- flat QArray[QBit,18] register,
  decimal_precision=17, QASM exported FROM the qmod, gate-list assertion,
  verify_sv18 on the export. The three-port qmod model mis-numbers wires.
- Where results live: FACTS.md (standing facts, standings), RECORD_FULL.md
  (full experimental record), cp??_results.txt (per-line logs). Read them
  as needed; never copy results into this file.

## Working style
Short answers, ASCII-only deliverables, ask before scope changes, measured
numbers only ("not measured" otherwise). Results go in cp??_results.txt logs,
not in this file; this file holds only directions and pointers.
No Co-Authored-By trailers in commits. Do not commit or push unless asked.
