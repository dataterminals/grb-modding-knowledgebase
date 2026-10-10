#!/usr/bin/env python3
"""
id_census.py - every resource ClassID in an Anvil install, and the IDs two installs
share, classified by whether they name the same object. Read-only on the forges.

    python id_census.py scan     <install dir> <out dir> [--skip-dir Extracted]
    python id_census.py classify <grw scan dir> <grb scan dir> <grw install> <grb install> <out dir>

Wildlands containers are LZO: set GRB_ATK to the ATK folder (for Libs/lzo.dll),
as for data_inspect.py. Breakpoint's Oodle DLL is found in the install.

`scan` reads only each container's metadata block, a few KB per forge entry, so
it is fast even on a spinning disk. On 2026-10-10 it took 42 s for Breakpoint and
5 min for Wildlands (HDD). It writes `rows.bin` (u64 id, u32 entry#) and
`entries.tsv` (entry#, forge, category, entry id, type, name, offset, length).

`classify` intersects the two ID sets. For each shared ID it walks one container
per side (patch > base > DLC/backup/other) to read the resource's type and name,
and writes `classified.tsv`:
  a   same type and name          (the same object: reuse GRB's, or ship ours)
  b1  same type, different name   (a different object now: re-ID ours)
  b2  different type              (re-ID ours; on 2026-10-10 all were same-name
                                   schema changes)
IDs only one install has are free (class c) and are not listed.
Re-IDing is done by grw_reid.py. Results and provenance: meta/notes-id-collisions.md.

CONTAINER METADATA BLOCK (verified against full walks of 390 containers in both
games): `u16 n`, then n x (`u64 ClassID | u32 size | u16 k | k x u16`), in the
same order as the resources in the files block. A forge entry's own ID is
always one of its container's resource IDs.
"""
import collections
import ctypes
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_inspect as di            # noqa: E402
import forge_inspect as fi           # noqa: E402

ROW = None                           # numpy dtype, set on first use


def memory_cap(mb):
    """Windows Job Object cap on this process (a runaway allocation fails instead of swapping)."""
    if os.name != "nt":
        return
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)

    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("a", "b", "c", "d", "e", "f")]

    class Basic(ctypes.Structure):
        _fields_ = [("t1", ctypes.c_longlong), ("t2", ctypes.c_longlong), ("flags", wintypes.DWORD),
                    ("mn", ctypes.c_size_t), ("mx", ctypes.c_size_t), ("apl", wintypes.DWORD),
                    ("aff", ctypes.c_size_t), ("pc", wintypes.DWORD), ("sc", wintypes.DWORD)]

    class Ext(ctypes.Structure):
        _fields_ = [("b", Basic), ("io", IO), ("pml", ctypes.c_size_t), ("jml", ctypes.c_size_t),
                    ("p1", ctypes.c_size_t), ("p2", ctypes.c_size_t)]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    job = k.CreateJobObjectW(None, None)
    info = Ext(); info.b.flags = 0x100; info.pml = mb << 20
    k.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(k.GetCurrentProcess()))
    memory_cap.job = job


def _np():
    global ROW
    import numpy as np
    if ROW is None:
        ROW = np.dtype([("id", "<u8"), ("e", "<u4")])
    return np


def meta_ids(meta):
    n = struct.unpack_from("<H", meta, 0)[0]
    o, out = 2, []
    for _ in range(n):
        cid, size, k = struct.unpack_from("<QIH", meta, o)
        o += 14 + 2 * k
        out.append(cid)
    if o != len(meta):
        raise ValueError(f"metadata block: parsed {o} of {len(meta)} bytes")
    return out


def read_meta(f, off, length, oodle):
    """The resource IDs of the container at `off`, reading only its metadata block."""
    f.seek(off)
    h = f.read(19)
    if len(h) < 19 or struct.unpack_from("<Q", h, 0)[0] != di.MAGIC:
        return None
    ver = struct.unpack_from("<h", h, 8)[0]
    n = struct.unpack_from("<i", h, 15)[0]
    if not 0 <= n <= 100000:
        return None
    fmt = "<HH" if ver == 1 else "<ii"
    w = struct.calcsize(fmt)
    infos = f.read(w * n)
    total = 19 + w * n + 4 * n + sum(struct.unpack_from(fmt, infos, w * k)[1] for k in range(n))
    if total > length:
        return None
    f.seek(off)
    meta, _, _ = di.read_cfd(f.read(total), 0, oodle)
    return meta_ids(meta)


def category(rel):
    r, b = rel.lower(), os.path.basename(rel).lower()
    if r.startswith("backups"):
        return "backup"
    if "grn_worldmap" in b or "tgt_worldmap" in b:
        return "dlc_world" if "dlc" in b else "world"
    if "ghostroom" in b or "titlescreen" in b:
        return "other"
    return "dlc_global" if "dlc" in b else "global"


