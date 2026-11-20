# Device backup and firmware variant

> The dump and generated images described here are local-only and are not
> committed to the public repository. Only this metadata/test log is published.

## `dump_all.bin`

Created by the stock **Upgrade by USB Disk -> Dump -> All** menu on the actual
receiver.

| Field | Value |
| --- | --- |
| Size | 8,323,072 bytes (`0x7F0000`) |
| SHA-256 | `88bd3d365bd94311b58f913e316087799a7178ec6c4354d8d18aae1af7b25460` |
| Firmware | `V5H H.265`, build `2024-11-21 17:41:17` |
| OTA identity string | `koqit.com/STB/upnet/eV5H` |
| SoC string | `GX6605H1` |

The app does not dump the final 64 KiB `AD` partition
(`0x7F0000`-`0x800000`). It is empty/reserved in this image.

## `dump_all_padded.bin`

`dump_all.bin` plus 64 KiB of `0xFF`, for tools that expect a full 8 MiB image.

| Field | Value |
| --- | --- |
| Size | 8,388,608 bytes (`0x800000`) |
| SHA-256 | `6047ba86022bc060c27a3f69bef8a705f92f8ac06665e1da1a93528a9262e5de` |

## Layout of this device

| Partition | Start | End | Used |
| --- | ---: | ---: | ---: |
| BOOT | `0x000000` | `0x020000` | `0x01ff80` |
| TABLE | `0x020000` | `0x020200` | `0x000200` |
| LOGO | `0x020200` | `0x06f000` | `0x00aa2c` |
| V_OEM | `0x06f000` | `0x070000` | `0x000108` |
| KERNEL | `0x070000` | `0x330000` | `0x2b6880` |
| ROOT | `0x330000` | `0x440000` | `0x0a1080` |
| DATA | `0x440000` | `0x7f0000` | `0x000001` |
| AD | `0x7f0000` | `0x800000` | `0x000000` |

This differs from the official **V5H Intelsat** image in
`firmware/V5H-Intelsat_263_flash.bin`:

| | This device (H.265 2024) | Official Intelsat 2026 |
| --- | ---: | ---: |
| KERNEL total | `0x2C0000` | `0x2B0000` |
| ROOT start | `0x330000` | `0x320000` |
| ROOT total | `0x110000` | `0x120000` |
| BOOT CRC | `6d7fed05` | `12c4d0f8` |
| KERNEL CRC | `1103fa38` | `a811741b` |
| TABLE CRC | `40b54dc2` | `d5c0d69c` |

Do not flash the official Intelsat image to this H.265 device without checking
the bootloader/variant compatibility. The dump in this directory is the correct
base for this unit.

## Extracted components

`extracted-h265/` contains the dump's unpacked eCos application, ROMFS member,
logo, OEM config and UI resources. Its eCos binary is different from the
official Intelsat build:

```text
extracted-h265/ecos.bin       e9a22db39c54b72b2d374e1bcad24427dccac9cafa38be38630a0b2cdc694a69
extracted-h265/ecos.bin.lzma  e58099b186422954503dda8cab2a29779b322d410acfe515be6e89e93e1f33a7
extracted-h265/logo.jpg       aa426466d813c22c9acc934739664382fcb2de54b1dd3bc308aceee99d7c031a
```

The logo is identical to the official image, so the dump is consistent and
complete.

## Generated USB files

- `out/recovery-H265-official.rcv`: this dump (`0x7F0000`) for the bootloader
  `/recovery.rcv` test.
- `out/V5H-H265-logo-test.bin`: dump-based, logo only, `0x7F0000`,
  SHA-256 `d948f957eca422475c820d3320bb9537601030e4dc90864b3827f4db8fbc685d`.
- `out/recovery-H265-logo-test.rcv`: the same logo-only image for recovery.
- `out/V5H-H265-logo-test-8m.bin`: the same logo-only image padded to 8 MiB
  for tools that require the full flash size.

## USB upgrade and recovery test log

- **App-level logo-only upgrade:** the stock app's **Upgrade by USB Disk** file
  list showed `/mnt/usb01/V5H-H265-logo-test.bin`; after the upgrade the
  receiver booted with the new test logo. The app accepts the dump-based image,
  writes the LOGO partition, and the TABLE/CRC layout is valid.
  Screenshots: `Screenshots/Upgrade_test.png` and `Screenshots/boot.png`.
- **Bootloader `/recovery.rcv` with the `0x7F0000` raw dump:** the device
  booted normally, but the test logo remained. The bootloader did not consume
  this file/container.
- **App-level restore with the `0x7F0000` official dump:** the app accepted
  `V5H-H265-official.bin` and the stock KOQIT logo returned. This proves the
  app-level restore path.
- **Bootloader `/recovery.rcv` with the 8 MiB padded test-logo image:** the
  device booted normally and the **stock logo remained**. The 8 MiB container
  was also not consumed.
- **KERNEL modification attempts:** the app rejected corrupted KERNEL content,
  a bad KERNEL CRC, and TABLE `used_size`/`start` changes. The app appears to
  validate the KERNEL content/signature against the stock layout, so the
  app-level upgrade cannot be used to write a custom KERNEL. LOGO-only changes
  are still accepted.
- **Conclusion:** on this H.265 unit the bootloader does not treat either a
  `0x7F0000` dump or an 8 MiB padded image as `recovery.rcv`. The H.265
  bootloader is a minimal variant (no `usbdown`, no boot menu strings), so the
  recovery path likely needs a vendor-specific container/trigger or a
  kernel-failure condition. The app-level Upgrade path is proven for LOGO and
  app-level restore, but it is blocked for KERNEL changes.

Remaining writers for a custom KERNEL:

1. the bootloader `/recovery.rcv` path (need to find the trigger/container);
2. the IR micro-USB port in USB device mode (connect to a PC and check
   enumeration);
3. Koqit's original H.265 recovery package;
4. a bypass in the app's update validation/writer found by reverse
   engineering.

Do not replace KERNEL/ROOT until one of these is proven.
