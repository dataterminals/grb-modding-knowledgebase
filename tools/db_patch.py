#!/usr/bin/env python3
"""
db_patch.py - make one checked edit to a GRB gameplay DB record, and know exactly
what an ATK repack of the DB container will change before and after you run it.

    python db_patch.py <unpack folder> --sync <container.data | forge>      # 1. is the folder safe to repack?
    python db_patch.py <unpack folder> --record SC_TGT_Rifleman_Marks1      # 2. what does this record point at?
    python db_patch.py <unpack folder> --record SC_TGT_Rifleman_Marks1 \\
        --repoint DBAICheatConfig_NoCheat=DBAICheatConfig_Miter_Omniscience --out DIR   # 3. make the edit
    python db_patch.py --compare <old .data | forge> <new .data | forge>    # 4. what did the repack change?

The unpack folder is ATK's, e.g.
    <install>\\Extracted\\DataPC_patch_01.forge\\Extracted\\1_-_DBContainerEntry_0X104634F921.data\\
A `.forge` argument means the DB container entry inside that forge (`--entry` to
name another), so step 1 can be checked against what the game loads today.

⚠️ READ-ONLY on the game. It writes only into `--out`; placing the file, and both
repacks, stay with you and ATK.

WHY EACH STEP EXISTS
 1. --sync. ATK rebuilds a container from its unpack folder, not from the
    container. If anything wrote the container since the folder was unpacked
    (the GRB Mod Manager writes containers directly), a repack silently reverts
    it. This replays ATK 1.3.1's `DataFile.Serialize` selection on the folder -
    GetFiles order, stable sort by the number before `_-_`, first file per
    ClassID wins, name taken from the filename, ignored extensions skipped - and
    compares every record with the container. "IN SYNC" means a repack of the
    untouched folder reproduces it byte for byte.
 2. --record NAME alone lists every handle in the record that resolves, by
    offset. A handle is the target's ClassID (docs/14 §5), so no schema is needed.
 3. --repoint OLD=NEW swaps one handle. Refused unless OLD occurs exactly once in
    the record, NEW names exactly one packed record (or is given as 0x…), and NEW
    has the same type id as OLD - so a cheat slot can only get a cheat config. The
    output is `1_-_<name>.<type>`, which ATK packs ahead of the vanilla copy; it
    is refused if another file for the same ClassID would still win.
 4. --compare lists records added, removed and changed between two containers,
    with the differing offsets. After the container repack, compare the old and
    new `.data`: one changed record, at most eight bytes, is a clean edit. After the forge
    repack, compare the forge with the `.data`: identical means it landed.

Verified 2026-09-23 on this install: --sync reproduces all 61,446 live records
(bytes, names, types, headers and order) from a 61,820-file folder. See
docs/14-ai-and-npc-behaviour.md §6 and meta/research-log.md.
"""
import sys, os, re, struct, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_inspect as di

DB_ENTRY = "DBContainerEntry_0X104634F921"
# ATK 1.3.1's shipped IgnoredExtensions setting (AnvilToolkit.dll.config); it
# replaces the hardcoded list in DataStorage, so this is what a repack skips.
IGNORED = {".dependency", ".bak", ".dds", ".obj", ".glb", ".xml", ".ignored"}

Pick = collections.namedtuple("Pick", "file number type_id name header payload")


def _long(p):
    """Record names run past MAX_PATH; open them the way .NET does."""
    p = os.path.abspath(p)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p


def _number(fname):
    m = re.match(r"^(\d+)_-_", fname)
    return int(m.group(1)) if m else 0


def atk_selection(folder):
    """What ATK's container repack would pack from `folder`, in packing order.

    Returns (picked, files): picked maps ClassID -> Pick for the winning file;
    files is every candidate as (fname, number, ClassID)."""
    names = [n for n in os.listdir(folder)
             if os.path.splitext(n)[1].lower() not in IGNORED
             and os.path.isfile(_long(os.path.join(folder, n)))]
    names.sort(key=_number)                  # stable, like LINQ OrderBy
    picked, files = {}, []
    for n in names:
        b = open(_long(os.path.join(folder, n)), "rb").read()
        h = di.header_len(b, 0)
        cid, tid = struct.unpack_from("<QI", b, h)
        files.append((n, _number(n), cid))
        if cid in picked:
            continue
        stem = os.path.splitext(n)[0].split("_-_", 1)[-1]
        picked[cid] = Pick(n, _number(n), tid, "" if stem.lower() == "unnamed" else stem,
                           b[:h], b[h:])
    return picked, files


