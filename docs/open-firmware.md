# Open-firmware plan for the KOQIT V5H

This is an engineering assessment, not a promise that the hardware can be
fully opened. The V5H is a closed eCos box with a proprietary bootloader,
demodulator, VPU and front-panel MCU. The practical goal is to get a useful
open Linux system running, with a SAT>IP server as the first milestone and a
full UI later only if the VPU/OSD documentation permits it.

## v1 requirements (user constraint)

The first custom firmware must keep:

1. **HDMI control/output.** v1 cannot be a headless-only SAT>IP box. The
   kernel/driver stack must drive the V5H HDMI/VPU/OSD at least to a
   framebuffer console or minimal UI. This likely means keeping the vendor
   `av.ko`/framebuffer/HDMI driver or writing a replacement; the McMCCRU
   SAT>IP image is a starting point but is headless.
2. **A working flashing/update path.** v1 must remain updatable over USB
   without a serial cable. Keep the stock bootloader and a USB full-image
   writer/recovery path, or implement an updater in Linux plus a recovery
   partition. Do not ship a v1 that is unflashable.
3. **The stock BOOT/recovery path** until a replacement is proven. The
   `/recovery.rcv` path is currently unproven on the H.265 unit; do not flash
   v1 until a recovery path is verified.

These constraints also mean v1 should keep the stock partition layout or a
strictly verified replacement, and preserve the HDMI/OSD path while adding the
Linux DVB stack.

## Compatibility matrix

| Component | V5H | GX6605S reference | Gap |
| --- | --- | --- | --- |
| CPU | CK610 ABI v1 | CK610M ABI v1 | Same ISA family; same toolchain |
| DRAM | 128 MiB DDR3 | 64 MiB DDR2 (in-package) | New DDR3 init/training; new device-tree size |
| Flash | 8 MiB SPI NOR | 4 MiB SPI NOR | New partition sizes; same GxLoader TABLE concept |
| Boot ROM | Unknown Taurus variant | Documented GX6605S BootROM/UART protocol | Loader protocol likely compatible; verify baud/chip ID |
| Bootloader | Vendor GxLoader/U-Boot (Taurus) | Vendor GxLoader/U-Boot | No open Taurus stage-2; can keep stock BOOT |
| Demod | Integrated GXDemod S2 | Integrated GXDemod S2/S | Community `fe.ko` has GXDemod paths; verify profile |
| Tuner | RDA5815M | Board dependent | Community `fe.ko` already contains `rda5815m`/`rda581x` |
| Video decode | H.265/H.264 VPU | H.264/H.265 VPU | Vendor VPU/OSD stack, no mainline driver |
| Display | HDMI 1080p | HDMI framebuffer | HDMI/HDCP/OSD reverse engineering |
| Front panel | 7-seg + IR + 8051/LPC | 7-seg/GPIO | Panel MCU protocol and key map |
| Network | USB dongles | USB dongles | Kernel drivers exist; verify VID/PID and power |

## Route A: Linux on the stock bootloader (recommended first)

The vendor GxLoader can boot a Linux kernel from flash or USB. The community
`McMCCRU/gx6605s_linux_fw_build` project proves this on GX6605S: it builds a
uImage (`C lzma`, load/entry `0x90000000`), a squashfs root, a vendor
bootloader, and a `minifs` filler, then writes a 4 MiB full-flash image with
`genflash`. It already includes `minisatip` (SAT>IP), `fe.ko`, `av.ko`, Wi-Fi
drivers, and a 24 MHz/27 MHz variant.

What to reuse:

- the C-Sky GCC/binutils toolchain and Linux 4.9.y GX6605S port;
- the `gx6605s.dts` / `gx66xx_defconfig` as a starting board description;
- the `mkimage`/`genflash`/`gxdownloader` flow;
- the squashfs rootfs and `minisatip` userland;
- the 4 MiB flash layout as a template, resized to 8 MiB.

What must change:

1. **DDR3 / 128 MiB.** The stock V5H stage-2 already initializes the DDR3.
   The lowest-risk approach is to keep the stock BOOT partition and let it load
   a Linux kernel. A fully open boot chain needs a Taurus DDR3 initializer,
   which does not exist publicly yet.
2. **Memory node.** Device tree memory becomes
   `reg = <0x10000000 0x08000000>` if Linux is entered with all 128 MiB mapped.
   Verify the stock stage-2 maps the full 128 MiB at `0x10000000`.
3. **Flash layout.** The TABLE must describe an 8 MiB image with BOOT/TABLE/
   KERNEL/ROOT/DATA/AD partitions. Either keep the stock layout and place the
   kernel in KERNEL, or rebuild the table and update its CRCs.
4. **RDA5815M + GXDemod.** The community GX6605S `fe.ko` already contains
   `rda5815m`, `rda581x_rda5815m_init`, and GXDemod paths. It is configured
   through the `profile` module parameter (tuner/demod type, I2C id, chip
   addresses). This is a much better starting point than a clean-room driver,
   but the V5H's I2C address, LNB supply and demod variant still need to be
   verified against the stock eCos frontend.
5. **Front panel / IR.** The stock eCos drives the panel through the 8051/LPC
   core. Linux must either start that core with the vendor `gxlowpower.fw` or
   bit-bang the panel protocol from the main CPU.
6. **VPU/OSD/HDMI.** For a SAT>IP server these are not needed. For a UI they
   are mandatory. Plan for a framebuffer-only console first, then evaluate the
   vendor VPU/OSD modules.

Boot strategy:

