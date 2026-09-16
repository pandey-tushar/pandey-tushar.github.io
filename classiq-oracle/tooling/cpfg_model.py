"""CP-FG: time-first-then-space.  Layer-accurate-ish CP-SAT over the 18
PHYSICAL wires with the exact (affine | node-set | const) wire semantics.

Time = steps of one Margolus window.  Step t:  L layers of CX (+free X) that
rebase wires, then the Toffolis of step t fire, each reading its operands
EXACTLY (70-bit equality) from distinct wires and XORing its node bit into a
distinct target wire.  Data wires may accumulate (stacks), copies cost a CX,
nothing is abstract.  The body B is scheduled; the circuit is B; phase; B^-1.
"""
import sys, pickle, time, collections
sys.path.insert(0, '/home/user/classiq-challenge')
from ortools.sat.python import cp_model
import cpeu_dag as U

BITS = 70
NW = 18
N, PH, nmask, A = U.load()
TERMS = U.simplify_phases(PH)
NN = len(N)
lev, preds, succ = A['lev'], A['preds'], A['succ']
dur = [2 if len(N[k]) == 3 else 1 for k in range(NN)]
FORMS = sorted(set(o for k in N for o in k) | set(o for t in TERMS for o in t))
FID = {o: i for i, o in enumerate(FORMS)}
def bit(o, b): return (o >> b) & 1


def windows(T):
    est = [0] * NN
    for k in sorted(range(NN), key=lambda k: lev[k]):
        est[k] = max([est[j] + dur[j] for j in preds[k]], default=0)
    h = [0] * NN
    for k in sorted(range(NN), key=lambda k: -lev[k]):
        h[k] = dur[k] + max([h[s] for s in succ[k]], default=0)
    lst = [T - h[k] for k in range(NN)]
    return est, lst


def list_schedule(cap):
    """ASAP list schedule of the body: at most `cap` target-steps per step,
    priority = height.  Returns (step per node, T)."""
    est, _ = windows(10**6)
    h = [10**6 - l for l in windows(10**6)[1]]
    done = {}; used = collections.Counter(); t = 0
    while len(done) < NN:
        ready = [k for k in range(NN) if k not in done
                 and all(j in done and done[j] + dur[j] <= t for j in preds[k])]
        ready.sort(key=lambda k: (-h[k], k))
        for k in ready:
            need = [t, t + 1] if dur[k] == 2 else [t]
            if all(used[u] < cap for u in need):
                for u in need: used[u] += 1
                done[k] = t
        t += 1
    T = max(done[k] + dur[k] for k in range(NN))
    return done, T


