#!/usr/bin/env python3
"""
grbblend.py - drive Blender from the command line, for GRB modding.

Blender ships its own Python and can run with no window at all, so anything you
can do by clicking in Blender can also be done from a terminal - or by an AI
assistant working alongside you. That is what this is: the host half of a bridge
whose other half (`_inside.py`) runs inside Blender.

    python grbblend.py doctor
    python grbblend.py selftest
    python grbblend.py inspect Coat_LOD0.glb
    python grbblend.py transfer-weights --source Coat.glb --target Poncho.glb --out Bound.glb
    python grbblend.py run --code "result = describe_scene()" --file Coat.glb

Finding Blender: pass --blender, or set GRB_BLENDER, or let it search the usual
Steam and Program Files locations.

Nothing here reads or writes your GRB install. The game-file side of the
pipeline is still ATK's job - see ../README.md and ../../docs/07-modding-workflow.md.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSIDE = os.path.join(HERE, "_inside.py")

BEGIN = "<<<GRBBLEND-JSON"
END = "GRBBLEND-JSON>>>"


# --------------------------------------------------------------------------
# finding Blender
# --------------------------------------------------------------------------

def candidate_blenders():
    """Every place Blender plausibly lives on this machine, best guess first."""
    seen, out = set(), []

    def add(path):
        if path and path not in seen and os.path.isfile(path):
            seen.add(path)
            out.append(path)

    add(os.environ.get("GRB_BLENDER"))
    add(shutil.which("blender"))
    add(shutil.which("blender.exe"))

    if os.name == "nt":
        roots = []
        # Steam, on every drive letter that exists.
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            base = "%s:\\" % drive
            if not os.path.isdir(base):
                continue
            roots.append(os.path.join(base, "SteamLibrary", "steamapps",
                                      "common", "Blender"))
            roots.append(os.path.join(base, "Program Files", "Blender Foundation"))
            roots.append(os.path.join(base, "Program Files (x86)", "Steam",
                                      "steamapps", "common", "Blender"))
        for root in roots:
            add(os.path.join(root, "blender.exe"))
            if os.path.isdir(root):
                # Program Files/Blender Foundation/Blender 4.2/blender.exe
                for entry in sorted(os.listdir(root), reverse=True):
                    add(os.path.join(root, entry, "blender.exe"))
    else:
        for path in ("/usr/bin/blender", "/usr/local/bin/blender",
                     "/snap/bin/blender",
                     "/Applications/Blender.app/Contents/MacOS/Blender"):
            add(path)

    return out


def find_blender(explicit=None):
    if explicit:
        if not os.path.isfile(explicit):
            raise SystemExit("no Blender executable at %s" % explicit)
        return explicit
    found = candidate_blenders()
    if not found:
        raise SystemExit(
            "Could not find Blender. Install it (https://www.blender.org/download/ "
            "or the free Steam listing), then pass --blender <path to blender.exe> "
            "or set the GRB_BLENDER environment variable.")
    return found[0]


# --------------------------------------------------------------------------
# running it
# --------------------------------------------------------------------------

def run_inside(payload, blender=None, timeout=900, verbose=False):
    """Run one command inside Blender and hand back its JSON report."""
    exe = find_blender(blender)
    cmd = [exe, "--background", "--factory-startup",
           "--python", INSIDE, "--", json.dumps(payload)]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    out = proc.stdout or ""

    if verbose:
        sys.stderr.write(out)
        sys.stderr.write(proc.stderr or "")

    if BEGIN not in out or END not in out:
        raise SystemExit(
            "Blender ran but produced no report.\n"
            "--- exit code %s ---\n%s\n--- stderr ---\n%s"
            % (proc.returncode, out[-4000:], (proc.stderr or "")[-4000:]))

    blob = out.split(BEGIN, 1)[1].split(END, 1)[0]
    return json.loads(blob)


# --------------------------------------------------------------------------
# plain-language reports
# --------------------------------------------------------------------------

def print_mesh(m, indent="  "):
    print("%s%s  -  %d verts, %d tris" % (indent, m["object"], m["vertices"],
                                          m["triangles"]))
    print("%s  UV sets:        %s" % (indent, ", ".join(m["uv_layers"]) or "(none)"))
    cols = ", ".join("%s [%s/%s]" % (c["name"], c["domain"], c["type"])
                     for c in m["color_attributes"])
    print("%s  vertex colors:  %s" % (indent, cols or "(none)"))
    print("%s  materials:      %s" % (indent, ", ".join(
        str(x) for x in m["materials"]) or "(none)"))
    if m["vertex_group_count"]:
        print("%s  vertex groups:  %d  (%d actually used)"
              % (indent, m["vertex_group_count"], m.get("distinct_bones_used", 0)))
        print("%s  influences:     max %d per vertex   %s"
              % (indent, m.get("max_influences", 0),
                 dict(m.get("influences_per_vertex", {}))))
        print("%s  unweighted:     %d vertices"
              % (indent, m.get("vertices_with_no_weight", 0)))
    else:
        print("%s  vertex groups:  (none - not skinned)" % indent)
    if m["modifiers"]:
        print("%s  modifiers:      %s" % (indent, ", ".join(
            "%s(%s)" % (x["name"], x["type"]) for x in m["modifiers"])))
    for w in m["warnings"]:
        print("%s  !  %s" % (indent, w))


def print_scene(report):
    print("Blender %s" % report.get("blender"))
    for entry in report.get("loaded", []):
        print("  loaded %s  (%d objects)" % (entry["file"], entry["objects_added"]))
    print()
    if report["meshes"]:
        print("MESHES (%d)" % len(report["meshes"]))
        for m in report["meshes"]:
            print_mesh(m)
            print()
    if report["armatures"]:
        print("ARMATURES (%d)" % len(report["armatures"]))
        for a in report["armatures"]:
            print("  %s  -  %d bones, roots: %s"
                  % (a["object"], a["bone_count"], ", ".join(a["root_bones"])))
            names = [b["name"] for b in a["bones"]]
            head = ", ".join(names[:12])
            print("    %s%s" % (head, " ..." if len(names) > 12 else ""))
            print()
    if report["other_objects"]:
        print("OTHER: %s" % ", ".join(
            "%s(%s)" % (o["object"], o["type"]) for o in report["other_objects"]))


def print_transfer(r):
    src, tgt, after = r["before"]["source"], r["before"]["target"], r["after"]
    print("Blender %s" % r["blender"])
    print()
    print("SOURCE (the vanilla garment)")
    print_mesh(src)
    print()
    print("TARGET (your new mesh), before")
    print_mesh(tgt)
    print()
    print("TARGET, after the transfer")
    print_mesh(after)
    print()
    arm = r["before"].get("armature")
    if arm:
        print("rig:              %s (%d bones)" % (arm["object"], arm["bone_count"]))
    else:
        print("rig:              none found in the source file  !")
    print("copied across:    %s" % ", ".join(r.get("transferred", ["weights"])))
    print("groups moved:     %d" % r["groups_transferred"])
    print("weight coverage:  %s%% of the new mesh's vertices got a weight"
          % r["weight_coverage_percent"])
    if r.get("exported"):
        print("written:          %s" % r["exported"])
    if (r["weight_coverage_percent"] or 0) < 100:
        print()
        print("!  Some vertices came out unweighted. They will not deform in game.")
        print("   Usually the two meshes are not sitting in the same place, or the")
        print("   new mesh extends past where the old one had geometry. Try")
        print("   --vert-mapping NEAREST or line the meshes up first.")


def print_selftest(r):
    print("Blender %s" % r["blender"])
    print("workdir: %s" % r["workdir"])
    print()
    for name, ok in r["checks"].items():
        print("  [%s]  %s" % ("PASS" if ok else "FAIL", name.replace("_", " ")))
    print()
    t = r["transfer"]
    print("  the fake coat had %d bone groups; %d landed on the fake poncho,"
          % (r["coat"]["vertex_group_count"], t["groups_transferred"]))
    print("  covering %s%% of its %d vertices. Reloading the exported GLB found"
          % (t["weight_coverage_percent"], t["after"]["vertices"]))
    print("  %d groups and %d unweighted vertices on it."
          % (r["reloaded"].get("vertex_group_count", 0),
             r["reloaded"].get("vertices_with_no_weight", -1)))
    print()
    print("RESULT: %s" % ("PASS - the bridge works end to end."
                          if r["passed"] else "FAIL - see above."))


def cmd_doctor(args):
    """Say what is installed and where, without running anything heavy."""
    print("Looking for Blender...")
    found = candidate_blenders()
    if not found:
        print("  none found.")
        print()
        print("Install Blender from https://www.blender.org/download/ (free), or")
        print("the Steam listing, then re-run. Point at it with --blender or the")
        print("GRB_BLENDER environment variable if it lands somewhere unusual.")
        return 1
    for i, path in enumerate(found):
        print("  %s %s" % ("->" if i == 0 else "  ", path))
    print()
    exe = found[0]
    proc = subprocess.run([exe, "--background", "--factory-startup",
                           "--python-expr",
                           "import sys,bpy,addon_utils;"
                           "print('BLENDER', bpy.app.version_string);"
                           "print('PYTHON', sys.version.split()[0]);"
                           "print('GLTF', any('gltf' in m.__name__ for m in "
                           "addon_utils.modules()))"],
                          capture_output=True, text=True, timeout=300,
                          encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith(("BLENDER", "PYTHON", "GLTF")):
            key, _, val = line.partition(" ")
            label = {"BLENDER": "Blender version", "PYTHON": "bundled Python",
                     "GLTF": "glTF add-on"}[key]
            print("  %-16s %s" % (label + ":", val))
    print()
    print("The glTF add-on is the bridge to ATK: ATK exports GRB meshes as GLB")
    print("and imports them back, and Blender reads and writes GLB natively.")
    print("Nothing extra to install.")
    print()
    print("Next: python grbblend.py selftest")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Drive Blender headlessly for GRB modding.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--blender", help="path to blender.exe (else auto-detected)")
    p.add_argument("--json", action="store_true", help="print the raw JSON report")
    p.add_argument("--verbose", action="store_true",
                   help="also show Blender's own console output")
    p.add_argument("--timeout", type=int, default=900, help="seconds (default 900)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="is Blender here, and does it have what we need?")

    sp = sub.add_parser("selftest",
                        help="prove the bridge works, touching no game files")
    sp.add_argument("--workdir", default=os.path.join(HERE, "_selftest"))

    sp = sub.add_parser("inspect",
                        help="what is in this GLB? UVs, colors, bones, weights")
    sp.add_argument("files", nargs="+")

    sp = sub.add_parser(
        "transfer-weights",
        help="copy weight painting from a vanilla garment onto a new mesh")
    sp.add_argument("--source", required=True, help="the rigged vanilla garment")
    sp.add_argument("--target", required=True, help="your new mesh")
    sp.add_argument("--out", help="write the result here (.glb)")
    sp.add_argument("--source-mesh", help="pick a mesh by name (else the biggest)")
    sp.add_argument("--target-mesh", help="pick a mesh by name (else the biggest)")
    sp.add_argument("--vert-mapping", default="POLYINTERP_NEAREST",
                    choices=["NEAREST", "EDGE_NEAREST", "EDGEINTERP_NEAREST",
                             "POLY_NEAREST", "POLYINTERP_NEAREST",
                             "POLYINTERP_VNORPROJ"],
                    help="how new vertices find old ones (default "
                         "POLYINTERP_NEAREST)")
    sp.add_argument("--keep-source", action="store_true",
                    help="leave the donor mesh in the exported scene")
    sp.add_argument("--no-bind", action="store_true",
                    help="skip adding the Armature modifier to the new mesh")
    sp.add_argument("--with-colors", action="store_true",
                    help="also copy the donor's vertex colors (GRB reads them)")
    sp.add_argument("--with-uvs", action="store_true",
                    help="also copy the donor's UV layout (overwrites the "
                         "new mesh's own UVs)")

    sp = sub.add_parser("run", help="run your own Python inside Blender")
    sp.add_argument("--code", help="a snippet; set `result` to report something")
    sp.add_argument("--script", help="a .py file to run instead")
    sp.add_argument("--file", dest="files", action="append", default=[],
                    help="import this file first (repeatable)")

    args = p.parse_args(argv)

    if args.command == "doctor":
        return cmd_doctor(args)

    payload = {"command": args.command}
    if args.command == "selftest":
        payload["workdir"] = args.workdir
    elif args.command == "inspect":
        payload["files"] = args.files
    elif args.command == "transfer-weights":
        payload.update({
            "source": args.source, "target": args.target, "out": args.out,
            "source_mesh": args.source_mesh, "target_mesh": args.target_mesh,
            "vert_mapping": args.vert_mapping,
            "drop_source": not args.keep_source,
            "bind_armature": not args.no_bind,
            "with_colors": args.with_colors,
            "with_uvs": args.with_uvs,
        })
    elif args.command == "run":
        if not args.code and not args.script:
            p.error("run needs --code or --script")
        payload.update({"code": args.code, "script": args.script,
                        "files": args.files})

    result = run_inside(payload, blender=args.blender, timeout=args.timeout,
                        verbose=args.verbose)

    if not result.get("ok"):
        print("FAILED: %s" % result.get("error"), file=sys.stderr)
        if args.verbose:
            print(result.get("traceback", ""), file=sys.stderr)
        return 1

    report = result["report"]
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "inspect":
        print_scene(report)
    elif args.command == "transfer-weights":
        print_transfer(report)
    elif args.command == "selftest":
        print_selftest(report)
        return 0 if report["passed"] else 1
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
