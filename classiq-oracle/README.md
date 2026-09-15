# Classiq Quantum Circuit Challenge — exact phase oracle for the 64x64 logo

Implements U|x,y> = (-1)^F(x,y) |x,y>, where F is the 64x64 Classiq logo
(1097 set pixels), with index i = y*64 + x; x on qubits 0-5 (little-endian),
y on qubits 6-11, and six clean ancillas on qubits 12-17 that are returned
to |0>.

## Measured

| metric | value |
|---|---|
| width | 18 |
| depth | 249 |
| CX | 520 |
| u3 | 536 |

Depth and CX are measured after
`transpile(basis_gates=['u3','cx'], optimization_level=2)`; optimization
levels 0, 1, 2 and 3 all report 249 / 520.

## Verification

`verify18.verify_sv18` on the full 2^18 statevector prepared as
|+>^12 (x) |0>^6: PASS, err 4.18e-15 (bound 1e-10), including global phase.

## Files

- `submission24.qasm` — OpenQASM 2.0, u3 + cx only.
- `submission24.qmod` — the same circuit as literal Qmod statements.
