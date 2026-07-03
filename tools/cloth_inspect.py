#!/usr/bin/env python3
"""
cloth_inspect.py - tell a modder, in plain language, what a GRB cloth file is.

It reads a GRB cloth resource and reports: how many cloth pieces (LODs) it has,
which mesh + LOD each is bound to (the Sim_<Mesh>_LOD<n> body name), and how big the
simulated "cage" mesh is.

Reskin reality check: the VISIBLE garment is a SEPARATE, larger, skeleton-skinned mesh
that follows the low-res sim cage via a stored wrap. That wrap is decoded on paper but
NOT yet validated in-game, so rebinding a brand-new visible mesh is unsolved for GRB.
What works today: reshape the vanilla garment while keeping the sim cage's points in the
same order (constraints are addressed by cage-vertex index).

    python cloth_inspect.py  yourcloth.Cloth          # or a cloth .data
    python cloth_inspect.py  clothA.Cloth  clothB.Cloth   # compare two

Prefer the friendly window: run cloth_inspect_gui.py (or the "Cloth Inspector
(GUI).bat" launcher). See tools/README.md.

Accuracy: this now uses the exact MotionCloth reader (motioncloth.py) - it walks
each section by its real size, so counts are correct (the old magic-scan was
approximate). It reads both the decompressed `*.Cloth` file ATK produces AND a
cloth `.data` directly (auto-decompressing with the game's Oodle DLL). Read-only.
See docs/11-cloth-and-physics.md.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motioncloth as mc


def _clean_name(n):
    if not n:
        return "(unnamed)"
    m = re.match(r"(.*?_LOD\d+)", n)   # trim the trailing _0x<hash>_<i>
    return m.group(1) if m else n


def _purpose(name):
    n = (name or "").lower()
    if "_cin" in n or "cinematic" in n or "tpri" in n:
        return "cinematic / cutscene cloth"
    if n.startswith("sim_tp") or "_tp_" in n or n.startswith("sim_ftp"):
        return "gameplay / wearable cloth"
    return ""


def _describe_body(body, lod_index):
    L = []
    raw = mc.body_name(body)
    name = _clean_name(raw)
    purpose = _purpose(raw)
    sv = mc.sim_vertex_count(body)
    tr = mc.sim_triangle_count(body)
    tag = f"   [{purpose}]" if purpose else ""
    L.append(f"  - LOD{lod_index}: {name}{tag}")
    L.append(f"      simulation cage: {sv} points, {tr} triangles")
    if mc.uses_barycentric(body):
        L.append("      (+ 'additional-vertices' sections 4561-4565: a small per-triangle")
        L.append("       point set, likely collision - NOT the visible-mesh binding.)")
    return L


def report(path):
    """Human-readable single-file report as a string (used by the GUI too)."""
    try:
        payload = mc.load_resource_payload(path)
        pkgs = mc.locate_clothpackages(payload)
    except Exception as e:
        return f"Could not read:\n  {path}\n  {e}\n"
    L = ["=" * 70, f"FILE: {os.path.basename(path)}"]
    if not pkgs:
        L += ["  No cloth data found here.",
              "  Is this a GRB cloth resource? (a *.Cloth file from unpacking a cloth",
              "  .data in ATK, or a cloth .data named like *_Cloth / Cloth_*.)"]
        return "\n".join(L) + "\n"
    total_bodies = sum(len(p.bodies) for p in pkgs)
    L.append(f"  {len(pkgs)} cloth LOD(s), {total_bodies} simulated piece(s).")
    L.append("")
    L.append("  A piece named  Sim_<TargetMesh>_LOD<n>  is bound to that exact mesh + LOD -")
    L.append("  match your mod to it (e.g. Sim_TP_... is the wearable one, not a cutscene).")
    for i, pkg in enumerate(pkgs):
        for body in pkg.bodies:
            L.append("")
            L += _describe_body(body, i)
    L.append("")
    L.append("  Reskin note: the sizes above are the low-res SIMULATION CAGE. The visible")
    L.append("  garment is a separate, larger, skeleton-skinned mesh that follows the cage")
    L.append("  via a stored wrap (decoded on paper, NOT yet validated in-game). Rebinding a")
    L.append("  brand-new mesh is unsolved for GRB; reshaping the vanilla garment while")
    L.append("  keeping the cage's points in the same order is the route that works today.")
    return "\n".join(L) + "\n"


def _fingerprint(path):
    payload = mc.load_resource_payload(path)
    pkgs = mc.locate_clothpackages(payload)
    rows = []
    for i, pkg in enumerate(pkgs):
        for body in pkg.bodies:
            rows.append((i, _clean_name(mc.body_name(body)), mc.sim_vertex_count(body),
                         mc.sim_triangle_count(body),
                         "yes" if mc.uses_barycentric(body) else "no"))
    return rows


def diff(path_a, path_b):
    """Report both files plus a compact side-by-side of their cloth pieces."""
    out = [report(path_a), report(path_b)]
    try:
        ra, rb = _fingerprint(path_a), _fingerprint(path_b)
    except Exception as e:
        return "\n".join(out) + f"\n(comparison skipped: {e})\n"
    out.append("=" * 70)
    out.append("SIDE-BY-SIDE  (A = first file, B = second)")
    out.append(f"  A = {os.path.basename(path_a)}   pieces: {len(ra)}")
    out.append(f"  B = {os.path.basename(path_b)}   pieces: {len(rb)}")
    out.append("")
    out.append("  (addl-verts = has sections 4561-4565, a small per-triangle collision-ish")
    out.append("   point set - NOT the visible-mesh binding. 'cage pts' = sim-cage vertices.)")
    out.append(f"  {'piece':40} {'cage pts':>8} {'tris':>6} {'addl-verts':>10}")
    out.append(f"  {'-'*40} {'-'*8} {'-'*6} {'-'*10}")
    for tag, rows in (("A", ra), ("B", rb)):
        for (i, nm, sv, tr, att) in rows:
            out.append(f"  {tag}: {nm[:36]:37} {sv:>8} {tr:>6} {att:>10}")
    return "\n".join(out) + "\n"


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(argv) == 2:
        print(report(argv[1]))
    elif len(argv) >= 3:
        print(diff(argv[1], argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
