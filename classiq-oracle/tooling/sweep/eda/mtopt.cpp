// mockturtle MC optimizer: ESOP cubes of F -> XAG -> repeat {minmc cut rewriting,
// MC resubstitution with don't cares, constant-fanin opt} until no gain.
// usage: mtopt cubes.txt out.v ROUNDS
// prints per round: gates, ANDs (multiplicative complexity), AND-depth; writes verilog.
#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp>
#include <mockturtle/algorithms/xag_optimization.hpp>
#include <mockturtle/algorithms/xag_resub_withDC.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/io/write_verilog.hpp>
#include <mockturtle/io/verilog_reader.hpp>
#include <lorina/verilog.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <mockturtle/views/fanout_view.hpp>
#include <mockturtle/properties/mccost.hpp>
#include <mockturtle/utils/cost_functions.hpp>
#include <kitty/dynamic_truth_table.hpp>
#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace mockturtle;
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

uint32_t and_depth(xag_network const& x)
{
  std::vector<uint32_t> d(x.size(), 0);
  uint32_t best = 0;
  x.foreach_gate([&](auto n) {
    uint32_t m = 0;
    x.foreach_fanin(n, [&](auto f) { m = std::max(m, d[x.get_node(f)]); });
    d[n] = m + (x.is_and(n) ? 1 : 0);
  });
  x.foreach_po([&](auto f) { best = std::max(best, d[x.get_node(f)]); });
  return best;
}

uint32_t nands(xag_network const& x)
{
  uint32_t c = 0;
  x.foreach_gate([&](auto n) { if (x.is_and(n)) ++c; });
  return c;
}

int main(int argc, char** argv)
{
  std::ifstream in(argv[1]);
  int rounds = std::stoi(argv[3]);
  xag_network x;
  std::string fn = argv[1];
  bool isv = fn.size() > 2 && fn.substr(fn.size() - 2) == ".v";
  if (isv) {
    if (lorina::read_verilog(fn, verilog_reader(x)) != lorina::return_code::success) { std::cout << "[fail] verilog read\n"; return 1; }
  } else {
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
  }
  x = cleanup_dangling(x);
  auto tt0 = simulate<kitty::dynamic_truth_table>(x, default_simulator<kitty::dynamic_truth_table>(12));
  auto t0 = std::chrono::steady_clock::now();
  auto report = [&](const char* tag) {
    auto el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::cout << tag << "  gates " << x.num_gates() << "  ANDs " << nands(x) << "  AND-depth " << and_depth(x)
              << "  " << el << "s" << std::endl;
  };
  report("[start]");
  future::xag_minmc_resynthesis resyn;
  uint32_t best = nands(x);
  for (int r = 0; r < rounds; ++r) {
    cut_rewriting_params cps;
    cps.cut_enumeration_ps.cut_size = 6;
    cut_rewriting_with_compatibility_graph(x, resyn, cps, nullptr, mc_cost<xag_network>());
    x = cleanup_dangling(x);
    report("  [cut-rewrite]");
    resubstitution_params rps;
    rps.max_inserts = 20;
    rps.max_pis = 12;
    {
      fanout_view<xag_network> fx{x};
      depth_view<fanout_view<xag_network>> dx{fx};
      resubstitution_minmc_withDC(dx, rps);
    }
    x = cleanup_dangling(x);
    report("  [resub-DC]");
    x = xag_constant_fanin_optimization(x);
    x = cleanup_dangling(x);
    std::string tag = "[round " + std::to_string(r + 1) + "]";
    report(tag.c_str());
    auto tt = simulate<kitty::dynamic_truth_table>(x, default_simulator<kitty::dynamic_truth_table>(12));
    if (tt != tt0) { std::cout << "[error] function changed\n"; return 2; }
    uint32_t a = nands(x);
    if (a < best) {
      best = a;
      write_verilog(x, argv[2]);
      std::cout << "  saved " << argv[2] << std::endl;
    } else if (r > 0) break;
  }
  std::cout << "[final] ANDs " << best << "  function == F: yes" << std::endl;
  return 0;
}
