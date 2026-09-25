// caterpillar driver: ESOP cubes of F -> XAG (balanced trees) -> quantum netlist
// usage: catdrv cubes.txt MODE PEBBLES TIMEOUT out.txt
//   MODE: lowd (xag_low_depth), lowt (xag_mapping), pebb (xag_pebbling, needs PEBBLES)
// out.txt: one gate per line: "<nctl> <c0> <p0> ... <target> <function-hex>"
//   (p = 1 if control complemented); header "qubits <n> inputs <i..> outputs <o..>"
#include <fstream>
#include <iostream>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/print.hpp>
#include <tweedledum/networks/netlist.hpp>
#define private public   // read stg_gate::_function (no accessor)
#include <caterpillar/structures/stg_gate.hpp>
#undef private
#include <caterpillar/synthesis/lhrs.hpp>
#include <caterpillar/synthesis/strategies/xag_mapping_strategy.hpp>
#include <caterpillar/structures/stg_gate.hpp>
#include <caterpillar/verification/circuit_to_logic_network.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <tweedledum/networks/netlist.hpp>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/print.hpp>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace caterpillar;
using namespace mockturtle;
using namespace tweedledum;
using sig = xag_network::signal;

sig tree(xag_network& x, std::vector<sig> v, bool isand)
{
  while (v.size() > 1) {
    std::vector<sig> w;
    for (size_t i = 0; i + 1 < v.size(); i += 2)
      w.push_back(isand ? x.create_and(v[i], v[i + 1]) : x.create_xor(v[i], v[i + 1]));
    if (v.size() % 2) w.push_back(v.back());
    v = w;
  }
  return v[0];
}

int main(int argc, char** argv)
{
  std::string mode = argv[2];
  uint32_t peb = std::stoi(argv[3]), tmo = std::stoi(argv[4]);
  std::ifstream in(argv[1]);
  xag_network x;
  std::vector<sig> pis;
  for (int i = 0; i < 12; ++i) pis.push_back(x.create_pi());
  std::vector<sig> terms;
  std::string line;
  while (std::getline(in, line)) {
    if (line.size() < 12) continue;
    std::vector<sig> lits;
    for (int i = 0; i < 12; ++i)
      if (line[i] != '-') lits.push_back(line[i] == '1' ? pis[i] : !pis[i]);
    terms.push_back(tree(x, lits, true));
  }
  x.create_po(tree(x, terms, false));
  x = cleanup_dangling(x);
  depth_view dv{x};
  uint32_t nand = 0;
  x.foreach_gate([&](auto n) { if (x.is_and(n)) ++nand; });
  std::cout << "[xag] gates " << x.num_gates() << " ands " << nand << " depth " << dv.depth() << std::endl;

  netlist<stg_gate> q;
  logic_network_synthesis_params ps;
  logic_network_synthesis_stats st;
  if (mode == "lowd") {
    xag_low_depth_mapping_strategy s;
    logic_network_synthesis(q, x, s, {}, ps, &st);
  } else if (mode == "lowt") {
    xag_mapping_strategy s;
    logic_network_synthesis(q, x, s, {}, ps, &st);
  } else {
    pebbling_mapping_strategy_params pp;
    pp.pebble_limit = peb;
    pp.search_timeout = tmo;
    pp.progress = true;
    pp.increment_pebbles_on_failure = false;
    xag_pebbling_mapping_strategy s(pp);
    logic_network_synthesis(q, x, s, {}, ps, &st);
  }
  std::cout << "[qnet] qubits " << q.num_qubits() << " gates " << q.num_gates() << std::endl;
  if (q.num_gates() == 0) { std::cout << "[fail] no circuit\n"; return 1; }
  // verify: netlist back to logic network, simulate
  auto tt_x = simulate<kitty::dynamic_truth_table>(x, {12});
  auto ntk = circuit_to_logic_network<xag_network, netlist<stg_gate>>(q, st.i_indexes, st.o_indexes);
  bool ok = ntk && simulate<kitty::dynamic_truth_table>(*ntk, {12}) == tt_x;
  std::cout << "[verify] netlist computes F: " << (ok ? "yes" : "NO") << std::endl;
  std::ofstream out(argv[5]);
  out << "qubits " << q.num_qubits() << " inputs";
  for (auto i : st.i_indexes) out << " " << i;
  out << " outputs";
  for (auto o : st.o_indexes) out << " " << o;
  out << "\n";
  q.foreach_cgate([&](auto const& n) {
    auto const& g = n.gate;
    std::vector<std::pair<uint32_t, bool>> cs;
    g.foreach_control([&](auto c) { cs.push_back({c.index(), c.is_complemented()}); });
    uint32_t t = 0;
    g.foreach_target([&](auto tq) { t = tq.index(); });
    out << cs.size();
    for (auto& c : cs) out << " " << c.first << " " << c.second;
    out << " " << t << " " << kitty::to_hex(g._function) << "\n";
  });
  return ok ? 0 : 2;
}
