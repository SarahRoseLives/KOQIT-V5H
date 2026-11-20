# KOQIT V5H reverse engineering and open-firmware research

**Status: paused at a dead end (2026-11-20).** This repository documents the
research and tooling, not a working custom firmware. The stock app accepts
LOGO-only USB upgrades but rejects KERNEL changes (content/signature
validation). The H.265 bootloader's `/recovery.rcv` path did not consume our raw
images while the KERNEL was valid. Without RS232 or SPI hardware, no reliable
recovery writer was proven. See `docs/usb-only.md` and `backups/README.md`.
Vendor firmware, bootloaders, and dumps are deliberately not redistributed.

## Current status

- Device: KOQIT V5H H.265 (eCos build 2024-11-21), currently restored to stock.
- App-level USB upgrade/restore: **works** for LOGO-only images and full stock
  dumps.
- App-level USB upgrade: **rejects** KERNEL content, KERNEL CRC, `used_size`,
  and `start` changes. The app validates the KERNEL against the stock layout.
- Bootloader `/recovery.rcv`: **unproven**; raw `0x7F0000` and 8 MiB images were
  ignored while the KERNEL was valid.
- v1 requirement (HDMI/OSD control + a working USB flashing path): **not
  achieved**.
- Remaining paths: find the bootloader recovery trigger/container, use the IR
  micro-USB port in USB-device mode, obtain the vendor H.265 `recovery.rcv`, or
  reverse the app's update validation. A CH341A/SPI clip or UART adapter would
  remove the risk.

## Short version

- The V5H is a **NationalChip GX6605H1 ("Taurus")** DVB-S/S2 receiver.
- CPU: **C-SKY CK610 / ABI v1**, 32-bit, MMU; the same CPU core family as the
  public GX6605S development board.
- Memory: **128 MiB DDR3**, **8 MiB SPI NOR** flash.
- Tuner: **RDA5815M**; demodulator is the integrated **"Nationalchip GXDemod S2"**.
- Stock OS: **eCos RTOS**, not Linux. The UI/app is a 6.5 MiB eCos binary stored
  LZMA-compressed inside a ROMFS in the KERNEL partition.
- The complete 8 MiB flash image is downloadable from Koqit; it is **not**
  redistributed here. The tools expect a local copy at `firmware/` and
  extracted artifacts under `extracted/`.
- The most practical open-firmware route is the vendor-published **C-Sky Linux
  port for GX6605S** plus a community GX6605S SAT>IP firmware builder, adapted
  to the V5H's DDR3/128 MiB and 8 MiB layout. Its `fe.ko` already supports the
  RDA5815M tuner and GXDemod. The main remaining blockers are DDR3/memory
  adaptation, the 8 MiB flash layout, and VPU/OSD/HDMI for a full UI.
- USB-only development is possible: the stock app can dump/upgrade over USB and
  the bootloader looks for `/recovery.rcv`. See `docs/usb-only.md`.

## Hardware

| Item | Value | Evidence |
| --- | --- | --- |
| SoC | NationalChip GX6605H1 ("Taurus") | `GX6605H1` and `taurus` strings in the eCos binary; C-Sky boot header family `taurus-6605H1` |
| CPU | C-SKY CK610, ABI v1, MMU, 16 KiB I/D cache | C-Sky GX6605S dev-board documentation; `csky-ecos` string |
| DRAM | 128 MiB DDR3 | Jungle-Team V5H review |
| Flash | 8 MiB SPI NOR | 8,388,608-byte full image; repair/review data |
| Tuner | RDA5815M | `rda5815m` string next to the frontend device table |
| Demod | Integrated NationalChip GXDemod S2; other builds list M3031/TS6011/ATBM | strings in eCos |
| Video | DVB-S/S2, T2-MI, H.265/HEVC and H.264, 1080p | vendor copy and review |
| Outputs | HDMI 2.0a/HDCP 2.2, SPDIF, CVBS/RC, RS232, 2x USB 2.0 | review and product data |
| Network | None onboard; USB Ethernet/Wi-Fi dongles (MT7601, RT5370, RTL8188FU, SR9900) | eCos strings |
| Front panel | 7-segment LCD, IR receiver, buttons | review; eCos `gxpanel`/`gxirr` devices |

