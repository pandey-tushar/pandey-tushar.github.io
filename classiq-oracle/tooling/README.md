# Tooling

Support code for building and checking the oracle. Kept here so the work
survives a container restart.

## Verification and metrics

- `logo.py` — `logo_pixel(x, y)`, `build_logo()`, `challenge_metrics`.
- `verify18.py` — `verify_sv18(qc, fv)`, the full 2^18 statevector check on
  |+>^12 (x) |0>^6, comparing up to global phase. Build `fv` as
  `np.array([1 if logo_pixel(i & 63, (i >> 6) & 63) else 0 for i in range(4096)], dtype=np.int8)`.
- `cpae_core.py` — `check`, `sv_check`, `real_depth`, `ops_to_qc` / `qc_to_ops`,
  `model_depth`.

## Construction

- `cpej_ir.py` — gate-list IR and the commutation DAG used for scheduling.
- `qmod_build12.py` — `ops_from_qasm`, `ops_from_qmod`, `notebook_metrics`.
- `cpdh_core.py` — the `.prog` format: `parse`, `replay`, `check_block`,
  `measure`, `want_mask`.
- `cpdv_z4.py` — Margolus / RCCX diagonal-phase tables.
- `cpdw_mask.py` — exact 4096-bit mask bookkeeping.
- `cpdp_base.py` — base construction.
- `pack23.py` — packages a QASM file into the submission `.qasm` + `.qmod` pair.

## Circuits

| file | width | depth | CX | verify_sv18 |
|---|---|---|---|---|
| `cpen_best.qasm` | 18 | 258 | 520 | PASS, 6.11e-15 |
| `cpej_best.qasm` | 18 | 259 | 516 | PASS, 5.60e-15 |
| `cpdp_best.qasm` | 18 | — | — | earlier base |

Depth and CX after `transpile(basis_gates=['u3','cx'], optimization_level=2)`;
both current circuits report the same numbers at level 3.

`cpen_best.qasm` has the lower depth and `cpej_best.qasm` the lower CX count.
Depth is the primary metric and CX the tiebreaker, so `cpen_best.qasm` is the
better of the two; `submission23.*` in the parent directory still packages
`cpej_best.qasm`.

## Notes

- `CLAUDE.md` — task definition and working directives.
- `FACTS.md` — neutral log of each attempt and its measured result.
- `RECORD_FULL.md` — the full experimental record.
- `results/` — per-run measurement logs.
