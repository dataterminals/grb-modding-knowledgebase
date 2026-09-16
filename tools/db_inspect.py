#!/usr/bin/env python3
"""
db_inspect.py - list and extract the gameplay records inside GRB's DBContainer.

GRB keeps almost all of its *gameplay tuning* - AI perception, fighting
behaviour, NPC health, reinforcement waves, loot, economy - as tens of thousands
of small named records inside ONE forge entry:

    DataPC.forge / <N>_-_DBContainerEntry_0X104634F921.data      (61,426 records)
    DataPC_patch_01.forge / <N>_-_DBContainerEntry_0X104634F921.data

The records are simply that container's resources - the same framing as any
`.data`, walked by `data_inspect.walk()`. This tool adds what a database needs on
top: name filters, per-type statistics, extraction, and a field diff.

    python db_inspect.py <DBContainerEntry...data>                    # summary
    python db_inspect.py <...data> --grep '^DBSoldierSoundDetection'  # list
    python db_inspect.py <...data> --grep '^DBNpcHealth' --out DIR    # extract
    python db_inspect.py --diff a.bin b.bin                           # compare

⚠️ READ-ONLY on the game. It only ever writes the `--out` directory you name;
point that somewhere that is NOT your install.

HOW IT WORKS
 1. The `.data` is an ordinary GRB container - two `CompressedFileData` blocks,
    Oodle Mermaid - and its records are that container's resources. Decoding and
    walking both come from `data_inspect.py`, so the Oodle DLL search and the
    container format live in exactly one place.
 2. Each record is framed

        [uint32 typeId][int32 payloadLen][int32 nameLen][name][FileHeader][payload]

    The FileHeader is counted by neither length: one 0x00 byte, or 12*n+8 bytes
    when it starts 0x01 (17 records in this container do). Some records have no
    name at all. Handling both, the walk reads all 61,426 records of the base
    container and lands exactly on the end of the block.
    ⚠️ Before 2026-09-16 this tool stopped at the first unnamed record and
    reported 50,098 - a prefix covering 16.5 MB of the 56.8 MB block.
 3. Record 0 is a `DBContainerEntry` resource (776 KB); the rest are the
    database proper.
 4. `typeId` is the schema, the *name* is the instance - e.g. every
    `DBNpcHealth_*` record carries typeId 0xefb394e7 and is exactly 408 B.
    Several type ids are shared by more than one name prefix (the four
    `DB*StrafeBehaviour` / `DB*FightingBehaviour` families pair up this way), so
    trust the id for layout and the name for meaning.

WHY FIXED SIZES MATTER: 775 of the 1,008 DB types have a single record size
across every instance. Two records of one type are therefore field-aligned, so
`--diff` shows you the schema without a schema: diff a live variant against the
game's own "off" variant (`_NoDetection`, `_NoCall`, `_NoConfidence`) and the
differing offsets ARE the tunable fields. ATK cannot help here - it ships no
`DB*` classes at all, so there is no XML round-trip for these records.

Verified 2026-09-16 against the 1.4 TU base container on this machine; the
Fear the Radio mod's own unpacked records byte-match the records this walker
extracts. See `docs/14-ai-and-npc-behaviour.md` and `meta/research-log.md`.
"""
import sys, os, re, struct, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_inspect as di


def records(path, oodle=None, oodle_dll=None):
    """Yield (name, typeId, payload, offset) for every record in a DBContainer.

    `oodle_dll` names the game's `oo2core_7_win64.dll` explicitly - needed when
    the `.data` has been copied out of the install, since the auto-search walks
    up from the file's own path."""
    if oodle is None:
        oodle = di.Oodle(di.find_oodle(path, oodle_dll))
    _meta, files = di.read_container(path, oodle)
    res, end = di.walk(files)
    if end != len(files):
        print(f"  !! {os.path.basename(path)}: walk stopped at byte {end:,} of "
              f"{len(files):,} - every count below is INCOMPLETE", file=sys.stderr)
    for r in res:
        yield r.name, r.type_id, r.payload, r.offset


