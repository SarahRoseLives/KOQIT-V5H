# USB-only development and recovery

> Generated images and dumps referenced here are local artifacts and are not
> committed to this repository.

The V5H does not need a serial cable for normal flashing. The stock firmware has
two USB paths:

1. the application's **Upgrade by USB Disk** menu (Upgrade/Dump, All/App/User);
2. the bootloader's own USB support and its hard-coded **`/recovery.rcv`**
   recovery path.

Both are visible in the stock images:

- The official **Intelsat** BOOT contains a FAT driver, `usbdown`/`usbdump`,
  and the literal `/recovery.rcv`.
- The actual **H.265** device BOOT is a minimal variant: it has a FAT driver
  and the literal `/recovery.rcv`, but no `usbdown`/boot menu strings.
- The eCos app contains `Upgrade by USB Disk`, `Dump successfully!`,
  `flash.bin`, `dump_all.bin`, `download_ecos.bin`, `.user`, `bin;BIN`,
  `app_upgrade_crc_check`, and `check_sign`.

Status on this H.265 unit:

- the app-level **Upgrade by USB Disk** accepted a custom raw image and the
  app-level restore brought back the stock firmware;
- the bootloader `/recovery.rcv` ignored both the `0x7F0000` dump and the 8 MiB
  padded image while the KERNEL was valid.

Treat the bootloader recovery as **unproven**. Do not replace KERNEL/ROOT until
you have a hardware recovery (CH341A + SOIC-8 SPI clip or UART adapter) or
Koqit's original H.265 `recovery.rcv`.

## Safety rules

- Do not flash a custom image until you have both:
  1. a full flash dump made by the device itself, and
  2. a proven `/recovery.rcv` restore using that dump.
- Do not modify BOOT or TABLE on your only unit.
- A failed BOOT/TABLE write can brick the device. Without a serial adapter or an
  SPI clip, recovery then depends entirely on the bootloader's USB path.
- A second identical V5H is the cheapest insurance; they are inexpensive.
- On this unit the app-level path is the only proven restore route, and it
  requires the stock app to boot. Get a CH341A/SPI clip or UART adapter before
  replacing KERNEL/ROOT or BOOT.
- The stock app may check a signature (`check_sign`, `sign error`). If it
  rejects your image, do not assume the bootloader will accept it too; test
  with the official/dumped image first.

## Step 1: full backup through the stock UI

1. Use a FAT32 USB stick with an MBR partition table (not GPT), preferably
   empty and small (4-32 GB).
2. Boot the receiver and open the utility/upgrade menu. The stock strings name
   the entry **Upgrade by USB Disk**, with an **Upgrade Type** choice of
   `Upgrade` or `Dump`, and an **All/App/User** scope.
3. Choose **Dump**, scope **All**, and start. The app writes a full image
   (internally named `dump_all.bin`).
4. Copy the file to your computer and record its size and SHA-256. On this
   **V5H H.265** unit the dump is **8,323,072 bytes (`0x7F0000`)**, excluding
   the final 64 KiB `AD` partition.
5. Keep at least two copies. This is the only trustworthy backup of your
   specific unit.

The device dump is `backups/dump_all.bin`
(`88bd3d36...b25460`). It is **not** byte-identical to the official
`firmware/V5H-Intelsat_263_flash.bin` (`15fcc1ce...a6f884`): this unit runs the
H.265 build from 2024-11-21 with a larger KERNEL and smaller ROOT. Use the dump
as the base for this device. `backups/dump_all_padded.bin` is the same dump
padded with 64 KiB of `0xFF` for tools that expect a full 8 MiB image.

## Step 2: prove the bootloader recovery path

Do this before any custom image. The vendor procedure for `recovery.rcv` is:

1. Copy the recovery file to the **root** of the FAT32 USB stick. The
   bootloader looks for the literal path `/recovery.rcv`.
2. Power the receiver off.
3. Insert the USB stick, power on, and press the remote **OK** button
   repeatedly.
4. Wait about two minutes. Do not remove the stick or cut power.
5. Power off, remove the USB stick, and power on again with no USB stick.

For the first test, use the file **you dumped from the device**, renamed to
`recovery.rcv`. That is the exact image the bootloader should expect. The
project copy is:

- `out/recovery-H265-official.rcv`
  SHA-256 `88bd3d365bd94311b58f913e316087799a7178ec6c4354d8d18aae1af7b25460`
  (the 0x7F0000 device dump)

If the device reflashes the same firmware and boots normally, you have a
USB-only restore path. If nothing happens:

- verify the stick is FAT32/MBR and the file is in the root;
- try the official image if you used the dump, or vice versa;
- try a different USB stick (some sticks are not recognized by U-Boot EHCI);
- ask Koqit support for the original `recovery.rcv` (the web links to
  `recovery5.zip`/`recovery.zip` are currently 404).

Do not proceed until this works.

## Step 3: build and test a custom image

The image builder reproduces the stock image byte-for-byte when you replace the
logo with the same logo, so its TABLE/CRC logic is verified:

```sh
python3 tools/v5h_image.py info backups/dump_all_padded.bin
python3 tools/v5h_image.py replace backups/dump_all_padded.bin \
    -o out/my-test.bin --logo my_logo.jpg --truncate 0x7f0000 --recovery-copy
```

Use the dump as the template for this H.265 unit. The `--truncate 0x7f0000`
option produces the same size as the stock app's dump/upgrade file.