The public **GX6605S** dev board is the closest documented platform, but it is
not identical: it has 64 MiB DDR2 and a 4 MiB flash. Do not assume the V5H's
DDR3 initialization or board wiring is covered by the GX6605S device tree.

## What is in this repository

| Path | Contents |
| --- | --- |
| `README.md`, `docs/` | Hardware, firmware format, USB workflow, open-firmware plan, sources |
| `tools/` | Original extraction and image-rebuild scripts |
| `Screenshots/` | Test screenshots from the actual unit |
| `backups/README.md` | Device dump metadata and USB test log (no dump binaries) |
| `research/README.md` | Provenance and links to third-party research (not vendored) |
| `LICENSE`, `NOTICE` | License for original content and third-party disclaimer |

### Local-only artifacts (not in this repository)

| Path | Contents |
| --- | --- |
| `firmware/` | Official firmware and vendor tools; download from Koqit |
| `extracted/`, `extracted-h265/` | Unpacked firmware/dump components |
| `backups/*.bin` | Full flash dumps; keep local |
| `out/` | Generated test/recovery images |
| `research/<projects>/` | Third-party source snapshots; fetch from upstream |

### Downloaded firmware

| Field | Value |
| --- | --- |
| URL | `https://koqit.com/STB/upnet/V5H/V5H-Intelsat_263_flash.bin` |
| Size | 8,388,608 bytes (0x800000) |
| SHA-256 | `15fcc1ce5502304c2f939ec34bc49024a8f1b30f4e86e053495c921848a6f884` |
| Build time (in app) | 2026-01-09 15:00:07 |
| Brand | `V5H Intelsat` |

The actual receiver dump is a **different variant**: `backups/dump_all.bin` is
the `V5H H.265` build from 2024-11-21, with KERNEL `0x2C0000` and ROOT at
`0x330000`. See `backups/README.md`. The official Intelsat image above is kept
as a reference, not as the base for this unit.

The image is a full flash dump: it starts with the `aa55aa55` BootROM header at
offset 0 and contains the complete partition table, not just an update payload.
Neither the official image nor the device dump is committed to this repository;
download the official file from the URL above and keep your own dump private.

## Flash layout

Parsed from the GxLoader TABLE at `0x20000` (magic `aa bc de fa`):

| Partition | Start | End | Used | Notes |
| --- | ---: | ---: | ---: | --- |
| BOOT | `0x000000` | `0x020000` | `0x01ff80` | Stage-1 (`aa55aa55`, code at `0x4`) plus GxLoader/U-Boot stage-2 |
| TABLE | `0x020000` | `0x020200` | `0x000200` | 8 partition records |
| LOGO | `0x020200` | `0x06f000` | `0x00aa2c` | JPEG boot logo, 1280x720 |
| V_OEM | `0x06f000` | `0x070000` | `0x000108` | OEM/version INI |
| KERNEL | `0x070000` | `0x320000` | `0x2ae880` | ROMFS containing `ecos.bin.lzma` |
| ROOT | `0x320000` | `0x440000` | `0x0b7080` | 155 XZ-compressed UI resource chunks (fonts/images/XML) |
| DATA | `0x440000` | `0x7f0000` | `0x000001` | Writable/user data, empty in this image |
| AD | `0x7f0000` | `0x800000` | `0x000000` | Reserved advertisement area |

## Extracted artifacts

These are local-only outputs, not committed to this repository. Reproduce them
from a locally downloaded official image.

