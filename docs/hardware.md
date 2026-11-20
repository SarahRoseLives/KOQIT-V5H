# KOQIT V5H hardware notes

## Identity

The stock eCos binary contains both `GX6605H1` and the string
`taurus unsupport use dmxid %d filter section`, which ties the board to
NationalChip's **Taurus / GX6605H1** family. The vendor flasher package also
ships `taurus-6605H1-sflash.boot`, matching the firmware header. This is *not*
plain GX6605S: it is a related but distinct member of the GX6605 family.

## CPU / SoC

| Property | Value | Source |
| --- | --- | --- |
| ISA | C-SKY ABI v1, CK610 core | eCos `csky-ecos`; C-Sky docs; `gxipl` |
| MMU | Yes, CK610 CP15-style | C-Sky GX6605S docs; `gxipl` |
| I-cache / D-cache | 16 KiB / 16 KiB (GX6605S dev board) | C-Sky GX6605S docs |
| Clock | ~594-672 MHz class (board dependent) | C-Sky loader banners; `gxipl` notes |
| DRAM | 128 MiB DDR3 on V5H | Jungle-Team review |
| SPI NOR | 8 MiB | image size; V5H repair page |
| Package/board | metal case, 150 x 80 x 40 mm class | review |

The public GX6605S dev board has **64 MiB DDR2 integrated in the SoC** and a
4 MiB flash. The V5H uses external **DDR3**, so the public DDR2 initialization
cannot be used unchanged.

## Peripherals seen in the vendor kernel/device tree (GX6605S baseline)

These are the documented GX6605S addresses. They are a starting point for the
V5H, not a confirmed V5H map.

| Block | Address | Notes |
| --- | ---: | --- |
| Interrupt controller | `0x00500000` | `nationalchip,intc-v1,ave` |
| Timer 0 | `0x0020a000` | `nationalchip,timer-v1`, 1 MHz, IRQ 10 |
| EHCI | `0x00900000` | IRQ 59 |
| OHCI 0 | `0x00a00000` | IRQ 58 |
| OHCI 1 | `0x00b00000` | IRQ 57 |
| UART (Linux DTS) | `0x00403000` | ns16550a, 29.4912 MHz, 115200 |
| Native GX UART | `0x00400000` | observed by the emulator/boot code |
| GPIO | `0x00305000` | direction/data/set/clear |
| System/clock control | `0x0030a000` | PLL, gates, DDR PHY |
| Clock routes | `0x00601000` | per-domain dividers |
| DDR controller | `0x00c00000` | controller/training |
| eFuse command/status | `0x00f80080` / `0x00f80088` | DDR trim / OTP |

The eCos binary exposes a `/dev/gx*` device model rather than Linux device
nodes: `gxav`, `gxcrypto`, `gxfe`, `gxgpio`, `gxirr`, `gxklm`, `gxlowpower`,
`gxmisc`, `gx_otp`, `gxpanel`, and `gxfirewall`.

## Tuner and demodulator

- Tuner: **RDA5815M** (string next to the frontend names in eCos).
- Demod: the integrated **`Nationalchip GXDemod S2`**. Other builds of the same
  eCos app list `M3031`, `TS6011`, `ATBM253_DVBT`, and `ATBM2040_DVBT`, so the
  binary carries multiple frontend options.
- Supported: DVB-S/S2, multistream/T2-MI, low symbol rates (review), DiSEqC
  1.0/1.1/1.2, 22 kHz, Unicable.
- The RDA5815M is an I2C tuner; the GXDemod is memory-mapped inside the SoC.
  No mainline Linux driver exists for this exact pair, so a port or a new
  driver is required for a Linux firmware.

## Front panel, IR, HDMI

- 7-segment front panel and buttons; IR receiver.
- eCos loads `gxlowpower.fw` into the standby 8051/LPC core for the panel on
  related GX6605S boards. The open GX6706 IPL notes document a TM1650/FD650
  two-wire panel protocol on 8051 pins P1.5/P1.6. Expect similar work on V5H.
- HDMI 2.0a with HDCP 2.2, up to 1080p output. H.265/H.264 decode is handled by
  the SoC VPU, not the CPU.

## Network

No RJ45 and no onboard Wi-Fi. The eCos app supports USB dongles and lists
`MT7601+RT5370+RTL8188FU` Wi-Fi and `SR9900` USB Ethernet. Any open firmware
must supply those drivers, or use a supported USB Ethernet adapter.

## Unknowns that matter for a port

1. Exact DDR3 part, topology, and training values.
2. Whether the V5H BootROM/stage-2 enforces image signatures beyond CRC32.
3. RDA5815M I2C address, clock/data pins, and LNB supply control.
4. GXDemod S2 register map and firmware-loading protocol.
5. VPU/OSD/HDMI register map and firmware blobs.
6. Front-panel MCU protocol and key map.
7. OTP contents and whether any keys are required for update acceptance.

## References

- <https://c-sky.github.io/docs/gx6605s.html>
- <https://github.com/c-sky/linux-4.9.y/blob/master/arch/csky/boot/dts/gx6605s.dts>
- <https://github.com/c-sky/linux-4.9.y/blob/master/arch/csky/configs/gx66xx_defconfig>
- <https://github.com/c-sky/tools/tree/master/gx6605s> (CK610 spec, PCB, boot tools)
- <https://github.com/linux-goxceed/gxipl> (CK610 boot/IPL notes)
- <https://github.com/RalphTamer/gx6605s-emu> (peripheral/register observations)
- <https://jungle-team.com/review-koqit-v5h/> (teardown/review)