def summarize(path, oodle_dll=None):
    total, db = 0, 0
    types = collections.defaultdict(lambda: {"n": 0, "sizes": set(), "tid": None})
    tid_names = collections.defaultdict(set)
    for name, tid, payload, _ in records(path, oodle_dll=oodle_dll):
        total += 1
        m = re.match(r"^(DB[A-Za-z0-9]+)", name)
        if not m:
            continue                      # GR_*/TGT_*/WaveSetting_* live here too
        db += 1
        d = types[m.group(1)]
        d["n"] += 1
        d["sizes"].add(len(payload))
        d["tid"] = tid
        tid_names[tid].add(m.group(1))
    fixed = sum(1 for d in types.values() if len(d["sizes"]) == 1)
    shared = sum(1 for v in tid_names.values() if len(v) > 1)
    print(f"{os.path.basename(path)}: {total:,} records "
          f"({db:,} DB*-named, {total - db:,} other)")
    print(f"  {len(types):,} distinct DB types over {len(tid_names):,} type ids "
          f"({shared} ids shared by more than one name prefix)")
    print(f"  {fixed:,} of {len(types):,} DB types have a single fixed record "
          f"size (field-aligned -> --diff is meaningful)")
    return types


def is_float(f):
    return f == f and abs(f) != float("inf") and (f == 0 or 0.001 <= abs(f) <= 20000)


def diff(pa, pb):
    a, b = open(pa, "rb").read(), open(pb, "rb").read()
    print(f"{os.path.basename(pa)}  vs  {os.path.basename(pb)}   "
          f"({len(a)} B / {len(b)} B)")
    if len(a) != len(b):
        print("  !! different sizes - not the same type, or a variable-size type")
        return
    raw = sum(1 for x, y in zip(a, b) if x != y)
    print(f"  {raw} differing bytes (the first 8 are the record's own ClassID)")
    hits, last = [], -9
    for o in range(len(a) - 3):
        if a[o:o + 4] == b[o:o + 4]:
            continue
        fa, = struct.unpack_from("<f", a, o)
        fb, = struct.unpack_from("<f", b, o)
        if is_float(fa) and is_float(fb) and fa != fb and o - last >= 4:
            hits.append((o, fa, fb)); last = o
    for o, fa, fb in hits:
        print(f"    @{o:<5} {fa:>12.4g}   ->  {fb:>12.4g}")
    print(f"    ({len(hits)} differing float-plausible fields)")


def main(argv):
    if "--diff" in argv:
        k = argv.index("--diff")
        return diff(argv[k + 1], argv[k + 2])
    paths, pat, out, dll, i = [], None, None, None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--grep":
            pat = argv[i + 1]; i += 2
        elif a == "--out":
            out = argv[i + 1]; i += 2
        elif a == "--oodle":
            dll = argv[i + 1]; i += 2
        elif a.startswith("--"):
            return print(f"  ! unknown flag {a}") or 2
        else:
            paths.append(a); i += 1
    if not paths:
        print("usage: db_inspect.py <DBContainerEntry...data> [--grep REGEX] [--out DIR] [--oodle DLL]\n"
              "       db_inspect.py --diff a.bin b.bin\n\n"
              "  The container lives at <install>/Extracted/DataPC[_patch_01].forge/\n"
              "  <N>_-_DBContainerEntry_0X104634F921.data - unpack the forge in ATK first.")
        return 2
    if out:
        os.makedirs(out, exist_ok=True)
    for p in paths:
        if not pat:
            summarize(p, oodle_dll=dll)
            continue
        n = m = 0
        for name, tid, payload, off in records(p, oodle_dll=dll):
            n += 1
            if re.search(pat, name):
                m += 1
                print(f"{name}\ttypeId=0x{tid:08x}\t{len(payload)} B")
                if out:
                    fname = name or f"_unnamed_at_{off}"     # some records carry no name
                    with open(os.path.join(out, fname + ".bin"), "wb") as fh:
                        fh.write(payload)
        print(f"-- {m:,} of {n:,} records matched {pat!r}"
              + (f", written to {out}" if out and m else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except EnvironmentError as e:
        raise SystemExit(f"  ! {e}")
