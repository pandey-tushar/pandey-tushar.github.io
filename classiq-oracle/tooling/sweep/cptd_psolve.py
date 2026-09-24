"""SAT solve with live progress: CaDiCaL in conflict-budget chunks (learnt
clauses are kept between chunks).  After every chunk one log line and a JSON
progress checkpoint (elapsed, conflicts, decisions, restarts, rates).
A true resume is not possible (the solver state cannot be saved); the
checkpoint shows the run is alive and moving.
solve(cl, tag, ckpt_path) -> model list | None"""
import os, sys, json, time
from pysat.solvers import Cadical153

CHUNK0 = int(os.environ.get('PCHUNK', '20000'))     # first chunk (conflicts)
EVERY = float(os.environ.get('PEVERY', '300'))       # target seconds per log line


def solve(cl, tag, ckpt_path):
    s = Cadical153(bootstrap_with=cl)
    t0 = time.time(); chunk = CHUNK0; last = t0; n = 0
    while True:
        s.conf_budget(chunk)
        r = s.solve_limited()
        now = time.time(); st = s.accum_stats(); n += 1
        rec = dict(tag=tag, status='running' if r is None else ('SAT' if r else 'UNSAT'),
                   elapsed_s=round(now - t0), chunks=n, conflicts=st.get('conflicts'),
                   decisions=st.get('decisions'), restarts=st.get('restarts'),
                   propagations=st.get('propagations'),
                   conf_per_s=round(st.get('conflicts', 0) / max(now - t0, 1e-9)),
                   utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
        tmp = ckpt_path + '.tmp'
        json.dump(rec, open(tmp, 'w'), indent=1); os.replace(tmp, ckpt_path)
        print('[%s] %s  %6ds  conflicts %s  restarts %s  %s conf/s' %
              (rec['utc'], tag, rec['elapsed_s'], rec['conflicts'], rec['restarts'], rec['conf_per_s']), flush=True)
        if r is not None:
            return s.get_model() if r else None
        dt = now - last; last = now          # retune chunk toward EVERY seconds per line
        if dt > 0: chunk = max(1000, min(int(chunk * EVERY / dt), 50_000_000))
