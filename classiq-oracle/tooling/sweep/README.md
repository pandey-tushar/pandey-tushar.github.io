# Round-schedule sweep

Local search for a low-depth exact phase oracle for the 64x64 Classiq logo
at width 18 (12 data + 6 ancilla).

Current verified best: **depth 249, 520 CX** (`../cpev_best.qasm`).
Board leader: 121 depth / 576 CX.

## The idea in five sentences

The oracle factors exactly into an x-side and a y-side joined by 11 `cz`
pairs; that decomposition is verified and is in `cph_terms.py`.  Depth is
set by how many levels of RCCX each side needs, and every construction built
by hand so far computes those 11 functions more or less in sequence, which
lands around 175-185 layers per side.

To approach 120 the functions have to be computed in parallel *rounds*: R
rounds, at most G RCCX per side per round, optionally L permanent CX per
side per round for hosting, with the `cz` pairs read out between rounds.
`cpri_round.py` encodes "does a valid R-round schedule exist?" as SAT; a
smaller feasible R means a shallower circuit.

The sweep runs that question across the whole parameter matrix at once,
including one pair at a time, because the number nobody has yet is the
minimum R each individual function needs.

## Install

    pip install python-sat qiskit numpy

Python 3.9+.  No other dependencies.

## Run

    cd classiq-oracle/tooling/sweep
    python cpri_sweep.py --workers 8 --timeout 7200

`--workers` defaults to the core count; each job is its own process, capped
at `--mem-gb` (default 3) of address space, killed 300 s after its solver
timeout.  Results are appended to `results.csv` as they land, and the sweep
is **resumable** -- rerun the same command and it skips job ids already in
the file.  Per-job stderr goes to `logs/<jobid>.log`, schedules to
`out/<jobid>.pkl`.

Useful flags:

    python cpri_sweep.py --list                 # print the matrix, run nothing
    python cpri_sweep.py --tier 1 --timeout 3600
    python cpri_sweep.py --only mx_pk4          # substring filter on job id
    python cpri_job.py --mode x --pairs k4 --R 3 --timeout 600   # one job

## What the matrix covers

400 jobs in four tiers, cheapest first.

| tier | what | why |
| --- | --- | --- |
| 1 | one pair at a time, x-only and y-only, R = 2..5 | smallest instances; each answer is a hard minimum number of rounds for that function |
| 2 | rings / P-Q / bands / halves, one side at a time, R = 3..8, L = 0,2 | where the interference between functions starts |
| 3 | all 11 pairs, one side at a time, R = 6..12, G = 3,4, L = 0,2,3, maxsel = 3,5 | the per-side feasibility frontier |
| 4 | all 11 pairs, both sides, R = 6..12, L = 0,2, maxsel = 3,5, two seeds | the only tier that produces a whole circuit |

Seeds shuffle the clause order, which changes the solver's search path; they
are not a random restart of the encoding.

## Reading results.csv

One row per job.  `status` is one of:

- `sat` -- a schedule exists.  The row's `pkl` holds it, and it has already
  been checked against the pixel tables (`note` carries `check=True`).
- `unsat` -- proved impossible at that R.  **This is a real result**: it
  raises the floor and rules out everything below it.
- `timeout` -- undecided within the budget.  Says nothing either way.
- `oom`, `crash`, `error` -- see `logs/<jobid>.log`.

Tier-4 `sat` rows also carry `depth`, `cx` and `err`: the schedule was
emitted as a real circuit, transpiled with `optimization_level=2` to
`u3`/`cx`, and verified on the statevector.  `err` below `1e-10` with
`leak` ~ 0 in `note` means it is a valid oracle.  `note` says `LIVE` or
`DEAD>200`; anything over depth 200 is not worth pursuing.

To check any QASM file the way the challenge checker does:

    python cpri_verify.py ../cpev_best.qasm
    # depth 249  cx 520  err 7.27e-15  leak 3.04e-30  PASS

(The global phase is divided out first -- a transpiled u3/cx circuit picks
up a phase QASM 2.0 cannot express; `cpev_best.qasm` carries -pi/8.)

## Honest expectation

On four cores here, single-pair tier-1 jobs were still undecided after 120 s,
and full 11-pair joint instances ran for an hour without deciding.  Nothing
guarantees the big instances finish at any timeout.

The tiers are ordered so the sweep pays out early if it pays out at all:
tier 1 and tier 2 are the ones expected to return answers, and an `unsat`
there is worth more than a `timeout` in tier 4, because it tells you which
function is the one forcing the depth.  Run tier 1 and 2 to completion before
spending cores on tiers 3 and 4.

## Files

| file | what |
| --- | --- |
| `cpri_sweep.py` | the matrix driver (parallel, resumable, CSV) |
| `cpri_job.py` | one job: encode, solve, check, emit, measure |
| `cpri_round.py` | the SAT encoding of an R-round schedule |
| `cpri_emit.py` | schedule -> real circuit, with the cz readout placement |
| `cpri_verify.py` | verify a QASM file |
| `cpri_hand.py`, `cpri_design.py` | the hand-built 24-round x schedule and its residual/coverage report, for reference |
| `cpri_side.py`, `cpri_xonly.py`, `cpri_diag.py` | single-instance drivers kept from the interactive runs |
| `cph_terms.py` | the 11-pair decomposition and every x- and y-side term, with a self-test that asserts 0 pixel mismatches |
| `cph_x.py`, `cph_v1.py`, `cph_build.py` | the exact hand-built x side (31 RCCX, 184 forward layers) and the shared setup |
| `cpae_core.py` | ops -> circuit, mirror, transpiled depth, statevector check |

Self-test of the decomposition itself:

    python cph_terms.py      # must print 0 mismatches
