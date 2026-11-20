# V5H firmware format

> Vendor firmware is not redistributed in this repository. Download the official
> image from the vendor and place it locally at `firmware/`.

Tested against `firmware/V5H-Intelsat_263_flash.bin` (8,388,608 bytes,
SHA-256 `15fcc1ce...a6f884`).

## Top level

The file is a complete SPI NOR image, not an update package:

- offset `0x0`: `aa55aa55` BootROM magic, then stage-1 code (the vendor
  `.boot` files place the same body at offset `0x20` after a `toob` wrapper).
- offset `0x20000`: GxLoader TABLE (`aa bc de fa`).
- offset `0x20200`: JPEG boot logo.
- offset `0x70000`: ROMFS containing the LZMA-compressed eCos application.
- offset `0x320000`: XZ-compressed UI resource store.

## Partition table

The TABLE is 512 bytes at `0x20000`:

```text
+0x00  u8[4]  magic = aa bc de fa
+0x04  u8     record count (8)
+0x05  record[count]
```

Each record is 24 bytes, multi-byte fields big-endian:

```text
+0x00  char[8] name
+0x08  u32     total_size
+0x0c  u32     used_size
+0x10  u32     start (contiguous from 0)
+0x14  u8      fs_type
+0x15  u8      flags
+0x16  u8      id
+0x17  u8      padding
```

This matches `research/gxipl/include/gx_table.h` and
`research/gxipl/bootcode/gx_table.c`. The `gxipl` parser expects the table at a
64 KiB boundary; here it is at `0x20000` because BOOT is 128 KiB.

Parsed result:

| Part | Start | Total | Used | fs |
| --- | ---: | ---: | ---: | ---: |
| BOOT | `0x000000` | `0x020000` | `0x01ff80` | 0 |
| TABLE | `0x020000` | `0x000200` | `0x000200` | 0 |
| LOGO | `0x020200` | `0x04ee00` | `0x00aa2c` | 0 |
| V_OEM | `0x06f000` | `0x001000` | `0x000108` | 0 |
| KERNEL | `0x070000` | `0x2b0000` | `0x2ae880` | 0 |
| ROOT | `0x320000` | `0x120000` | `0x0b7080` | 6 |
| DATA | `0x440000` | `0x3b0000` | `0x000001` | 127 |
| AD | `0x7f0000` | `0x010000` | `0x000000` | 0 |

This table is the official **V5H Intelsat** image. The actual receiver dump is
the **V5H H.265** build, which uses the same format but a different split:

| Part | Start | Total | Used |
| --- | ---: | ---: | ---: |
| KERNEL | `0x070000` | `0x2c0000` | `0x2b6880` |
| ROOT | `0x330000` | `0x110000` | `0x0a1080` |
| DATA | `0x440000` | `0x3b0000` | `0x000001` |
| AD | `0x7f0000` | `0x010000` | `0x000000` |

The stock app's dump is `0x7F0000` bytes (AD excluded). See
`backups/README.md`.

`fs_type` values are vendor-defined. In the companion GX6605S images the ROOT
partition is a CramFS; here it is the custom chunked-XZ store described below.

## BOOT

The first 128 KiB contain the first stage and the GxLoader/U-Boot stage-2:

- `0x0`: `aa55aa55`.
- `0x4`: stage-1 body. `research/gxipl` documents the flash BootROM copying
  `BOOT[4:0x2000]` to SRAM `0x00100000` and checking an MSB-first CRC-32
  (poly `0x04C11DB7`, init `0xffffffff`, no final XOR) over the first
  `0x1ff8` bytes, with the checksum word at `0x1ff8`.
- `0x1d4dc`: readable `U-Boot` strings; stage-2 is a vendor NationalChip
  U-Boot/GxLoader fork.
- `research/libre-gxdl/loaders/taurus-6605H1-sflash-27M.boot` is a matching
  Taurus loader for the UART BootROM protocol.