def scan(install, out, skip_dirs=("extracted",)):
    os.makedirs(out, exist_ok=True)
    oodle = di.Oodle(di.find_oodle(os.path.join(install, "x")))
    forges = []
    for dp, _, fn in os.walk(install):
        rel = os.path.relpath(dp, install).lower()
        if any(rel.startswith(s.lower()) for s in skip_dirs):
            continue
        forges += [os.path.join(dp, f) for f in fn if f.lower().endswith(".forge")]
    eidx = 0
    with open(os.path.join(out, "rows.bin"), "wb") as rows, \
            open(os.path.join(out, "entries.tsv"), "w", encoding="utf-8") as ent:
        for p in sorted(forges):
            rel = os.path.relpath(p, install)
            cat, stats = category(rel), collections.Counter()
            buf = bytearray()
            with open(p, "rb", buffering=0) as f:
                for fid, ext, name, off, ln in sorted(fi.forge_entries(p), key=lambda e: e[3]):
                    ent.write(f"{eidx}\t{rel}\t{cat}\t{fid}\t{ext}\t{name}\t{off}\t{ln}\n")
                    try:
                        ids = read_meta(f, off, ln, oodle)
                    except Exception:
                        ids, stats["errors"] = None, stats["errors"] + 1
                    for cid in (ids if ids is not None else [fid]):
                        buf += struct.pack("<QI", cid, eidx)
                    stats["entries"] += 1
                    stats["resources"] += len(ids) if ids else 0
                    eidx += 1
            rows.write(buf)
            print(f"{rel} [{cat}] {dict(stats)}", flush=True)


def _rank(rel, cat):
    return (0 if "patch_01" in rel.lower() else 1) + (2 if cat in ("backup", "dlc_world", "dlc_global", "other") else 0)


def _types_names(scan_dir, install, wanted):
    """id -> (type id, name, forge), walking one container per wanted id."""
    np = _np()
    rows = np.fromfile(os.path.join(scan_dir, "rows.bin"), dtype=ROW)
    hit = rows[np.isin(rows["id"], wanted)]
    del rows
    ent, rank = {}, np.full(int(hit["e"].max()) + 1, 9, np.uint8)
    with open(os.path.join(scan_dir, "entries.tsv"), encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            k = int(p[0])
            if k < len(rank):
                rank[k] = _rank(p[1], p[2])
                ent[k] = (p[1], int(p[6]), int(p[7]), int(p[3]), p[4], p[5])
    h = hit[np.lexsort((rank[hit["e"]], hit["id"]))]
    first = np.ones(len(h), bool)
    first[1:] = h["id"][1:] != h["id"][:-1]
    need = sorted({int(k) for k in h["e"][first]}, key=lambda k: (ent[k][0], ent[k][1]))
    oodle = di.Oodle(di.find_oodle(os.path.join(install, "x")))
    want, out, cur, f, fresh = set(int(x) for x in wanted), {}, None, None, {}

    def read(off, ln):
        f.seek(off)
        return di.read_container_bytes(f.read(ln), oodle)[1]

    for k in need:
        forge, off, ln, fid, ext, name = ent[k]
        if forge != cur:
            f and f.close()
            f, cur = open(os.path.join(install, forge), "rb"), forge
        try:
            files = read(off, ln)
        except Exception:
            files = None
            # The forge may have been repacked since the scan (a live install):
            # look the entry up in the forge's current index and retry once.
            if forge not in fresh:
                fresh[forge] = {e[0]: (e[3], e[4]) for e in fi.forge_entries(os.path.join(install, forge))}
            if fid in fresh[forge] and fresh[forge][fid] != (off, ln):
                try:
                    files = read(*fresh[forge][fid])
                except Exception:
                    files = None
        if files is None:
            # not a container (GlobalMetaFile, prefetch table, compiled shaders):
            # the forge entry's own type and name stand in for the resource's
            if fid in want and fid not in out:
                out[fid] = (int(ext) if str(ext).isdigit() else f"entry:{ext}", name, forge)
            continue
        for r in di.walk(files)[0]:
            cid = di.class_id(r)
            if cid in want and cid not in out:
                out[cid] = (r.type_id, r.name, forge)
    f and f.close()
    return out


def classify(grw_scan, grb_scan, grw_install, grb_install, out):
    np = _np()
    os.makedirs(out, exist_ok=True)
    w = np.unique(np.fromfile(os.path.join(grw_scan, "rows.bin"), dtype=ROW)["id"])
    b = np.unique(np.fromfile(os.path.join(grb_scan, "rows.bin"), dtype=ROW)["id"])
    shared = np.intersect1d(w, b, assume_unique=True)
    print(f"GRW {len(w):,} ids, GRB {len(b):,} ids, shared {len(shared):,}", flush=True)
    W = _types_names(grw_scan, grw_install, shared)
    B = _types_names(grb_scan, grb_install, shared)
    counts = collections.Counter()
    with open(os.path.join(out, "classified.tsv"), "w", encoding="utf-8", newline="") as fo:
        cw = csv.writer(fo, delimiter="\t", lineterminator="\n")
        cw.writerow(["id", "class", "grw_type", "grw_name", "grb_type", "grb_name", "grw_forge", "grb_forge"])
        for i in shared.tolist():
            if i not in W or i not in B:
                counts["unreadable"] += 1
                continue
            (tw, nw, fw), (tb, nb, fb) = W[i], B[i]
            c = "a" if (tw, nw) == (tb, nb) else ("b1" if tw == tb else "b2")
            counts[c] += 1
            label = lambda t: t if isinstance(t, str) else di.type_name(t)
            cw.writerow([i, c, label(tw), nw, label(tb), nb, fw, fb])
    print(dict(counts))


def main(argv):
    memory_cap(1400)
    if len(argv) >= 3 and argv[0] == "scan":
        skip = ("extracted",)
        if "--skip-dir" in argv:
            skip = (argv[argv.index("--skip-dir") + 1],)
        scan(argv[1], argv[2], skip)
    elif len(argv) == 6 and argv[0] == "classify":
        classify(*argv[1:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