def build(T, L=2, readers=3, feas=False, center=None, slack=0):
    m = cp_model.CpModel()
    est, lst = windows(T)
    if center is not None:
        est = [max(est[k], center[k] - slack) for k in range(NN)]
        lst = [min(lst[k], center[k] + slack) for k in range(NN)]
    if any(est[k] > lst[k] for k in range(NN)):
        return None
    B = m.NewBoolVar
    # content snapshots: cl[t][l][w][b], l=0 start of step t, l=L after CX phase
    cl = [[[[None] * BITS for w in range(NW)] for l in range(L + 1)] for t in range(T + 1)]
    for w in range(NW):
        for b in range(BITS):
            v = B('c0_%d_%d' % (w, b))
            m.Add(v == (1 if (w < 12 and b == w) else 0))
            cl[0][0][w][b] = v
    cx = {}
    xf = {}
    for t in range(T + 1):
        if t > 0:
            for w in range(NW):
                for b in range(BITS):
                    cl[t][0][w][b] = B('c_%d_%d_%d' % (t, w, b))
        for l in range(1, L + 1):
            for w in range(NW):
                for b in range(BITS):
                    cl[t][l][w][b] = B('cl_%d_%d_%d_%d' % (t, l, w, b))
            for s in range(NW):
                for w in range(NW):
                    if s != w:
                        cx[t, l, s, w] = B('cx_%d_%d_%d_%d' % (t, l, s, w))
            for w in range(NW):
                xf[t, l, w] = B('xf_%d_%d_%d' % (t, l, w))
                inb = [cx[t, l, s, w] for s in range(NW) if s != w]
                outb = [cx[t, l, w, d] for d in range(NW) if d != w]
                m.Add(sum(inb) + sum(outb) <= 1)
                has = B('has_%d_%d_%d' % (t, l, w))
                m.Add(sum(inb) == has)
                for b in range(BITS):
                    inc = B('inc_%d_%d_%d_%d' % (t, l, w, b))
                    m.AddImplication(inc, has)
                    for s in range(NW):
                        if s == w: continue
                        m.AddBoolOr([cx[t, l, s, w].Not(), inc.Not(), cl[t][l - 1][s][b]])
                        m.AddBoolOr([cx[t, l, s, w].Not(), inc, cl[t][l - 1][s][b].Not()])
                    lits = [cl[t][l - 1][w][b], inc, cl[t][l][w][b].Not()]
                    if b == 69:
                        lits.append(xf[t, l, w])
                    m.AddBoolXOr(lits)   # parity: new = old ^ inc (^ xf)
    # Toffolis
    fire = {}; tgt = {}; rd = {}; ft = {}; rdt = {}
    for k in range(NN):
        ts = list(range(est[k], lst[k] + 1))
        for t in ts: fire[k, t] = B('f_%d_%d' % (k, t))
        m.AddExactlyOne([fire[k, t] for t in ts])
        for w in range(NW):
            tgt[k, w] = B('tg_%d_%d' % (k, w))
            for i in range(len(N[k])):
                rd[k, i, w] = B('rd_%d_%d_%d' % (k, i, w))
        m.AddExactlyOne([tgt[k, w] for w in range(NW)])
        for i in range(len(N[k])):
            m.AddExactlyOne([rd[k, i, w] for w in range(NW)])
        for w in range(NW):
            m.Add(tgt[k, w] + sum(rd[k, i, w] for i in range(len(N[k]))) <= 1)
        for t in ts:
            for w in range(NW):
                v = B('ft_%d_%d_%d' % (k, t, w)); ft[k, t, w] = v
                m.AddImplication(v, fire[k, t]); m.AddImplication(v, tgt[k, w])
                m.AddBoolOr([fire[k, t].Not(), tgt[k, w].Not(), v])
                for i in range(len(N[k])):
                    r = B('rt_%d_%d_%d_%d' % (k, i, t, w)); rdt[k, i, t, w] = r
                    m.AddImplication(r, fire[k, t]); m.AddImplication(r, rd[k, i, w])
                    m.AddBoolOr([fire[k, t].Not(), rd[k, i, w].Not(), r])
    # presence of a form on a wire after the CX phase of step t (lazy)
    pres = {}
    def P(o, w, t):
        key = (FID[o], w, t)
        if key not in pres:
            v = B('p_%d_%d_%d' % key); pres[key] = v
            for b in range(BITS):
                if bit(o, b): m.AddImplication(v, cl[t][L][w][b])
                else: m.AddImplication(v, cl[t][L][w][b].Not())
        return pres[key]
    # occupancy / reads per (t,w)
    occ = {}
    for t in range(T):
        for w in range(NW):
            tl = [ft[k, t, w] for k in range(NN) if (k, t, w) in ft]
            tl += [ft[k, t - 1, w] for k in range(NN) if dur[k] == 2 and (k, t - 1, w) in ft]
            o = B('occ_%d_%d' % (t, w)); occ[t, w] = o
            m.Add(sum(tl) == o)
            rl = [rdt[k, i, t, w] for k in range(NN) for i in range(len(N[k])) if (k, i, t, w) in rdt]
            rl += [rdt[k, i, t - 1, w] for k in range(NN) if dur[k] == 2 for i in range(3) if (k, i, t - 1, w) in rdt]
            m.Add(sum(rl) <= readers)
            for r in rl: m.AddImplication(r, o.Not())
    for (k, i, t, w), r in rdt.items():
        m.AddImplication(r, P(N[k][i], w, t))
        if dur[k] == 2:
            m.AddImplication(r, P(N[k][i], w, t + 1))
    # a c3x target is mid-gate during step t+1's CX phase: nothing touches it
    for (k, t, w), v in ft.items():
        if dur[k] == 2:
            for l in range(1, L + 1):
                m.AddImplication(v, xf[t + 1, l, w].Not())
                for s in range(NW):
                    if s != w:
                        m.AddImplication(v, cx[t + 1, l, s, w].Not())
                        m.AddImplication(v, cx[t + 1, l, w, s].Not())
    # step boundary: node bits appear on the target
    for t in range(T):
        for w in range(NW):
            for b in range(BITS):
                new, old = cl[t + 1][0][w][b], cl[t][L][w][b]
                if 12 <= b < 12 + NN:
                    k = b - 12
                    tf = t if dur[k] == 1 else t - 1
                    if (k, tf, w) in ft:
                        m.AddBoolXOr([old, ft[k, tf, w], new.Not()])
                        continue
                m.Add(new == old)
    # phase terms read the final snapshot
    pw = {}
    for p, term in enumerate(TERMS):
        for i, o in enumerate(term):
            for w in range(NW):
                pw[p, i, w] = B('pw_%d_%d_%d' % (p, i, w))
                m.AddImplication(pw[p, i, w], P(o, w, T))
            m.AddExactlyOne([pw[p, i, w] for w in range(NW)])
        for w in range(NW):
            m.Add(sum(pw[p, i, w] for i in range(len(term))) <= 1)
    if not feas:
        m.Minimize(sum(cx.values()))
    return m, dict(cl=cl, cx=cx, xf=xf, fire=fire, tgt=tgt, rd=rd, pw=pw, T=T, L=L, est=est, lst=lst)


