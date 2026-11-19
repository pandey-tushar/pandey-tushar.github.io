# Independent reference for the bivariate bicycle code explorer (tools/js/bb-math.js, bb-distance.js).
#
# Builds the check matrices of a BB code with numpy, from the definitions of Bravyi, Cross, Gambetta, Maslov,
# Rall and Yoder, Nature 627, 778 (2024), arXiv:2308.07915, Section 4: S_l is the l x l cyclic shift whose row i
# has its one in column i+1 mod l, x = S_l (x) I_m, y = I_l (x) S_m, H_X = [A | B], H_Z = [B^T | A^T].
# The matrices are built here with np.kron and matrix powers, not with the index arithmetic of the JS code.
# Ranks over GF(2) come from ldpc.mod2.rank (the ldpc package) and are checked against a numpy elimination.
#
# Supports are compared by hash: sha256 of the export body, one line per row, the sorted 0-based column indices of
# its ones separated by single spaces, each line ended by "\n" (the format of the page's download).
#
# Distance, for the two smallest presets, by exhaustive meet-in-the-middle:
#   A Z-type logical is z with H_X z = 0 and z not in the row space of H_Z, i.e. K z != 0 for K a basis of
#   ker H_Z. Every nontrivial z of weight <= w can be translated (the code is invariant under the shifts x, y,
#   which act on L and R alike) so that its support contains qubit L_0 or R_0, and split as z = a + b with a holding
#   that qubit and at most ceil(w/2) - 1 others and |b| <= floor(w/2). So such a z exists iff some pair has
#   H_X a = H_X b and K a != K b. Enumerating all such a and b decides "is there a nontrivial logical of weight
#   <= w" exactly. Same for X type with the roles of H_X and H_Z exchanged.
#   [[72,12,6]]: none of weight <= 5 and one of weight <= 6 exists, so d = 6 exactly.
#   [[90,8,10]]: none of weight <= 9, so d >= 10; a randomized information-set search here finds weight 10.
#
#   python _studio/tools/tests/tools/make_bb_reference.py
import hashlib, json, math, pathlib, random, time
import numpy as np
import ldpc
import ldpc.mod2

OUT = pathlib.Path(__file__).with_name('bb-reference.json')

# Table 3 of arXiv:2308.07915, typed here independently of tools/js/bb-math.js
PRESETS = [
    ('[[72,12,6]]', 6, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 72, 12),
    ('[[90,8,10]]', 15, 3, [(9, 0), (0, 1), (0, 2)], [(0, 0), (2, 0), (7, 0)], 90, 8),
    ('[[108,8,10]]', 9, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 108, 8),
    ('[[144,12,12]]', 12, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 144, 12),
    ('[[288,12,18]]', 12, 12, [(3, 0), (0, 2), (0, 7)], [(0, 3), (1, 0), (2, 0)], 288, 12),
    ('[[360,12,<=24]]', 30, 6, [(9, 0), (0, 1), (0, 2)], [(0, 3), (25, 0), (26, 0)], 360, 12),
    ('[[756,16,<=34]]', 21, 18, [(3, 0), (0, 10), (0, 17)], [(0, 5), (3, 0), (19, 0)], 756, 16),
]


def shift(s):
    S = np.zeros((s, s), dtype=np.uint8)
    for i in range(s):
        S[i, (i + 1) % s] = 1
    return S


def poly(l, m, terms):
    Sl, Sm = shift(l), shift(m)
    M = np.zeros((l * m, l * m), dtype=np.int64)
    for a, b in terms:
        M += np.kron(np.linalg.matrix_power(Sl.astype(np.int64), a), np.linalg.matrix_power(Sm.astype(np.int64), b))
    return (M % 2).astype(np.uint8)


def matrices(l, m, A, B):
    a, b = poly(l, m, A), poly(l, m, B)
    return np.hstack([a, b]), np.hstack([b.T, a.T])


def rank_np(M):
    M = M.copy() % 2
    r = 0
    for c in range(M.shape[1]):
        p = np.nonzero(M[r:, c])[0]
        if not len(p):
            continue
        M[[r, r + p[0]]] = M[[r + p[0], r]]
        rows = np.nonzero(M[:, c])[0]
        rows = rows[rows != r]
        M[rows] ^= M[r]
        r += 1
        if r == M.shape[0]:
            break
    return r


