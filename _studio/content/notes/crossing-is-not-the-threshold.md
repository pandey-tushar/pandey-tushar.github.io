# The crossing is not the threshold

The threshold of a quantum error correcting code is usually read off a plot. One draws
the logical error rate against the physical error rate p for a few code distances, and
the point where the curves cross is reported as the threshold. This works well when the
codes are large. However, most plots one sees, including the one in the
[threshold lesson](/qec-in-practice/threshold.html) of our course, use small distances
such as 3, 5 and 7, and for these the crossing can sit far from the actual threshold.
In this note, we measure how far, for the surface code with a union-find decoder.

## Setup

We consider the rotated surface code with d x d data qubits. Each data qubit is flipped
independently with probability p, once, and the checks are then read perfectly. The
decoder is union-find with clusters grown smallest boundary first, the same one that
runs in the course. For the 2d toric code with perfect syndrome measurements, Delfosse
and Nickerson [1] obtain a threshold of 9.9% for this decoder.

Below the threshold a bigger code fails less often, and above it a bigger code fails
more often. Therefore the curves of two distances cross, and if all the curves passed
through one point, that point would be the threshold. They do not.

## Pairwise crossings

For each pair of consecutive distances in our list, we find the p at which the two curves cross.
We use 100,000 shots per point, with p from 0.06 to 0.11 in steps of 0.005.

| Distances | Crossing | One standard error |
|-----------|----------|--------------------|
| 3 and 5   | 0.074    | 0.070 to 0.077     |
| 5 and 7   | 0.082    | 0.079 to 0.085     |
| 7 and 9   | 0.088    | 0.086 to 0.089     |
| 9 and 11  | 0.094    | 0.091 to 0.096     |
| 11 and 13 | not resolved | |
| 13 and 17 | 0.100    | 0.099 to 0.102     |
| 17 and 21 | 0.101    | 0.098 to 0.103     |

The crossing climbs from 7.4% to about 10% and then stops moving. The last two rows
agree with the 9.9% of [1]. The first row is lower by a quarter. For the pair 11 and 13,
the two curves lie within noise of each other from p = 0.09 to 0.11, so we do not
report a number.

## What goes wrong at small distances

It is easier to see the problem in one column of the data than in the crossings. At
p = 0.08, the logical error rates for d = 3, 5 and 7 are 0.092, 0.096 and 0.095. These
are equal to within a few percent. If these three codes were all we had, we would
conclude that 8% is the threshold, or slightly above it. At d = 21, the logical error
rate at the same p is 0.057. So 8% is well below the threshold, and the small codes
are not able to show it.

This is known as a finite-size effect. Close to the threshold, the logical error rate
depends on p and d mostly through the combination (p - p_th) d^(1/nu), where p_th is
the threshold and nu is a critical exponent. If this were exact, every curve would pass
through the same point at p = p_th. There are correction terms which shrink as d grows,
and at d = 3 they are not small. More precisely, a distance 3 patch has nine data
qubits, eight of which lie on the boundary, and two errors are already enough for the
decoder to guess wrong. Such a patch does not behave like a piece of a large lattice.
The crossing of two small codes measures the threshold together with these
corrections, and in our case the corrections push it down.

## The same happens with matching

One may ask whether this is a defect of union-find. It is not, although union-find
makes it worse. We have reference data for a minimum-weight perfect matching decoder
(pymatching, with samples from stim, 200,000 shots per point) at p = 0.08 and 0.10.
Interpolating between these two points, the curves for d = 3 and 5 cross near 0.093,
and those for d = 5 and 7 near 0.098. Both values are below the matching threshold of
0.1031 found by Wang, Harrington and Preskill [2]. Note that this interpolation uses
only two points, so it is coarse.

Therefore the small distance crossing is low for both decoders. It is much lower for
union-find: 0.074 against 0.093 for the same pair of codes. We do not have an argument
for why the corrections are larger for union-find, and we leave it as an observation.

## Consequences

For this code and noise model, a crossing between two small codes is a lower estimate
of the threshold and not the threshold itself. If a threshold is quoted from d = 3, 5
and 7, one should check whether the pairwise crossings are still moving. If they are,
the number will change with bigger codes.

There are two ways around this. One is to go to larger distances. The other is a
finite-size scaling fit over several code sizes.
We used the second for bivariate bicycle codes on the erasure channel, where large
codes are expensive to simulate; see the
[companion page](/papers/bb-erasure-baselines.html) of that paper.

One can watch the drift directly. In the
[threshold lesson](/qec-in-practice/threshold.html), run the first figure with the
default distances, then add d = 9 and 11 and run it again. The crossing moves to the
right.

## Details

The crossings are found by linear interpolation in log p of the log ratio of the two
logical error rates. The ranges are one binomial standard error and are statistical
only. All runs use fixed seeds. The 9.9% of [1] and the 0.1031 of [2] are for the toric
code, which has no boundary, so the agreement with the rows at large distance is a
consistency check and not a reproduction.

## References

[1] N. Delfosse and N. H. Nickerson, "Almost-linear time decoding algorithm for
topological codes", Quantum 5, 595 (2021). arXiv:1709.06218.

[2] C. Wang, J. Harrington and J. Preskill, "Confinement-Higgs transition in a
disordered gauge theory and the accuracy threshold for quantum memory", Annals of
Physics 303, 31-58 (2003). arXiv:quant-ph/0207088.
