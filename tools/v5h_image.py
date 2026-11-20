#!/usr/bin/env python3
"""Inspect and rebuild KOQIT V5H / GX6605H1 full-flash images.

The stock V5H TABLE stores partition CRCs at fixed offsets:

  TABLE+0x19d  BOOT   CRC32(BOOT[0:used])
  TABLE+0x1a9  V_OEM  CRC32(V_OEM[0:used])
  TABLE+0x1ad  KERNEL CRC32(KERNEL[0:used])
  TABLE+0x1fc  TABLE  CRC32(TABLE[0:0x1fc])

All are standard zlib CRC32 values stored big-endian. LOGO, ROOT, DATA and AD
have no per-partition CRC in this image; only the TABLE CRC covers them.

This tool is for building test/recovery images. It does not flash anything.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import zlib
from pathlib import Path

TABLE_OFF = 0x20000
TABLE_SIZE = 0x200
TABLE_MAGIC = bytes.fromhex("aabcdefa")
TABLE_CRC_OFF = 0x1FC
CRC_OFF = {"BOOT": 0x19D, "V_OEM": 0x1A9, "KERNEL": 0x1AD}
PART_NAMES = ("BOOT", "TABLE", "LOGO", "V_OEM", "KERNEL", "ROOT", "DATA", "AD")


def be32(buf: bytes, off: int) -> int:
    return struct.unpack_from(">I", buf, off)[0]


def put_be32(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into(">I", buf, off, value & 0xFFFFFFFF)


def parse_table(image: bytes) -> list[dict]:
    table = image[TABLE_OFF:TABLE_OFF + TABLE_SIZE]
    if table[:4] != TABLE_MAGIC:
        raise SystemExit("TABLE magic aabcdefa not found at 0x20000")
    count = table[4]
    if not 1 <= count <= 16:
        raise SystemExit(f"invalid partition count {count}")
    parts = []
    pos = 5
    for _ in range(count):
        rec = table[pos:pos + 24]
        name = rec[:8].split(b"\0", 1)[0].decode("latin1")
        parts.append({
            "name": name,
            "rec_off": pos,
            "total_size": be32(rec, 8),
            "used_size": be32(rec, 12),
            "start": be32(rec, 16),
            "fs_type": rec[20],
            "flags": rec[21],
            "id": rec[22],
        })
        pos += 24
    return parts


def table_of(image: bytes) -> bytearray:
    return bytearray(image[TABLE_OFF:TABLE_OFF + TABLE_SIZE])


def set_used(table: bytearray, part: dict, used: int) -> None:
    put_be32(table, part["rec_off"] + 12, used)


def set_total(table: bytearray, part: dict, total: int) -> None:
    put_be32(table, part["rec_off"] + 8, total)


def set_start(table: bytearray, part: dict, start: int) -> None:
    put_be32(table, part["rec_off"] + 16, start)


def table_crc(table: bytes) -> int:
    return zlib.crc32(table[:TABLE_CRC_OFF]) & 0xFFFFFFFF


def partition_crc(image: bytes, part: dict) -> int:
    start = part["start"]
    used = part["used_size"]
    return zlib.crc32(image[start:start + used]) & 0xFFFFFFFF


def rebuild_crcs(image: bytearray) -> None:
    table = table_of(image)
    for part in parse_table(image):
        off = CRC_OFF.get(part["name"])
        if off is None:
            continue
        put_be32(table, off, partition_crc(image, part))
    put_be32(table, TABLE_CRC_OFF, table_crc(table))
    image[TABLE_OFF:TABLE_OFF + TABLE_SIZE] = table


def verify(image: bytes) -> list[tuple[str, bool, str]]:
    table = image[TABLE_OFF:TABLE_OFF + TABLE_SIZE]
    results = []
    for part in parse_table(image):
        off = CRC_OFF.get(part["name"])
        if off is None:
            results.append((part["name"], True, "no per-partition CRC"))
            continue
        stored = be32(table, off)
        calc = partition_crc(image, part)
        results.append((part["name"], stored == calc, f"{stored:08x} vs {calc:08x}"))
    stored = be32(table, TABLE_CRC_OFF)
    calc = table_crc(table)
    results.append(("TABLE", stored == calc, f"{stored:08x} vs {calc:08x}"))
    return results


def replace_partition(image: bytearray, name: str, data: bytes, pad: int = 0xFF) -> None:
    parts = {p["name"]: p for p in parse_table(image)}
    if name not in parts:
        raise SystemExit(f"partition {name} not found")
    part = parts[name]
    if len(data) > part["total_size"]:
        raise SystemExit(
            f"{name}: file is {len(data):#x} bytes, partition is only {part['total_size']:#x}"
        )
    start = part["start"]
    image[start:start + part["total_size"]] = bytes([pad]) * part["total_size"]
    image[start:start + len(data)] = data
    table = table_of(image)
    set_used(table, part, len(data))
    image[TABLE_OFF:TABLE_OFF + TABLE_SIZE] = table
    rebuild_crcs(image)


def build_with_layout(
    image: bytes,
    replacements: dict[str, bytes],
    totals: dict[str, int],
    auto_data: bool,
    pad: int = 0xFF,
) -> bytearray:
    """Rebuild the image with new partition sizes, copying untouched data."""
    parts = parse_table(image)
    by_name = {p["name"]: p for p in parts}
    fixed = {"BOOT", "TABLE", "LOGO", "V_OEM"}

    new_totals = {}
    for part in parts:
        name = part["name"]
        total = totals.get(name, part["total_size"])
        if name in fixed and total != part["total_size"]:
            raise SystemExit(f"{name}: resizing this partition is not supported")
        new_totals[name] = total

    if auto_data:
        used = sum(t for n, t in new_totals.items() if n != "DATA")
        new_totals["DATA"] = 0x800000 - used

    if sum(new_totals.values()) != 0x800000:
        raise SystemExit(
            f"partition totals sum to {sum(new_totals.values()):#x}, expected 0x800000"
        )

    starts = {}
    pos = 0
    for part in parts:
        starts[part["name"]] = pos
        pos += new_totals[part["name"]]

    new = bytearray([pad]) * 0x800000
    table = table_of(image)
    for part in parts:
        name = part["name"]
        total = new_totals[name]
        start = starts[name]
        old_start = part["start"]
        old_total = part["total_size"]
        base = bytearray(image[old_start:old_start + old_total])
        if len(base) < total:
            base.extend(bytes([pad]) * (total - len(base)))
        else:
            base = base[:total]

        if name in replacements:
            data = replacements[name]
            if len(data) > total:
                raise SystemExit(
                    f"{name}: {len(data):#x} bytes does not fit in total {total:#x}"
                )
            base[:len(data)] = data
            used = len(data)
        else:
            used = part["used_size"]
            if used > total:
                raise SystemExit(
                    f"{name}: existing used size {used:#x} exceeds new total {total:#x}"
                )

        new[start:start + total] = base
        set_start(table, part, start)
        set_total(table, part, total)
        set_used(table, part, used)
    new[TABLE_OFF:TABLE_OFF + TABLE_SIZE] = table
    rebuild_crcs(new)
    return new


def info(image: bytes) -> None:
    print(f"size: {len(image)} ({len(image):#x})")
    print(f"sha256: {hashlib.sha256(image).hexdigest()}")
    print(f"{'name':8} {'start':>8} {'total':>8} {'used':>8}  flags fs")
    for part in parse_table(image):
        print(f"{part['name']:8} {part['start']:8x} {part['total_size']:8x} "
              f"{part['used_size']:8x}  {part['flags']:#04x} {part['fs_type']}")
    print("CRCs:")
    for name, ok, detail in verify(image):
        print(f"  {name:8} {'OK ' if ok else 'BAD'} {detail}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="show partitions and verify CRCs")
    p_info.add_argument("image", type=Path)

    p_rep = sub.add_parser("replace", help="replace one or more partitions")
    p_rep.add_argument("image", type=Path)
    p_rep.add_argument("-o", "--output", type=Path, required=True)
    for name in ("logo", "v-oem", "kernel", "root", "data", "ad"):
        p_rep.add_argument(f"--{name}", type=Path)
    p_rep.add_argument("--pad", type=lambda x: int(x, 0), default=0xFF)
    p_rep.add_argument("--set-total", action="append", default=[],
                       metavar="NAME=SIZE",
                       help="change a partition total size (KERNEL/ROOT/DATA/AD only)")
    p_rep.add_argument("--auto-data", action="store_true",
                       help="grow/shrink DATA to fill the rest of the 8 MiB flash")
    p_rep.add_argument("--truncate", type=lambda x: int(x, 0), default=None,
                       metavar="SIZE",
                       help="write only the first SIZE bytes (e.g. 0x7f0000 for the stock dump format)")
    p_rep.add_argument("--recovery-copy", action="store_true",
                       help="also write recovery.rcv next to the output")

    args = ap.parse_args()
    data = args.image.read_bytes()

    if args.cmd == "info":
        info(data)
        return 0

    if len(data) != 0x800000:
        raise SystemExit(f"expected an 8 MiB image, got {len(data)} bytes")

    mapping = {
        "LOGO": args.logo,
        "V_OEM": args.v_oem,
        "KERNEL": args.kernel,
        "ROOT": args.root,
        "DATA": args.data,
        "AD": args.ad,
    }
    replacements = {}
    for name, path in mapping.items():
        if path is None:
            continue
        replacements[name] = path.read_bytes()
        print(f"replacing {name} with {path} ({path.stat().st_size} bytes)")

    totals = {}
    for item in args.set_total:
        if "=" not in item:
            raise SystemExit(f"--set-total expects NAME=SIZE, got {item!r}")
        name, value = item.split("=", 1)
        totals[name.upper()] = int(value, 0)

    if not replacements and not totals and not args.auto_data:
        raise SystemExit("no partitions selected")

    image = build_with_layout(data, replacements, totals, args.auto_data, args.pad)
    bad = [name for name, ok, _ in verify(image) if not ok]
    if bad:
        raise SystemExit(f"CRC verification failed: {bad}")
    output = bytes(image)
    if args.truncate is not None:
        if not 0 < args.truncate <= len(output):
            raise SystemExit(f"invalid --truncate size {args.truncate:#x}")
        output = output[:args.truncate]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(f"wrote {args.output} ({len(output)} bytes)")
    print(f"sha256 {hashlib.sha256(output).hexdigest()}")
    if args.recovery_copy:
        rec = args.output.with_name("recovery.rcv")
        rec.write_bytes(output)
        print(f"wrote {rec} (rename/copy to the USB root as recovery.rcv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
