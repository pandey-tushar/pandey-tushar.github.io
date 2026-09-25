caterpillar driver (build against github.com/gmeuli/caterpillar @4c6f766 + pip z3-solver 5.1):
  g++ -std=c++17 -O2 -DUSE_Z3 -DFMT_HEADER_ONLY -I<cat>/include -I<cat>/lib/{mockturtle,tweedledum,kitty,lorina,fmt,sparsepp,percy,ez,bill,easy,json,rang,abcsat} -I<z3>/include catdrv.cpp -o catdrv -L<z3>/lib -lz3
logo_cubes.txt: exorcism ESOP of F, 59 cubes, char i = input i (verified == F).
Results (2026-09-25):
  XAG from ESOP (balanced trees): 291 gates, 233 AND, depth 10
  lowd (xag_low_depth, unbounded): 267 qubits, 1110 gates, netlist == F
  lowt (xag_mapping, unbounded):   246 qubits, 582 gates, netlist == F
  pebb 6 pebbles, 120 s search:    no strategy found (steps searched up to 253)
mockturtle (github lsils/mockturtle @d9e0249) MC optimizer mtopt.cpp: minmc cut rewriting (cut 6) + resubstitution_minmc_withDC + constant-fanin opt
  233 -> 218 -> 166 -> 159 -> 157 -> 156 ANDs (AND-depth 5), stops at 156; function == F checked each round -> logo_opt.v
caterpillar on logo_opt.v: lowt unbounded 169 qubits, 1081 gates, == F
  pebbling (qubit-limited): no strategy with 6 pebbles (300 s), nor 12 / 20 / 30 pebbles (120 s each)
  -> the pebbling compile does not scale to a 156-AND network; route closed