- Deploy over USB first: use the stock app's USB Dump/Upgrade or the bootloader
  `/recovery.rcv` path. Keep a self-dumped full image as the restore file.
- Start with a USB-bootable test kernel on the public GX6605S dev board if one
  is available (cheap and recoverable). Confirm the toolchain and rootfs.
- On the V5H, dump the stock flash, keep BOOT intact, and write only the
  KERNEL/ROOT/DATA areas. `tools/v5h_image.py` rebuilds the TABLE CRCs.
- If Linux cannot be booted by the stock stage-2, fall back to Route B.

## Route B: Replace the boot chain

`gxipl` provides an open CK610 stage-1/stage-2 for GX6702/GX6706 but not
Taurus. A Taurus port needs:

- the DDR3 controller profile (registers `0x00c00000` range, PHY training,
  eFuse trims);
- PLL/clock/UART initialization for the V5H board;
- SPI NOR and USB boot paths;
- a device tree and kernel command line for the V5H.

This is the clean long-term solution, but it is also the highest-risk path.
Capture a boot log and use the emulator/disassembler before writing a custom
stage-1.

## Route C: Keep eCos, replace the application

The eCos kernel and C-SKY port are open source, but the NationalChip BSP,
demod, VPU, panel and crypto drivers are not. Replacing only the application
still requires all those drivers, so this is not easier than Linux unless the
goal is a tiny custom appliance on the existing stack.

## Milestones

### M0 - preserve the device

- Dump the full 8 MiB flash over UART (`serialdump`).
- Verify the SHA-256 against `firmware/V5H-Intelsat_263_flash.bin`.
- Take a second dump with a SPI clip if possible.
- Record the boot banner (chip model, board type, flash JEDEC, memory size,
  CPU/memory frequency) and the UART baud.
- Do not touch OTP.

### M1 - reproduce the analysis

- Run `python3 tools/v5h_extract.py ...`.
- Build the C-SKY toolchain and disassemble the eCos and BOOT stage-2.
- Use `gx6605s-emu` to trace the stock boot to the point where it fails on the
  V5H image; map the first unimplemented peripheral.
- Identify the RDA5815M I2C address and the GXDemod register window from the
  eCos frontend code.

### M2 - Linux proof of concept

- Build the C-Sky 4.9.y kernel with `gx66xx_defconfig` and `gx6605s.dts`.
- Boot it on the GX6605S dev board or a compatible GX6605S receiver.
- Add a minimal initramfs and framebuffer console.
- Confirm UART, timer, GPIO, USB, and SPI.

### M3 - V5H bring-up

- Boot the same kernel on V5H with the stock BOOT and a V5H-specific DTS.
- Correct the memory size and DDR3 mapping.
- Get UART, timer, USB, and flash working.
- Add the RDA5815M tuner and GXDemod frontend, then `minisatip`.
- Add the front panel and IR.
- Only then consider a UI.

### M4 - packaging and recovery

- Build an 8 MiB full-flash image with a correct TABLE and CRCs.
- Test the update path on a sacrificial unit or with a guaranteed SPI-clip
  recovery.
- Document the exact recovery procedure.

## Test strategy

1. **Host-side extraction tests.** `tools/v5h_extract.py` must reproduce the
   known hashes for the stock image.
2. **Emulator smoke tests.** Boot the image and custom kernels in
   `gx6605s-emu`; treat OSD/video results as indicative, not proof.
3. **Bench tests.** UART console, then SPI flash read/write, then USB, then
   tuner I2C, then demod, then video.
4. **Never flash a new image without a self-dumped backup and a proven
   recovery path** (USB `/recovery.rcv` or hardware).

## Risks

- **DDR3 training** is the top blocker for an open boot chain.
- **Tuner/demod work** is lower risk than first thought: `fe.ko` already has
  RDA5815M and GXDemod code. The remaining work is profile/I2C/board
  verification.
- **VPU/OSD/HDMI** is the top blocker for a polished UI.
- **Update acceptance** may check more than CRC32; a valid-looking image may be
  rejected or, worse, partially written.
- **OTP/eFuse writes are irreversible.** Avoid them.
- **Proprietary blobs** cannot be redistributed; keep the vendor firmware and
  loader local.

## Realistic outcome

- A **SAT>IP server / headless Linux receiver** is plausible with the GX6605S
  Linux port plus RDA5815M profile/board work.
- A **full open living-room UI with hardware H.265 decode** is a much larger
  reverse-engineering effort and may never be fully open.
- A **fully open boot chain** requires a Taurus DDR3 initializer and is a
  separate project.

## Reference projects to study first

- `c-sky/linux-4.9.y` - GX6605S DTS and defconfig.
- `c-sky/tools/gx6605s` - CK610 spec, boot.elf, generic loader.
- `linux-goxceed/gxipl` - open CK610 IPL and flash/TABLE code.
- `linux-goxceed/gxdl-c`, `gxdl-rs`, `matu6968/libre-gxdl` - bootrom protocol
  and flashing.
- `McMCCRU/gx6605s_linux_fw_build` - proven GX6605S Linux/SAT>IP image.
- `RalphTamer/gx6605s-emu` - C-SKY interpreter and peripheral models.
- `GX-OSS/xboot-gx6605s` - MIT GX6605S register definitions.
- `c-sky/addons-linux` - vendor framebuffer/VPU driver examples.
- `KR0SIV/KOQIT-GX6605S-Digital-ATV-Firmware` - example of repacking a KOQIT
  GX6605S image.
