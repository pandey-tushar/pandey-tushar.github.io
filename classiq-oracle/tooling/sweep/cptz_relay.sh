#!/bin/bash
# When a 4 h cptz_sa2 run ends by time, continue it from its checkpoint with no time limit
# (cyclic temperature, 30 min cycles, restart from best each cycle); stops only on exact.
cd "$(dirname "$0")"
relay() {
  L=$1; R=$2; S=$3; log=ckpt/evo_logs/sa2_L${L}_R${R}_s${S}.log
  until grep -qE "EXACT|final" $log; do sleep 30; done
  grep -q EXACT $log && exit 0
  INIT=ckpt/sa2_L${L}_R${R}_s${S}.pkl CYCLE=30 T0=3 python3 cptz_sa2.py $L $R $S 0 > ckpt/evo_logs/sa2_L${L}_R${R}_s${S}_cont.log 2>&1
}
relay 6 24 1 & relay 6 24 2 & relay 7 30 3 & relay 8 36 4 & wait
