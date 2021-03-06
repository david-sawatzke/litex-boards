#!/usr/bin/env python3

# This file is Copyright (c) 2020 Paul Sajna <sajattack@gmail.com>
# License: BSD

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import de10nano

from litex.soc.cores.clock import CycloneVPLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import AS4C16M16
from litedram.phy import GENSDRPHY

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, with_sdram=False):
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        # # #

        # Clk / Rst
        clk50 = platform.request("clk50")
        platform.add_period_constraint(clk50, 1e9/50e6)

        # PLL
        self.submodules.pll = pll = CycloneVPLL(speedgrade="-I7")
        pll.register_clkin(clk50, 50e6)
        pll.create_clkout(self.cd_sys,    sys_clk_freq)
        pll.create_clkout(self.cd_sys_ps, sys_clk_freq, phase=90)

        # SDRAM
        if with_sdram:
            self.comb += platform.request("sdram_clock").eq(self.cd_sys_ps.clk)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(50e6), **kwargs):
        platform = de10nano.Platform()

        # SoCCore ---------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq, **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

# MiSTerSDRAMSoC -----------------------------------------------------------------------------------

class MiSTerSDRAMSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(50e6), **kwargs):
        platform = de10nano.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq, **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, with_sdram=True)

        # SDR SDRAM --------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"))
            self.add_sdram("sdram",
                phy                     = self.sdrphy,
                module                  = AS4C16M16(self.clk_freq, "1:1"),
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x40000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = True
            )

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on DE10 Nano")
    parser.add_argument("--with-mister-sdram", action="store_true",
                        help="enable MiSTer SDRAM expansion board")
    builder_args(parser)
    soc_sdram_args(parser)
    args = parser.parse_args()
    soc = None
    if args.with_mister_sdram:
        soc = MiSTerSDRAMSoC(**soc_sdram_argdict(args))
    else:
        soc = BaseSoC(**soc_sdram_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build()


if __name__ == "__main__":
    main()