- `firmware/KOQIT-GxDownloaderBoot.zip` contains the vendor loader
  `boot_file/taurus-6605H1-sflash.boot`.

The stage-2 body is not open source. `gxipl` only implements Gemini
(GX6702) and Cygnus (GX6706) initialization, not Taurus; it can be used as a
reference for the CK610 boot protocol and TABLE handling.

## LOGO and V_OEM

- LOGO (`0x20200`, `0xaa2c` bytes) is a baseline 1280x720 JPEG with EXIF/XMP
  metadata. Extract as `extracted/logo.jpg`.
- V_OEM (`0x6f000`, one 4 KiB sector) is an INI file:

```ini
[variable_oem]
version=0.0.1
[system]
update_type= auto
update_default_url=
[software]
bootloader_version=0.0.1
logo_version=0.0.1
application_version=0.0.1
rootfs_version=0.0.1
datafs_version=0.0.1
[update]
HwModel=0x0101
HwVer=0x0101
SwModel=0x0a10
SwVer=0x0201
```

The version fields are placeholders; the real version is in the app strings.

## KERNEL: ROMFS + LZMA eCos

KERNEL begins with a ROMFS superblock at `0x70000` (relative offset 0):

```text
0x70000  "-rom1fs-"
0x70008  be32 total size = 0x2ae600
0x7000c  be32 checksum
0x70010  volume name "rom 6960a786"
0x70060  inode header for the only large member
0x70068  be32 compressed size = 0x2ae57a
0x70070  "ecos.bin.lzma\0"
0x70080  LZMA-Alone stream (properties 0x66, dict 0x00800000)
```

The LZMA stream decompresses to `extracted/ecos.bin` (6,536,184 bytes). The
declared ROMFS size is `0x2ae600`; the file data ends six bytes before the
declared end, which is normal padding.

This ROMFS is a NationalChip variant: its inode `next` fields do not follow the
standard Linux ROMFS linked-list layout. The extractor therefore locates the
`.lzma` member by walking 16-byte-aligned inode headers and validating the size
and name, rather than trusting `next`.

### eCos application

`ecos.bin` is a raw C-SKY eCos image (not ELF). It contains the whole UI and
application stack:

- brand/model: `V5H Intelsat`, `V5H-Intelsat`, `GX6605H1`, `taurus`;
- build time: `2026-01-09 15:00:07`;
- eCos build marker: `csky-ecos`;
- frontends: `Nationalchip GXDemod S2`, `rda5815m`, `M3031`, `TS6011`,
  `ATBM253_DVBT`, `ATBM2040_DVBT`;
- features: MeeCast, YouTube, IPTV/M3U, Xtream, Stalker, Newcam/CCcam,
  Mshare Pro+, DVB2IP, PVR, PDF/EPUB viewer, UPnP/DLNA;
- OTA strings: `koqit.com/upnet/intelsat/1817`, `www.smartupg.com`,
  `download_ecos.bin`, `/mnt/netupg_ecos.bin`;
- `flash.bin`, `dump_all.bin`, `userdb.bin` update/backup names;
- `/dev/gx*` device names and eCos audio/VPU firmware version strings.

A useful next step is disassembly with a CK610 ABI-v1 toolchain. The
`linux-goxceed/binutils-gdb` and `linux-goxceed/gcc` forks, or a C-Sky vendor
toolchain, can do this. `RalphTamer/gx6605s-emu` already contains a C-SKY
interpreter/disassembler and can help map the image.

## ROOT: chunked XZ resource store

ROOT (`0x320000`, used `0xb7080`) is not a CramFS in this image. The first
`0x2814` bytes before the first XZ stream did not yield a readable index.

The data is a sequence of **155 independent XZ streams**, most of which
decompress to exactly 32 KiB. Concatenating the decompressed streams in order
produces a 3,899,149-byte resource blob containing:

