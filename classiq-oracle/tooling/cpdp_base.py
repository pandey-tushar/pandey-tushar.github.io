"""CP-DP step 1: reproduce the shipped baseline, per-block census."""
import time
import cpdp_lib as L
import cpae_core as AE

t0 = time.time()
ops, qcs = L.blocks_ops()
print("== per-block ==")
tot = 0
for nm in L.ORDER:
    o = ops[nm]
    d, c = L.depth_cx(o)
    tot += d
    t = L.touches(o)
    L.verify(o, nm, tag=nm)
    print("  %-4s depth %3d cx %4d ops %4d  touches %s"
          % (nm, d, c, len(o), " ".join("%d" % v for v in t)))
    cnt = {}
    for op in o:
        cnt[op[0]] = cnt.get(op[0], 0) + 1
    print("       gates %s" % cnt)
print("  serial ledger sum = %d" % tot)

ser = []
for nm in L.ORDER:
    ser += ops[nm]
d, c = L.depth_cx(ser)
print("== concatenated %s: depth %d cx %d ops %d" % (",".join(L.ORDER), d, c, len(ser)))
L.verify(ser, "LOGO", tag="serial LOGO")
e, lk = AE.sv_check(AE.ops_to_qc(ser, 18), "LOGO")
print("  sv_check err %.3e leak %.1e" % (e, lk))
lay = L.asap_layers(ser)
print("  model per-wire end layers: %s  (max %d)" % (lay, max(lay)))
print("[%.0fs]" % (time.time() - t0))
