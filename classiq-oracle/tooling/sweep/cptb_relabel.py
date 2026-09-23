"""search increasing relabellings g of widths so the y-side bits of g(W) are
cheap (greedy SOP cube count, care = V3 rows)."""
import itertools
from cptb_yprep import Wt, V3, ALL
cubes = []
for spec in itertools.product((0, 1, 2), repeat=6):
    m = 0
    for y in range(64):
        if all(s == 2 or ((y >> i) & 1) == s for i, s in enumerate(spec)): m |= 1 << y
    cubes.append(m)
def cost(T, C):
    best = 99
    for pol in (0, 1):
        on = (T ^ (ALL if pol else 0)) & C; off = C & ~on
        if on == 0: return 0
        ok = [m for m in cubes if m & off == 0 and m & on]
        cov = 0; n = 0
        while cov != on:
            m = max(ok, key=lambda m: bin(m & on & ~cov).count('1')); cov |= m & on; n += 1
        best = min(best, n)
    return best
res = []
for vals in itertools.combinations(range(16), 5):      # g(2)<g(4)<g(5)<g(6)<g(7)
    g = dict(zip((2, 4, 5, 6, 7), vals))
    # room: g(0),g(1) below g(2) -> g(2)>=2 ; g(3) between g(2),g(4) ; g(8) above g(7)
    if g[2] < 2 or g[4] - g[2] < 2 or g[7] > 14: continue
    tot = 0
    for b in range(4):
        T = sum(1 << y for y in Wt if Wt[y] != 8 and (g[Wt[y]] >> b) & 1)
        tot += cost(T, V3)
    res.append((tot, vals))
res.sort()
print('identity (2,4,5,6,7):', [r for r in res if r[1] == (2, 4, 5, 6, 7)])
for r in res[:10]: print(r)
