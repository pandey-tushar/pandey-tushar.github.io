// AND-depth / AND-count Pareto explorer for F's XAG.
// usage: mtdepth in.v outprefix ROUNDS SEED
// loop: algebraic AND-depth rewriting (depth counted with mc_cost: XOR 0, AND 1),
//       MC cut rewriting preserving AND-depth, MC resub, constant-fanin opt.
// writes outprefix_d<depth>.v for every new Pareto point; verifies function each round.
#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp>
#include <mockturtle/algorithms/xag_optimization.hpp>
#include <mockturtle/algorithms/xag_algebraic_rewriting.hpp>
#include <mockturtle/algorithms/xag_resub_withDC.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/io/write_verilog.hpp>
#include <mockturtle/io/verilog_reader.hpp>
#include <lorina/verilog.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <mockturtle/views/fanout_view.hpp>
#include <mockturtle/utils/cost_functions.hpp>
#include <kitty/dynamic_truth_table.hpp>
#include <chrono>
#include <iostream>
#include <map>
#include <string>
using namespace mockturtle;
uint32_t nands(xag_network const& x){uint32_t c=0;x.foreach_gate([&](auto n){if(x.is_and(n))++c;});return c;}
uint32_t adepth(xag_network const& x){depth_view<xag_network,mc_cost<xag_network>> d{x};return d.depth();}
int main(int argc,char**argv){
  xag_network x;
  if(lorina::read_verilog(argv[1],verilog_reader(x))!=lorina::return_code::success){std::cout<<"read fail\n";return 1;}
  std::string pre=argv[2]; int rounds=std::stoi(argv[3]);
  auto tt0=simulate<kitty::dynamic_truth_table>(x,default_simulator<kitty::dynamic_truth_table>(12));
  std::map<uint32_t,uint32_t> pareto; // depth -> ands
  auto t0=std::chrono::steady_clock::now();
  auto rep=[&](const char*tag){
    auto tt=simulate<kitty::dynamic_truth_table>(x,default_simulator<kitty::dynamic_truth_table>(12));
    if(tt!=tt0){std::cout<<"[error] function changed at "<<tag<<"\n";exit(2);}
    uint32_t a=nands(x),d=adepth(x);
    double el=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
    bool nw=true; for(auto&kv:pareto) if(kv.first<=d&&kv.second<=a) nw=false;
    std::cout<<tag<<"  ANDs "<<a<<"  AND-depth "<<d<<"  gates "<<x.num_gates()<<"  "<<el<<"s"<<(nw?"  [pareto]":"")<<std::endl;
    if(nw){pareto[d]=a; write_verilog(x,pre+"_d"+std::to_string(d)+".v");}
  };
  rep("[start]");
  future::xag_minmc_resynthesis resyn;
  for(int r=0;r<rounds;++r){
    { depth_view<xag_network,mc_cost<xag_network>> dx{x};
      xag_algebraic_depth_rewriting_params ps; ps.strategy=(r%2)?xag_algebraic_depth_rewriting_params::aggressive:xag_algebraic_depth_rewriting_params::dfs;
      ps.allow_rare_rules=true;
      xag_algebraic_depth_rewriting(dx,ps); }
    x=cleanup_dangling(x); rep("  [depth-rw]");
    for(int k=0;k<3;++k){
      { cut_rewriting_params cps; cps.cut_enumeration_ps.cut_size=6;
        cut_rewriting_with_compatibility_graph(x,resyn,cps,nullptr,mc_cost<xag_network>()); x=cleanup_dangling(x); }
      x=xag_constant_fanin_optimization(x); x=cleanup_dangling(x);
    }
    rep("  [mc-rw]");
    std::cout<<"[round "<<r+1<<"] pareto:"; for(auto&kv:pareto) std::cout<<" d"<<kv.first<<":"<<kv.second; std::cout<<std::endl;
  }
  return 0;
}