def decode(sol, V):
    T, L = V['T'], V['L']
    body = []
    for t in range(T + 1):
        for l in range(1, L + 1):
            for (tt, ll, s, w), v in V['cx'].items():
                if tt == t and ll == l and sol.Value(v): body.append(('cx', s, w))
            for (tt, ll, w), v in V['xf'].items():
                if tt == t and ll == l and sol.Value(v): body.append(('x', w))
        if t == T: break
        for k in range(NN):
            if (k, t) in V['fire'] and sol.Value(V['fire'][k, t]):
                tw = [w for w in range(NW) if sol.Value(V['tgt'][k, w])][0]
                rs = [[w for w in range(NW) if sol.Value(V['rd'][k, i, w])][0] for i in range(len(N[k]))]
                body.append((('ccx' if len(rs) == 2 else 'c3x'),) + tuple(rs) + (tw,))
    ph = []
    for p, term in enumerate(TERMS):
        ws = [[w for w in range(NW) if sol.Value(V['pw'][p, i, w])][0] for i in range(len(term))]
        ph.append((('cz' if len(ws) == 2 else 'ccz'),) + tuple(ws))
    return body, ph


if __name__ == '__main__':
    T = int(sys.argv[1]); limit = float(sys.argv[2]) if len(sys.argv) > 2 else 600
    L = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 2
    t0 = time.time()
    feas = '--feas' in sys.argv
    center = None; slack = 0
    if '--cap' in sys.argv:
        cap = int(sys.argv[sys.argv.index('--cap') + 1])
        slack = int(sys.argv[sys.argv.index('--slack') + 1]) if '--slack' in sys.argv else 0
        center, Tls = list_schedule(cap)
        print('list schedule cap=%d -> T=%d ; per-step targets %s' % (cap, Tls,
              [sum(1 for k in range(NN) if center[k] == t) for t in range(Tls)]))
        T = max(T, Tls)
    r = build(T, L, feas=feas, center=center, slack=slack)
    if r is None:
        print('T=%d below the weighted chain' % T); sys.exit()
    m, V = r
    print('T=%d L=%d  built in %.0fs' % (T, L, time.time() - t0), flush=True)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = limit
    s.parameters.num_workers = 4
    s.parameters.log_search_progress = True
    st = s.Solve(m)
    print('status', s.StatusName(st), 'time %.0fs' % (time.time() - t0), flush=True)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        body, ph = decode(s, V)
        print('body ops %d (cx %d)  phase %s' % (len(body), sum(1 for o in body if o[0] == 'cx'), ph))
        pickle.dump((body, ph), open('cpfg_T%d_L%d.pkl' % (T, L), 'wb'))
