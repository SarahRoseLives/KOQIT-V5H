# Sources and downloads

Collected 2026-11-19. Status notes are what was observed at collection time.

## Koqit official material

| Source | URL | Status / notes |
| --- | --- | --- |
| V5H firmware page | <https://koqit.com/satellite-tv-receiver-firmware/> | Lists `V5H-Intelsat_263_flash.bin`, OTA notes, update log |
| V5H full firmware | <https://koqit.com/STB/upnet/V5H/V5H-Intelsat_263_flash.bin> | 8 MiB, build 2026-01-09, downloaded |
| Firmware index | <https://koqit.com/firmware/> | Lists V5H, K1 Mini, T10, ATSC |
| V5H USB repair page | <https://koqit.com/v5htool/> | Describes `recovery.rcv`; linked `recovery5.zip`/`recovery.zip` return 404 |
| RS232/GxDownloader page | <https://koqit.com/koqit-rs232/> | Links `KOQIT-GxDownloaderBoot.zip`, downloaded |
| GxDownloader package | <https://koqit.com/wp-content/uploads/2021/03/KOQIT-GxDownloaderBoot.zip> | Contains `taurus-6605H1-sflash.boot` |
| Image tool page | <https://koqit.com/editor/> | Vendor bin editor; password required |
| Image tool package | <https://koqit.com/wp-content/uploads/editor/Koqit_imagetoolv3.43.zip> | Downloaded; zip requires vendor password |
| MeeCast page | <https://koqit.com/meecast/> | Companion app |

The V5H page's update log mentions:
- 2026-01-08: YouTube fix, dynamic network authorization, Dolby Plus EAC3.
- 2022-05-25: Newcam Irdeto, TikTok/Stalker, Mshare Pro+.
- 2021-10-19: EPG import fix, MeeTube/YouTube Kids, net-upgrade link.
- 2021-05-17: C/Ku satellite list, CCCam/Newcam import, TV Control remote.

## C-Sky / NationalChip

| Source | URL | Notes |
| --- | --- | --- |
| GX6605S dev board | <https://c-sky.github.io/docs/gx6605s.html> | CK610M, MMU, 64 MiB DDR2, 4 MiB SPI, toolchain/Linux links |
| Linux 4.9.y | <https://github.com/c-sky/linux-4.9.y> | `arch/csky/boot/dts/gx6605s.dts`, `gx6622.dts`, `arch/csky/configs/gx66xx_defconfig` |
| GX6605S tools | <https://github.com/c-sky/tools/tree/master/gx6605s> | `CK610_spec.pdf.tgz`, `pcbv1.1.pdf`, `boot.elf.tgz`, `gx6605s-generic-sflash.boot`, `loader-sflash.bin.tgz` |
| Linux SDK examples | <https://github.com/c-sky/linux-sdk-examples> | Framebuffer, ffmpeg player, IIS, V4L2 examples |
| Addons / vendor drivers | <https://github.com/c-sky/addons-linux> | `drivers/video/fbdev/nationalchip/gx6605s*.h` |
| C-Sky docs | <https://github.com/c-sky/csky-doc> | ABI and architecture manuals |
| Buildroot (newer XuanTie) | <https://github.com/c-sky/buildroot> | Not GX6605S-specific; useful for toolchain patterns |

`research/csky/` contains downloaded DTS/defconfig and the tools assets.

## Open-source flashers and boot code

| Project | URL | Notes |
| --- | --- | --- |
| linux-goxceed | <https://github.com/linux-goxceed> | Open GX IPL, flashers, C-SKY binutils/gcc forks |
| gxipl | <https://github.com/linux-goxceed/gxipl> | Open IPL for GX6702/GX6706 CK610; boot protocol, TABLE, CRC, DDR notes |
| gxdl-c | <https://github.com/linux-goxceed/gxdl-c> | C flasher, UART BootROM protocol |
| gxdl-rs | <https://github.com/linux-goxceed/gxdl-rs> | Rust flasher; supports Taurus loaders |
| libre-gxdl | <https://github.com/matu6968/libre-gxdl> | Python flasher; includes `taurus-6605H1-sflash-27M.boot` |
| rva3/gx6605s-loader | <https://github.com/rva3/gx6605s-loader> | GX6605S BootROM protocol notes |
| xboot GX6605S | <https://github.com/GX-OSS/xboot-gx6605s> | MIT register definitions (referenced by gx6605s-emu) |
| T-Head QEMU | <https://github.com/T-head-Semi/qemu> | C-SKY ABI v1 translator used as an ISA reference |

## Linux firmware and emulation projects

| Project | URL | Notes |
| --- | --- | --- |
| McMCCRU GX6605S Linux builder | <https://github.com/McMCCRU/gx6605s_linux_fw_build> | SAT>IP Linux firmware, 4 MiB image, `minisatip`, vendor modules |
| gx6605s-emu | <https://github.com/RalphTamer/gx6605s-emu> | C-SKY ABI v1 emulator, OSD/CIR/SPI models, disassembler, firmware workbench |
| KR0SIV KOQIT mod | <https://github.com/KR0SIV/KOQIT-GX6605S-Digital-ATV-Firmware> | Repacked KOQIT K1 Mini GX6605S image for DATV |
| vk-hca Himawarri | <https://github.com/vk-hca/GX6605s-receiver-for-Himawarri> | Notes on turning a GX6605S receiver into a TCP DVB-S2 receiver |
| epbrijesh/gx6605s | <https://github.com/epbrijesh/gx6605s> | GX6605S bin files |

## Documentation and community pages

| Source | URL | Notes |
| --- | --- | --- |
| 3ABN V5H H.265 instructions | <https://3abn.org/pdfs/news/Koqit-V5H-H265.pdf> | 2-page PDF: rescan instructions, not firmware |
| Jungle-Team V5H review | <https://jungle-team.com/review-koqit-v5h/> | Teardown, 128 MiB DDR3, 8 MiB flash, tuner tests, photos |
| Mr-Dish V5H page | <https://www.mr-dish.com/koqit-v5h-h-265/> | Specs, firmware update notes |
| About STB KOQIT downloads | <https://aboutstb.com/en/downloads/KOQIT/KOQIT-V5> | SPA requiring auth; not scraped |
| Dekazeta VH5 firmware | <https://www.dekazeta.net/foro/files/file/3184-koqit-vh5-firmware/> | Login required; forum copy |
| ManualsLib V5H | <https://www.manualslib.com/manual/4655018/Koqit-V5h.html> | User manual |
| Manuals.plus V5H | <https://manuals.plus/asin/B0817ZN2ML> | User manual |

## Firmware strings worth preserving

From `extracted/ecos.bin`:

```text
V5H Intelsat / V5H-Intelsat
GX6605H1 / taurus
Build Time 2026-01-09 15:00:07
csky-ecos
Nationalchip GXDemod S2
rda5815m
koqit.com/upnet/intelsat/1817
www.smartupg.com
download_ecos.bin
/mnt/netupg_ecos.bin
```

The embedded OTA URL returns HTTP 403 from this network. The eCos app also
contains FTP credentials and activation endpoints; these are vendor service
credentials and are intentionally not reproduced or used here.

## Dead or gated links

- `https://koqit.com/wp-content/uploads/2020/12/recovery5.zip` - 404.
- `https://koqit.com/wp-content/uploads/2022/05/recovery.zip` - 404.
- `https://koqit.com/upnet/intelsat/1817` - 301 then 403.
- Dekazeta download - login required.
- About STB catalogue API - requires Firebase token and HMAC; not public.
- Khandish Network - blocked by network policy / TLS mismatch at collection.
