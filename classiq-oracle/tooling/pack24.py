"""Package cpev_best.qasm (249 / 520) as submission24.qasm + submission24.qmod.
qmod written in the same literal-statement format as submission22.qmod."""
import re, shutil, sys
import qmod_build12 as qb
SRC = "cpev_best.qasm"
ops = qb.ops_from_qasm(SRC)
lines = ["qfunc main(output q: qbit[18]) {", "  allocate(q);"]
for op in ops:
    if op[0] == "c":
        lines.append(f"  CX(q[{op[1]}], q[{op[2]}]);")
    elif op[0] == "u":
        t, p, l = [repr(float(v)) for v in op[2:5]]
        lines.append(f"  U({t}, {p}, {l}, 0.0, q[{op[1]}]);")
    else:
        sys.exit(f"unexpected gate {op}")
lines.append("}")
open("submission24.qmod", "w").write("\n".join(lines) + "\n")
shutil.copy(SRC, "submission24.qasm")
back = qb.ops_from_qmod("submission24.qmod")
print("qmod round-trip identical:", back == ops, "| ops", len(ops))
src = open("submission24.qasm").read()
print("notebook format check:", qb.notebook_metrics(src))
print("ascii:", all(ord(c) < 128 for c in src + open("submission24.qmod").read()))