| File | Size | SHA-256 |
| --- | ---: | --- |
| `extracted/ecos.bin.lzma` | 2,811,258 | `5b7935895baa9962ae018941fdcca7d55c53632c24afb838608366938b3391cf` |
| `extracted/ecos.bin` | 6,536,184 | `d8c0f13a937b4e38952fb5e6fec9360257af1edba2ee7ee081325ea93f8c1096` |
| `extracted/logo.jpg` | 43,564 | `aa426466d813c22c9acc934739664382fcb2de54b1dd3bc308aceee99d7c031a` |
| `extracted/V_OEM.ini` | 4,096 | `d55b5cf4b8b65aa90535cc4cf9a6eb76f349781d80017dabddaa8181704a9c8d` |
| `extracted/font_arial.ttf` | 316,096 | `199356087c08f75e3f71d180ddc4ffd74a1e4ed1e9a794c972ca6ba7cafa20e9` |
| `extracted/root_resources.bin` | 3,899,149 | `3fcf7a5838d779d39ace816fee0566af572155e1847a228c83e3adbdac7013a8` |

Reproduce with:

```sh
python3 tools/v5h_extract.py firmware/V5H-Intelsat_263_flash.bin -o extracted
```

The tool writes `extracted/manifest.json` with every partition, XZ chunk offset,
and hash.

## USB-only recovery and flashing (no serial cable)

The stock firmware has a complete USB path:

- The application exposes **Upgrade by USB Disk** with Upgrade/Dump and
  All/App/User scopes, and writes a full `dump_all.bin`.
- The bootloader has a FAT driver, `usbdown`/`usbdump`, and a hard-coded
  `/recovery.rcv` recovery path.

Do this before any custom image:

1. **Dump first.** In the stock UI use Upgrade by USB Disk -> Dump -> All. This
   unit's dump is 8,323,072 bytes (`0x7F0000`) and is saved as
   `backups/dump_all.bin`; keep two copies.
2. **Prove recovery.** Put that dump on a FAT32/MBR stick as `recovery.rcv`,
   power on while pressing OK repeatedly, and wait about two minutes. Only
   proceed if the device reflashes and boots.
3. **Test a custom image.** `tools/v5h_image.py` rebuilds the TABLE CRCs.
   `out/V5H-H265-logo-test.bin` (dump-based, logo only, `0x7F0000`) is the safe
   first test; `out/recovery-H265-official.rcv` is the dump for the first
   recovery test. The official **Intelsat 2026** image is a different variant,
   so its test files live under `out/intelsat-263/` and are not for this unit.

On this unit the app accepted a custom raw image, and the app-level restore
worked. The bootloader `/recovery.rcv` path ignored both the `0x7F0000` dump and
the 8 MiB padded image while the KERNEL was valid, so it remains unproven. Do
not replace KERNEL/ROOT until you have a hardware recovery (CH341A/SPI clip or
UART) or Koqit's H.265 recovery image. Full details are in `docs/usb-only.md`.

## Serial/SPI recovery (if you have the hardware)

There is no public service manual for this board. A hardware recovery path is
still the only guaranteed way back if BOOT/TABLE is damaged.

1. **UART backup.** Use a 3.3 V USB-TTL adapter at 115200 8N1 and the vendor
   `taurus-6605H1` loader from `firmware/KOQIT-GxDownloaderBoot.zip`, or
   `libre-gxdl`'s `taurus-6605H1-sflash-27M.boot`.
2. **SPI backup.** A CH341A/SPI clip on the 8 MiB NOR is strongly recommended.
3. **Never touch OTP/eFuse** until the boot chain is fully understood.

Reference commands (verify with `--help` and a first read-only dump):

```sh
# gxdl-c / gxdl-rs style
gxdl-c -b taurus-6605H1-sflash-27M.boot -d /dev/ttyUSB0 \
       -c "serialdump 0 8388608 backup_v5h.bin"

# libre-gxdl style
python libre_gxdl.py -b loaders/taurus-6605H1-sflash-27M.boot -d /dev/ttyUSB0 \
       -c "serialdump 0 8388608 backup_v5h.bin"
```

