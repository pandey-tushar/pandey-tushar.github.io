"""cpfl: phase-tracking pass (pyzx phase-polynomial / TODD) on a u3+cx circuit.
Usage: python3 cpfl_zx.py <qasm> [mode]   mode in {basic, phase, full}"""
import sys, math, numpy as np
sys.path.insert(0,'/home/user/classiq-challenge')
import pyzx as zx
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

def qk_to_zx(t):
    n=t.num_qubits; c=zx.Circuit(n)
    for inst in t.data:
        qs=[t.find_bit(q).index for q in inst.qubits]; nm=inst.operation.name
        if nm=='cx': c.add_gate('CNOT',qs[0],qs[1])
        elif nm in('u3','u'):
            th,ph,la=[float(p) for p in inst.operation.params]
            # u3(th,ph,la) = Rz(ph) Ry(th) Rz(la) up to global phase; Ry(th)=Rz(-pi/2)Rx(th)Rz(pi/2)
            # Rx(th)=H Rz(th) H
            def rz(a):
                a=a%(2*math.pi)
                if abs(a)<1e-9 or abs(a-2*math.pi)<1e-9: return
                k=a/(math.pi/4)
                assert abs(k-round(k))<1e-6, ('non-T angle',a)
                from fractions import Fraction
                c.add_gate('ZPhase',qs[0],Fraction(int(round(k)),4))
            rz(la); 
            if abs(th)>1e-9:
                rz(-math.pi/2); c.add_gate('HAD',qs[0]); rz(th); c.add_gate('HAD',qs[0]); rz(math.pi/2)
            rz(ph)
        else: raise ValueError(nm)
    return c

def zx_to_qk(c,n):
    q=QuantumCircuit(n)
    for g in c.gates:
        nm=g.name
        if nm=='CNOT': q.cx(g.control,g.target)
        elif nm=='HAD': q.h(g.target)
        elif nm in('ZPhase','Z','S','T'):
            ph=float(g.phase)*math.pi if hasattr(g,'phase') else {'Z':math.pi,'S':math.pi/2,'T':math.pi/4}[nm]
            if getattr(g,'adjoint',False): ph=-ph
            q.rz(ph,g.target)
        elif nm in('XPhase','NOT'):
            ph=float(g.phase)*math.pi if hasattr(g,'phase') else math.pi
            q.rx(ph,g.target)
        elif nm=='CZ': q.cz(g.control,g.target)
        elif nm=='S': q.s(g.target)
        else: raise ValueError(nm)
    return q

def run(qc, mode='full', verbose=True):
    t=transpile(qc,basis_gates=['u3','cx'],optimization_level=2)
    d0=t.depth(); c0=t.count_ops().get('cx',0)
    c=qk_to_zx(t)
    if mode=='none': c2=c
    elif mode=='basic': c2=zx.optimize.basic_optimization(c.to_basic_gates())
    elif mode=='phase': c2=zx.optimize.phase_block_optimize(c.to_basic_gates())
    else: c2=zx.optimize.full_optimize(c.to_basic_gates())
    q2=zx_to_qk(c2.to_basic_gates(),qc.num_qubits)
    t2=transpile(q2,basis_gates=['u3','cx'],optimization_level=2)
    if verbose: print(mode,'before',d0,c0,'after',t2.depth(),t2.count_ops().get('cx',0),'tcount',zx.tcount(c),'->',zx.tcount(c2),flush=True)
    return t,t2

if __name__=='__main__':
    qc=QuantumCircuit.from_qasm_file(sys.argv[1]); mode=sys.argv[2] if len(sys.argv)>2 else 'full'
    t,t2=run(qc,mode)
    if qc.num_qubits<=10:
        U=Operator(t).data; V=Operator(t2).data
        k=np.argmax(np.abs(U.flatten())); ph=V.flatten()[k]/U.flatten()[k]
        print('unitary err',np.abs(V-ph*U).max())
    out=sys.argv[1].replace('.qasm','_zx_%s.qasm'%mode)
    from qiskit.qasm2 import dumps
    open(out,'w').write(dumps(t2)); print('wrote',out)