def _forge_entry(path, want):
    """Bytes of the first forge entry whose name contains `want`."""
    with open(path, "rb") as f:
        if f.read(8) != b"scimitar":
            raise SystemExit(f"  ! {path} is not a .forge")
        f.seek(9); f.read(4)
        f.seek(struct.unpack("<Q", f.read(8))[0] + 32)
        count_sets = struct.unpack("<I", f.read(4))[0]
        pos, seen = struct.unpack("<q", f.read(8))[0], 0
        while pos != -1 and seen < count_sets:
            f.seek(pos)
            n = struct.unpack("<I", f.read(4))[0]; f.read(4)
            off_tbl, nxt = struct.unpack("<qq", f.read(16)); f.read(8)
            info_tbl = struct.unpack("<q", f.read(8))[0]
            f.seek(off_tbl); ob = f.read(n * 20)
            f.seek(info_tbl); ib = f.read(n * 192)
            for r in range(n):
                if want in ib[r * 192 + 44:r * 192 + 172].split(b"\0")[0].decode("latin-1"):
                    off, _fid, ln = struct.unpack_from("<qQi", ob, r * 20)
                    f.seek(off)
                    return f.read(ln)
            seen += 1; pos = nxt
    raise SystemExit(f"  ! no entry matching {want!r} in {path}")


def container(path, entry=DB_ENTRY, oodle_dll=None):
    """The records of a container, from a `.data` or from an entry of a `.forge`."""
    raw = _forge_entry(path, entry) if path.lower().endswith(".forge") else open(path, "rb").read()
    oodle = di.Oodle(di.find_oodle(path, oodle_dll))
    _meta, off = di.read_cfd(raw, 0, oodle)[:2]
    files = di.read_cfd(raw, off, oodle)[0]
    res, end = di.walk(files)
    if end != len(files):
        raise SystemExit(f"  ! walk of {os.path.basename(path)} stopped at {end:,} of {len(files):,}")
    return res


def by_cid(res):
    return {di.class_id(r): r for r in res}


def sync(folder, target, entry, oodle_dll):
    picked, files = atk_selection(folder)
    live = container(target, entry, oodle_dll)
    lb = by_cid(live)
    only_f = [c for c in picked if c not in lb]
    only_c = [c for c in lb if c not in picked]
    changed = [c for c, p in picked.items() if c in lb and
               (lb[c].payload, lb[c].name, lb[c].type_id, lb[c].header) !=
               (p.payload, p.name, p.type_id, p.header)]
    order = [di.class_id(r) for r in live] == list(picked)
    print(f"folder   : {len(files):,} files -> ATK would pack {len(picked):,} records "
          f"({len(files) - len(picked):,} lose to a lower-numbered file)")
    print(f"container: {len(live):,} records  ({os.path.basename(target)})")
    print(f"  only in folder {len(only_f)} | only in container {len(only_c)} | "
          f"differ {len(changed)} | order identical {order}")
    for label, lst in (("only in folder", only_f), ("only in container", only_c), ("differs", changed)):
        for c in lst[:20]:
            print(f"    {label}: 0x{c:x} {picked[c].file if c in picked else lb[c].name}")
    ok = not (only_f or only_c or changed) and order
    print("IN SYNC - repacking this folder as it stands reproduces the container byte for byte"
          if ok else
          "NOT IN SYNC - a repack would change the records above; find out why before adding anything")
    return 0 if ok else 1


def handles(payload, picked):
    """(offset, ClassID) for every 8-byte window after the record's own id that
    resolves to a packed record."""
    return [(k, h) for k in range(8, len(payload) - 7)
            for h in (struct.unpack_from("<Q", payload, k)[0],) if h in picked]


def resolve(ref, picked):
    """ClassIDs of packed records named `ref`, or `ref` itself when given as 0x...."""
    if ref.lower().startswith("0x"):
        c = int(ref, 16)
        return [c] if c in picked else []
    return [c for c, p in picked.items() if p.name == ref]


def show(folder, record):
    picked, _ = atk_selection(folder)
    cs = resolve(record, picked)
    if len(cs) != 1:
        raise SystemExit(f"  ! {record!r} names {len(cs)} packed records; give its ClassID as 0x...")
    p = picked[cs[0]]
    print(f"{p.name}  0x{cs[0]:x}  type 0x{p.type_id:08x}  {len(p.payload)} B  <- {p.file}")
    for k, h in handles(p.payload, picked):
        q = picked[h]
        print(f"  @{k:<5} 0x{h:x}  {q.name}  (type 0x{q.type_id:08x})")