The vendor USB-repair package (`recovery.rcv`) was linked from
`https://koqit.com/v5htool/` as `recovery5.zip` / `recovery.zip`, but those URLs
currently return 404. The device's own dump is a better recovery candidate.

## Open-firmware paths

### 1. Linux on the same SoC family (recommended)

C-Sky publishes a working Linux 4.9.y port for GX6605S with a device tree and
defconfig, plus a GCC/binutils toolchain and a dev board. A community project
(`McMCCRU/gx6605s_linux_fw_build`) already produces a full 4 MiB **SAT>IP**
Linux firmware for GX6605S receivers using the vendor flasher, including a
kernel, squashfs root, `minisatip`, and Wi-Fi/Ethernet drivers.

Start from those, then:

- change the memory node to 128 MiB and bring up DDR3 instead of DDR2;
- adapt the SPI layout from 4 MiB/GX6605S to 8 MiB/V5H, and deploy over USB
  using the stock app or `/recovery.rcv`;
- configure the community `fe.ko`, which already contains `rda5815m` and
  GXDemod support via its `profile` module parameter;
- add the V5H front panel/IR/GPIO/HDMI details;
- keep the stock BOOT or capture its stage-2 for DDR init until an open DDR3
  initializer exists.

This route gives a real Linux userspace. It does **not** automatically give
H.265 hardware decode or a polished OSD; those need the vendor VPU/OSD stack or
new drivers.

### 2. Replace eCos or write bare-metal

The CK610 ISA and GX6605S register blocks are documented (C-Sky CK610 spec,
xboot, `gxipl`, `gx6605s-emu`). A bare-metal/eCos replacement is possible but
requires reverse-engineering the DDR3 controller, demodulator, VPU, HDMI and
front-panel MCU. This is the long path.

### 3. Emulate before flashing

`RalphTamer/gx6605s-emu` is a C-SKY ABIv1 interpreter/SoC model with an OSD
renderer, CIR remote model, SPI flash model, and a firmware workbench. It was
built for GX6605S/StarSat images, but it is the best available way to smoke-test
`aa55aa55` images before risking hardware. Its `inspect` command does not yet
parse the V5H image, but its disassembler and CPU model are useful.

See `docs/open-firmware.md` for a phased plan and a compatibility/risk list.

## Risks and legal notes

- Vendor firmware and bootloader binaries are proprietary. They are kept here
  for personal interoperability research; do not redistribute them.
- The update path may validate CRC32 or other checks. The ROMFS/TABLE CRCs and
  BootROM stage-1 CRC are documented in `research/gxipl`, but the full update
  acceptance rules for this V5H image are not known.
- USB recovery is not a substitute for a hardware backup if BOOT/TABLE is
  damaged. The stock app may also enforce an image signature (`check_sign`);
  test the official or self-dumped image before any custom image.
- Reverse engineering and firmware modification legality varies by
  jurisdiction. You are responsible for how you use this.
- No warranty. A wrong flash write can permanently brick the receiver.

## Sources

See `docs/sources.md` for the full list. Key starting points:

- Koqit V5H firmware: <https://koqit.com/satellite-tv-receiver-firmware/>
- C-Sky GX6605S dev board: <https://c-sky.github.io/docs/gx6605s.html>
- C-Sky Linux 4.9.y: <https://github.com/c-sky/linux-4.9.y>
- C-Sky GX6605S tools/spec: <https://github.com/c-sky/tools/tree/master/gx6605s>
- Open GX flasher: <https://github.com/linux-goxceed> and
  <https://github.com/matu6968/libre-gxdl>
- GX6605S Linux SAT>IP builder: <https://github.com/McMCCRU/gx6605s_linux_fw_build>
- GX6605S emulator: <https://github.com/RalphTamer/gx6605s-emu>