- Arial TrueType font (`00010000` sfnt header) at the start, 316,096 bytes;
- JPEG images (`ffd8ff...`);
- BMP images (`BM...`);
- PNG images (`89504e47...`);
- XML UI layout and translation files (`<?xml ...`);
- possible raw audio/video or table data at the end.

There is no recovered filename index. The chunk boundaries are not always file
boundaries: a file can span several 32 KiB chunks (the Arial font uses 10).
`tools/v5h_extract.py` writes the complete reconstructed blob as
`root_resources.bin` and carves the first font as `font_arial.ttf`.

## Checksums and TABLE CRCs

The V5H TABLE stores fixed-position CRCs in its 512-byte tail. Verified against
the stock image:

| TABLE offset | Covers | Algorithm |
| --- | --- | --- |
| `0x19d` | BOOT `[0:used]` | zlib CRC32, big-endian |
| `0x1a9` | V_OEM `[0:used]` | zlib CRC32, big-endian |
| `0x1ad` | KERNEL `[0:used]` | zlib CRC32, big-endian |
| `0x1fc` | TABLE `[0:0x1fc]` | zlib CRC32, big-endian |

The H.265 device dump uses the same offsets with different values:
BOOT `6d7fed05`, V_OEM `0db69d42`, KERNEL `1103fa38`, TABLE `40b54dc2`.

LOGO, ROOT, DATA and AD have no per-partition CRC in this image. The record
flags (`0x80` for BOOT/TABLE/V_OEM/KERNEL) correlate with the CRC-bearing
partitions, but the exact flag semantics are not confirmed.

`tools/v5h_image.py` rebuilds these values. Rebuilding the stock image with the
same logo produces a byte-identical file, which validates the layout and CRC
logic.

Other checksum notes:

- ROMFS has a 32-bit checksum at `0x7000c`; the standard ROMFS algorithm is
  known, but this variant's exact coverage should be verified before repacking.
- CramFS in companion images uses the standard little-endian magic and CRC32;
  this V5H ROOT does not use CramFS.
- The OTA/USB update acceptance rules are not fully known. `check_sign` in the
  app suggests a signature check; the bootloader `/recovery.rcv` path may be
  more permissive.

## USB update and recovery paths

The stock image exposes both a user-level and a bootloader-level USB path:

- App: `Upgrade by USB Disk`, Upgrade/Dump, All/App/User, `.bin` file filter,
  `flash.bin`, `download_ecos.bin`, `dump_all.bin`, `.user`.
- App validation strings: `app_upgrade_crc_check`, `check_sign`,
  `%s(%d) sign error:...`.
- Bootloader: FAT12/16/32 driver, `usbdown`, `usbdump`, and the literal
  `/recovery.rcv`.
- Bootloader kernel loaders: `uImage_load_kernel`, `cramfs_load_kernel`,
  `romfs_load`, plus `cramfs`, `squashfs`, `yaffs2`, `minifs` filesystem
  strings. This is why a Linux uImage/CramFS/SquashFS can be placed in
  KERNEL/ROOT without replacing BOOT.

See `docs/usb-only.md` for the workflow and safety rules.

## Appendix: known hashes

```text
image                 15fcc1ce5502304c2f939ec34bc49024a8f1b30f4e86e053495c921848a6f884
ecos.bin.lzma         5b7935895baa9962ae018941fdcca7d55c53632c24afb838608366938b3391cf
ecos.bin              d8c0f13a937b4e38952fb5e6fec9360257af1edba2ee7ee081325ea93f8c1096
logo.jpg              aa426466d813c22c9acc934739664382fcb2de54b1dd3bc308aceee99d7c031a
V_OEM.ini             d55b5cf4b8b65aa90535cc4cf9a6eb76f349781d80017dabddaa8181704a9c8d
font_arial.ttf        199356087c08f75e3f71d180ddc4ffd74a1e4ed1e9a794c972ca6ba7cafa20e9
root_resources.bin    3fcf7a5838d779d39ace816fee0566af572155e1847a228c83e3adbdac7013a8
```