def repoint(folder, record, old, new, out, number):
    picked, files = atk_selection(folder)
    cs = resolve(record, picked)
    if len(cs) != 1:
        raise SystemExit(f"  ! {record!r} names {len(cs)} packed records; give its ClassID as 0x...")
    cid, p = cs[0], picked[cs[0]]
    hits = [(k, h) for k, h in handles(p.payload, picked)
            if (h == int(old, 16) if old.lower().startswith("0x") else picked[h].name == old)]
    if len(hits) != 1:
        raise SystemExit(f"  ! {old!r} occurs {len(hits)} times in {p.name}; need exactly one")
    at, h_old = hits[0]
    ns = resolve(new, picked)
    if len(ns) != 1:
        raise SystemExit(f"  ! {new!r} names {len(ns)} packed records; give its ClassID as 0x...")
    h_new = ns[0]
    if picked[h_new].type_id != picked[h_old].type_id:
        raise SystemExit(f"  ! type mismatch: {picked[h_old].name} is 0x{picked[h_old].type_id:08x}, "
                         f"{picked[h_new].name} is 0x{picked[h_new].type_id:08x}")
    body = bytearray(p.payload)
    struct.pack_into("<Q", body, at, h_new)
    changed = sum(1 for a, b in zip(p.payload, body) if a != b)
    assert len(body) == len(p.payload) and changed <= 8 and body[:8] == p.payload[:8]

    fname = f"{number}_-_" + p.file.split("_-_", 1)[1]
    rivals = [(n, num) for n, num, c in files if c == cid and n != fname and num <= number]
    if rivals:
        raise SystemExit(f"  ! {rivals[0][0]} carries the same ClassID at number {rivals[0][1]} and "
                         f"would still be packed instead; use --number {min(r[1] for r in rivals) - 1}"
                         if min(r[1] for r in rivals) > 0 else
                         f"  ! {rivals[0][0]} carries the same ClassID at number 0; edit that file instead")
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, fname)
    with open(_long(dst), "wb") as fh:
        fh.write(p.header + bytes(body))
    print(f"{p.name}  0x{cid:x}  ({p.file})")
    print(f"  @{at}: 0x{h_old:x} {picked[h_old].name}  ->  0x{h_new:x} {picked[h_new].name}")
    print(f"  {changed} byte(s) changed of {len(body)}; size, ClassID and type unchanged")
    print(f"  wrote {dst}")
    print(f"  drop it into {folder}\n  beside {p.file}; ATK will pack it and skip the original.")
    if fname in os.listdir(folder):
        print(f"  !! {fname} already exists there - copying over it replaces that file; back it up first")
    return 0


def compare(a, b, entry, oodle_dll):
    ra, rb = by_cid(container(a, entry, oodle_dll)), by_cid(container(b, entry, oodle_dll))
    added = [c for c in rb if c not in ra]
    removed = [c for c in ra if c not in rb]
    changed = [c for c in rb if c in ra and (ra[c].payload, ra[c].name, ra[c].type_id, ra[c].header)
               != (rb[c].payload, rb[c].name, rb[c].type_id, rb[c].header)]
    body = sum(1 for c in changed if ra[c].payload != rb[c].payload)
    print(f"{os.path.basename(a)}: {len(ra):,} records   {os.path.basename(b)}: {len(rb):,} records")
    print(f"  identical {len(rb) - len(added) - len(changed):,} | changed {len(changed)} "
          f"({body} in the payload, {len(changed) - body} in name/header only) | "
          f"added {len(added)} | removed {len(removed)}")
    for c in changed[:40]:
        x, y = ra[c].payload, rb[c].payload
        offs = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
        what = (f"{len(offs)} byte(s) at @{offs[0]}..@{offs[-1]}" if offs else "same payload")
        if len(x) != len(y):
            what += f", size {len(x)} -> {len(y)}"
        if ra[c].name != rb[c].name:
            what += f", renamed from {ra[c].name!r}"
        print(f"    changed 0x{c:x} {rb[c].name}: {what}")
    for c in added[:20]:
        print(f"    added   0x{c:x} {rb[c].name}")
    for c in removed[:20]:
        print(f"    removed 0x{c:x} {ra[c].name}")
    return 0


def main(argv):
    sys.stdout.reconfigure(errors="replace")   # the docstring is UTF-8; consoles may not be
    opts, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ("--sync", "--record", "--repoint", "--out", "--entry", "--oodle", "--number"):
            opts[a] = argv[i + 1]; i += 2
        elif a == "--compare":
            opts[a] = (argv[i + 1], argv[i + 2]); i += 3
        elif a in ("-h", "--help"):
            print(__doc__); return 0
        elif a.startswith("--"):
            return print(f"  ! unknown flag {a}") or 2
        else:
            pos.append(a); i += 1
    entry, dll = opts.get("--entry", DB_ENTRY), opts.get("--oodle")
    if "--compare" in opts:
        return compare(*opts["--compare"], entry, dll)
    if not pos or not os.path.isdir(pos[0]):
        print(__doc__.split("The unpack folder")[0].strip())
        return 2
    folder = pos[0]
    if "--sync" in opts:
        return sync(folder, opts["--sync"], entry, dll)
    if "--record" in opts and "--repoint" in opts:
        if "--out" not in opts:
            return print("  ! --repoint needs --out DIR (never your install)") or 2
        old, _, new = opts["--repoint"].partition("=")
        return repoint(folder, opts["--record"], old, new, opts["--out"], int(opts.get("--number", 1)))
    if "--record" in opts:
        return show(folder, opts["--record"])
    print("  ! nothing to do - see --help")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except EnvironmentError as e:
        raise SystemExit(f"  ! {e}")