def body(H):
    return ''.join(' '.join(str(c) for c in np.nonzero(row)[0]) + '\n' for row in H)


def sha(H):
    return hashlib.sha256(body(H).encode('ascii')).hexdigest()


def kernel(H):
    K = ldpc.mod2.kernel(H)
    K = K.toarray() if hasattr(K, 'toarray') else np.asarray(K)
    return (K % 2).astype(np.uint8)


def describe(l, m, A, B):
    HX, HZ = matrices(l, m, A, B)
    n = 2 * l * m
    rx, rz = int(ldpc.mod2.rank(HX)), int(ldpc.mod2.rank(HZ))
    assert rx == rank_np(HX) and rz == rank_np(HZ), 'ldpc and numpy ranks disagree'
    assert not ((HX.astype(np.int64) @ HZ.T.astype(np.int64)) % 2).any()
    a = poly(l, m, A)
    b = poly(l, m, B)
    # k = 2 dim(ker A cap ker B), Bravyi et al. Lemma 1
    kab = 2 * (l * m - int(ldpc.mod2.rank(np.vstack([a, b]))))
    k = n - rx - rz
    assert k == kab, (k, kab)
    return dict(n=n, k=k, rankX=rx, rankZ=rz, hashX=sha(HX), hashZ=sha(HZ),
                rowWeightsX=sorted(set(int(v) for v in HX.sum(1))), rowWeightsZ=sorted(set(int(v) for v in HZ.sum(1))),
                colWeightsX=sorted(set(int(v) for v in HX.sum(0))), colWeightsZ=sorted(set(int(v) for v in HZ.sum(0))))


# ---------- exact low-weight logical test ----------
def packcols(M):
    """Each column of M (rows <= 64) as one uint64."""
    w = (1 << np.arange(M.shape[0], dtype=np.uint64)).astype(np.uint64)
    return (M.astype(np.uint64) * w[:, None]).sum(0, dtype=np.uint64) if M.shape[0] else np.zeros(M.shape[1], np.uint64)


def levels(syn, sig, cols, maxw):
    """(syndrome, signature) of every vector supported on `cols` with weight <= maxw."""
    S, G, last = [np.zeros(1, np.uint64)], [np.zeros(1, np.uint64)], [np.full(1, -1)]
    cur = (S[0], G[0], last[0])
    for _ in range(maxw):
        ns, ng, nl = [], [], []
        for t, c in enumerate(cols):
            keep = cur[2] < t
            ns.append(cur[0][keep] ^ syn[c]); ng.append(cur[1][keep] ^ sig[c]); nl.append(np.full(keep.sum(), t))
        cur = (np.concatenate(ns), np.concatenate(ng), np.concatenate(nl))
        S.append(cur[0]); G.append(cur[1]); last.append(cur[2])
    return np.concatenate(S), np.concatenate(G)