The tool rebuilds the known CRCs:

| Location | Covers | Algorithm |
| --- | --- | --- |
| TABLE+`0x19d` | BOOT `[0:used]` | zlib CRC32, big-endian |
| TABLE+`0x1a9` | V_OEM `[0:used]` | zlib CRC32, big-endian |
| TABLE+`0x1ad` | KERNEL `[0:used]` | zlib CRC32, big-endian |
| TABLE+`0x1fc` | TABLE `[0:0x1fc]` | zlib CRC32, big-endian |

LOGO, ROOT, DATA and AD have no per-partition CRC in this image; the TABLE CRC
still covers their record changes.

A ready-made safe first test for this device is:

- `out/V5H-H265-logo-test.bin` / `out/recovery-H265-logo-test.rcv`
- SHA-256 `d948f957eca422475c820d3320bb9537601030e4dc90864b3827f4db8fbc685d`

It is the **device dump** with **only the LOGO partition changed**, `0x7F0000`
bytes, matching the stock dump size. BOOT, V_OEM, KERNEL and ROOT are untouched,
and all CRCs verify. If the receiver boots with the new test logo, USB flashing
and the CRC/TABLE path are working.

Flash it by either:

- the stock **Upgrade by USB Disk** menu with `V5H-H265-logo-test.bin`;
- or the bootloader `/recovery.rcv` path with
  `recovery-H265-logo-test.rcv` renamed to `recovery.rcv`.

The older `out/intelsat-263/` files are based on the official Intelsat variant
and are **not** for this H.265 unit.

If the app reports a sign error, the app path rejects unsigned images; try the
bootloader path. If the bootloader path also rejects it, custom firmware via USB
is blocked on the stock bootloader and you need a serial/SPI recovery route or a
vendor-signed container.

## Step 4: the Linux firmware route

The stock bootloader is a GxLoader/U-Boot fork with `uImage_load_kernel`,
`cramfs_load_kernel`, `romfs_load`, and filesystem strings for `cramfs`,
`squashfs`, `yaffs2`, and `minifs`. That means it can boot a Linux kernel from
the KERNEL partition and mount a Linux rootfs from the ROOT partition, without
replacing BOOT.

The community GX6605S Linux build is a strong starting point:

- `research/gx6605s_linux_fw_build/` builds a uImage, a rootfs, and a full
  flash image with `genflash`.
- Its `fe.ko` **already supports RDA5815M** (`rda5815m`,
  `rda581x_rda5815m_init`) and GXDemod, with a `profile` module parameter for
  I2C/tuner/demod configuration.
- Its `av.ko` is built for `chip_gx6605s`.
- Its 4 MB `flash.conf` shows the layout: BOOT, TABLE, KERNEL=uImage,
  ROOTFS=rootfs, DATA=minifs.

For the V5H:

- Keep the stock BOOT so Taurus DDR3/128 MiB is initialized.
- Build a uImage for the GX6605S/GX6605H1 C-SKY kernel at load/entry
  `0x90000000`.
- Adjust the device tree memory to 128 MiB (`0x10000000`, size `0x08000000`).
- Fit the rootfs into an 8 MiB layout. On this H.265 unit the ROOT is only
  `0x110000` (1.06 MiB), so use the image tool's layout options to shrink
  KERNEL and grow ROOT:

```sh
# Example: 1 MiB kernel, 3.5 MiB root, DATA takes the remainder.
python3 tools/v5h_image.py replace backups/dump_all_padded.bin \
    -o out/V5H-linux.bin \
    --kernel uImage --root rootfs.img \
    --set-total KERNEL=0x100000 --set-total ROOT=0x380000 --auto-data \
    --truncate 0x7f0000
```

- Start with a minimal rootfs: BusyBox, `fe.ko`, the demux/AV modules needed for
  DVB, and `minisatip`. Leave out the Wi-Fi module zoo until the tuner works.
- If the rootfs is squashfs, keep the ROOT record's `fs_type` and let the
  bootloader detect it; the stock image's ROOT is a custom XZ resource store,
  so this is one of the first things to verify on hardware.
- A headless SAT>IP server needs no VPU/OSD/HDMI work. A full UI still does.

## USB hardware notes

- The USB ports are host ports (EHCI/OHCI); the stock app supports USB storage,
  USB Ethernet (`SR9900`), and USB Wi-Fi (`MT7601`, `RT5370`, `RTL8188FU`).
- U-Boot's FAT driver supports FAT12/16/32. Use a simple MBR stick; avoid GPT,
  exFAT, and unusual cluster sizes for the recovery test.
- Some sticks are not detected by the bootloader. Keep a known-good small stick
  for recovery.

## If something goes wrong

- **App sees no file:** FAT32/MBR, root directory, `.bin` extension for the app,
  exact `recovery.rcv` name for the bootloader.
- **Sign error:** the app's update signature check rejected the image. Try the
  bootloader recovery path or obtain a vendor-signed container.
- **No boot after flashing:** insert the USB with the proven `recovery.rcv`,
  power on, press OK repeatedly. If the bootloader itself is damaged and the USB
  path does not run, only a serial/SPI recovery can help.
- **Recovery file not accepted:** the container format differs from a raw full
  image. The dump produced by the stock app is the best candidate; otherwise ask
  Koqit for the original recovery package.
