#!/usr/bin/env python3
"""Extract the useful pieces of a KOQIT V5H (GX6605H1 / Taurus) flash image.

Tested against firmware/V5H-Intelsat_263_flash.bin (8 MiB full SPI dump).

The image uses the NationalChip GxLoader layout:
  TABLE at 0x20000 (512 bytes, magic aa bc de fa), 24-byte records, BE fields.

Partitions (from the table):
  BOOT   0x000000 - 0x020000  stage-1 + GxLoader/U-Boot stage-2
  TABLE  0x020000 - 0x020200
  LOGO   0x020200 - 0x06f000  JPEG boot logo
  V_OEM  0x06f000 - 0x070000  INI-style OEM/version config
  KERNEL 0x070000 - 0x320000  ROMFS containing ecos.bin.lzma
  ROOT   0x320000 - 0x440000  XZ-compressed UI resources (fonts)
  DATA   0x440000 - 0x7f0000  writable data / user DB (empty here)
  AD     0x7f0000 - 0x800000  advertisement/reserved

This tool is read-only with respect to the input image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import struct
from pathlib import Path

TABLE_MAGIC = bytes.fromhex("aabcdefa")
ROMFS_MAGIC = b"-rom1fs-"
XZ_MAGIC = b"\xfd7zXZ\x00"
SECTOR = 0x10000


def be32(buf: bytes, off: int) -> int:
    return struct.unpack_from(">I", buf, off)[0]


def find_table(data: bytes) -> tuple[int, list[dict]]:
    """Locate and parse the GxLoader partition table."""
    for off in range(SECTOR, 0x100000, SECTOR):
        if data[off:off + 4] != TABLE_MAGIC:
            continue
        count = data[off + 4]
        if not 1 <= count <= 16 or 5 + count * 24 > 512:
            continue
        parts = []
        pos = off + 5
        expect = 0
        for _ in range(count):
            rec = data[pos:pos + 24]
            name = rec[:8].split(b"\0", 1)[0].decode("latin1")
            total = be32(rec, 8)
            used = be32(rec, 12)
            start = be32(rec, 16)
            if start != expect or total == 0:
                break
            parts.append({
                "name": name,
                "start": start,
                "total_size": total,
                "used_size": used,
                "fs_type": rec[20],
                "flags": rec[21],
                "id": rec[22],
            })
            expect += total
            pos += 24
        if len(parts) == count:
            return off, parts
    raise SystemExit("GxLoader TABLE not found (expected magic aabcdefa at a 64 KiB boundary)")


def align16(n: int) -> int:
    return (n + 15) & ~15


def extract_romfs_payload(kernel: bytes, out_dir: Path) -> dict:
    """Find the .lzma member inside the ROMFS and decompress it."""
    base = kernel.find(ROMFS_MAGIC)
    if base < 0:
        raise SystemExit("ROMFS magic not found in KERNEL partition")
    result = {"romfs_offset_in_partition": base, "volume": None, "members": []}

    name_end = kernel.find(b"\0", base + 16)
    result["volume"] = kernel[base + 16:name_end].decode("latin1")

    # Walk the 16-byte inode headers and find the LZMA member. The inode
    # layout here is: next, mode, size(BE), checksum, name, pad to 16.
    for header in range(base + 32, min(len(kernel), base + 0x2000), 16):
        name_start = header + 16
        name_end = kernel.find(b"\0", name_start, name_start + 64)
        if name_end < 0:
            continue
        name = kernel[name_start:name_end].decode("latin1", "replace")
        if not name.endswith(".lzma"):
            continue
        size = be32(kernel, header + 8)
        data_off = align16(name_end + 1)
        if not 0 < size <= len(kernel) - data_off:
            continue
        blob = kernel[data_off:data_off + size]
        member = {
            "name": name,
            "inode_offset_in_partition": header,
            "data_offset_in_partition": data_off,
            "compressed_size": size,
            "sha256_compressed": hashlib.sha256(blob).hexdigest(),
        }
        (out_dir / "ecos.bin.lzma").write_bytes(blob)
        try:
            dec = lzma.decompress(blob, format=lzma.FORMAT_ALONE)
            (out_dir / "ecos.bin").write_bytes(dec)
            member["uncompressed_size"] = len(dec)
            member["sha256_uncompressed"] = hashlib.sha256(dec).hexdigest()
            member["lzma_format"] = "alone"
        except lzma.LZMAError as exc:
            member["lzma_error"] = str(exc)
        result["members"].append(member)
        break
    return result


NON_TTF_MAGIC = (
    b"\xff\xd8",          # JPEG
    b"\x89PNG",           # PNG
    b"BM",                # BMP
    b"<?xml",             # XML UI layout
    b"<widget",           # XML widget
    b"GIF8",              # GIF
    b"RIFF",              # WAV/WebP
)


def extract_root_resources(root: bytes, out_dir: Path) -> dict:
    """Reassemble the ROOT resource store from its 32 KiB XZ chunks.

    ROOT is not a mountable filesystem here. It is a sequence of independent
    XZ streams (mostly 32 KiB uncompressed each) whose concatenation forms the
    UI payload: TTF fonts, BMP/JPEG/PNG images and XML layouts. There is no
    recovered filename index, so this tool preserves the chunk list and the
    reassembled byte stream, and carves the first resource (Arial TTF).
    """
    chunks: list[bytes] = []
    records: list[dict] = []
    pos = 0
    while True:
        hit = root.find(XZ_MAGIC, pos)
        if hit < 0:
            break
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO)
        try:
            out = dec.decompress(root[hit:])
        except lzma.LZMAError:
            pos = hit + len(XZ_MAGIC)
            continue
        consumed = (len(root) - hit) - len(dec.unused_data)
        records.append({
            "index": len(chunks),
            "offset_in_partition": hit,
            "compressed_size": consumed,
            "uncompressed_size": len(out),
            "sha256": hashlib.sha256(out).hexdigest(),
        })
        chunks.append(out)
        pos = hit + consumed

    full = b"".join(chunks)
    (out_dir / "root_resources.bin").write_bytes(full)

    result = {
        "chunk_count": len(chunks),
        "reassembled_size": len(full),
        "reassembled_sha256": hashlib.sha256(full).hexdigest(),
        "chunks": records,
    }

    if chunks and chunks[0][:4] == b"\x00\x01\x00\x00":
        stop = 1
        while stop < len(chunks) and not any(chunks[stop].startswith(m)
                                             for m in NON_TTF_MAGIC):
            stop += 1
        font = b"".join(chunks[:stop])
        (out_dir / "font_arial.ttf").write_bytes(font)
        result["first_resource"] = {
            "name": "font_arial.ttf",
            "chunks": stop,
            "size": len(font),
            "sha256": hashlib.sha256(font).hexdigest(),
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("extracted"))
    args = ap.parse_args()

    data = args.image.read_bytes()
    args.out.mkdir(parents=True, exist_ok=True)

    table_off, parts = find_table(data)
    by_name = {p["name"]: p for p in parts}

    manifest = {
        "source": str(args.image),
        "source_size": len(data),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "table_offset": table_off,
        "partitions": parts,
        "extracted": {},
    }

    def part_data(name: str) -> bytes:
        p = by_name[name]
        return data[p["start"]:p["start"] + p["total_size"]]

    logo = by_name.get("LOGO")
    if logo:
        blob = data[logo["start"]:logo["start"] + logo["used_size"]]
        (args.out / "logo.jpg").write_bytes(blob)
        manifest["extracted"]["logo.jpg"] = {
            "size": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }

    oem = by_name.get("V_OEM")
    if oem:
        blob = part_data("V_OEM")
        (args.out / "V_OEM.ini").write_bytes(blob)
        manifest["extracted"]["V_OEM.ini"] = {
            "size": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }

    if "KERNEL" in by_name:
        manifest["extracted"]["romfs"] = extract_romfs_payload(part_data("KERNEL"), args.out)
        for member in manifest["extracted"]["romfs"]["members"]:
            if "sha256_uncompressed" in member:
                manifest["extracted"]["ecos.bin.lzma"] = {
                    "size": member["compressed_size"],
                    "sha256": member["sha256_compressed"],
                }
                manifest["extracted"]["ecos.bin"] = {
                    "size": member["uncompressed_size"],
                    "sha256": member["sha256_uncompressed"],
                }

    if "ROOT" in by_name:
        manifest["extracted"]["root_resources"] = extract_root_resources(part_data("ROOT"), args.out)

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"table @ {table_off:#x}, {len(parts)} partitions")
    for p in parts:
        print(f"  {p['name']:8} {p['start']:#08x}-{p['start'] + p['total_size']:#08x} "
              f"used={p['used_size']:#x} fs={p['fs_type']}")
    print(f"wrote {args.out}/ (manifest.json has hashes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