def exists_nontrivial(H, Hother, w):
    """Is there z with H z = 0, z not in rowspace(Hother), |z| <= w? Exhaustive, see the header."""
    n = H.shape[1]
    K = kernel(Hother)                       # z trivial iff K z = 0 (given H z = 0)
    assert H.shape[0] <= 64 and K.shape[0] <= 64
    syn, sig = packcols(H), packcols(K)
    bs, bg = levels(syn, sig, list(range(n)), w // 2)
    o = np.lexsort((bg, bs))
    bs, bg = bs[o], bg[o]
    us, first = np.unique(bs, return_index=True)
    lastidx = np.r_[first[1:], len(bs)] - 1
    gmin, gmax = bg[first], bg[lastidx]
    for q0 in (0, n // 2):
        others = [c for c in range(n) if c != q0]
        as_, ag = levels(syn, sig, others, (w + 1) // 2 - 1)
        as_ ^= syn[q0]; ag ^= sig[q0]
        pos = np.clip(np.searchsorted(us, as_), 0, len(us) - 1)
        hit = us[pos] == as_
        if (hit & ((gmin[pos] != ag) | (gmax[pos] != ag))).any():
            return True
    return False


def isd_upper(H, Hother, target, seed, iters):
    """Randomized information-set search: lowest weight nontrivial z found."""
    rng = np.random.default_rng(seed)
    G = kernel(H)
    K = kernel(Hother)
    best = H.shape[1] + 1
    for it in range(iters):
        perm = rng.permutation(H.shape[1])
        M = G[:, perm].copy()
        r = 0
        for c in range(M.shape[1]):
            p = np.nonzero(M[r:, c])[0]
            if not len(p):
                continue
            M[[r, r + p[0]]] = M[[r + p[0], r]]
            rows = np.nonzero(M[:, c])[0]
            M[rows[rows != r]] ^= M[r]
            r += 1
            if r == M.shape[0]:
                break
        Z = np.zeros_like(M); Z[:, perm] = M
        for z in Z:
            wt = int(z.sum())
            if wt < best and ((K.astype(np.int64) @ z) % 2).any():
                best = wt
        if best <= target:
            return best, it + 1
    return best, iters


def main():
    t0 = time.time()
    out = dict(source='arXiv:2308.07915, Table 3; built by _studio/tools/tests/tools/make_bb_reference.py',
               numpy=np.__version__, ldpc=ldpc.__version__,
               hash='sha256 of the rows, each the sorted 0-based column indices of its ones joined by single spaces and ended by a newline',
               presets=[], random=[])
    for name, l, m, A, B, n, k in PRESETS:
        d = describe(l, m, A, B)
        assert (d['n'], d['k']) == (n, k), (name, d['n'], d['k'])
        out['presets'].append(dict(name=name, l=l, m=m, A=A, B=B, **d))
        print(name, 'rank', d['rankX'], d['rankZ'], f'{time.time() - t0:.1f}s', flush=True)

    # exact distance of [[72,12,6]], lower bound of [[90,8,10]], both types
    dist = []
    for name, d_lo_check, find in (('[[72,12,6]]', 5, 6), ('[[90,8,10]]', 9, None)):
        _, l, m, A, B, n, k = next(p for p in PRESETS if p[0] == name)
        HX, HZ = matrices(l, m, A, B)
        rec = dict(name=name)
        for typ, H, Ho in (('Z', HX, HZ), ('X', HZ, HX)):
            none_le = not exists_nontrivial(H, Ho, d_lo_check)
            assert none_le, (name, typ)
            if find:
                assert exists_nontrivial(H, Ho, find), (name, typ)
                rec[typ] = dict(noneAtOrBelow=d_lo_check, existsAtOrBelow=find, method='exhaustive meet-in-the-middle')
            else:
                ub, it = isd_upper(H, Ho, d_lo_check + 1, 7, 20000)
                rec[typ] = dict(noneAtOrBelow=d_lo_check, isdUpperBound=ub, isdIterations=it,
                                method='exhaustive meet-in-the-middle for the lower bound, randomized information set (numpy, seed 7) for the upper bound')
            print(name, typ, rec[typ], f'{time.time() - t0:.1f}s', flush=True)
        dist.append(rec)
    out['distance'] = dist

    # random cases with a fixed seed: polynomials as strings in mixed notations, exponents up to 2l, 2m, so the
    # JS parser must reduce them; repeated monomials are allowed and cancel here by the mod-2 sum
    rnd = random.Random(20261119)
    while len(out['random']) < 12:
        l, m = rnd.randint(1, 9), rnd.randint(1, 9)

        def term():
            a, b = rnd.randrange(2 * l), rnd.randrange(2 * m)
            fx = '' if a == 0 else rnd.choice(['x^%d' % a] + (['x'] if a == 1 else []))
            fy = '' if b == 0 else rnd.choice(['y^%d' % b] + (['y'] if b == 1 else []))
            s = (fx + rnd.choice(['', '*', ' ']) + fy).strip() if fx and fy else (fx or fy or '1')
            return (a, b), s

        def polystr():
            ts = [term() for _ in range(rnd.randint(1, 4))]
            return [t for t, _ in ts], rnd.choice([' + ', '+']).join(s for _, s in ts)
        (A, As), (B, Bs) = polystr(), polystr()
        if not poly(l, m, A).any() or not poly(l, m, B).any():
            continue
        out['random'].append(dict(l=l, m=m, A=As, B=Bs, **describe(l, m, A, B)))
    OUT.write_text(json.dumps(out, indent=1) + '\n', encoding='ascii')
    print('wrote', OUT, f'{time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
