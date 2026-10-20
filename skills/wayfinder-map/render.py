#!/usr/bin/env python3
"""Render a /wayfinder map (GitHub issue + sub-issues + native blocked-by) as a tree.

Usage: render.py <map-number> [--repo owner/name]
"""
import json
import subprocess
import sys


def gh(*args):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else None


def fetch(repo, map_no):
    base = f"repos/{repo}/issues"
    root = gh("api", f"{base}/{map_no}")
    children = gh("api", "--paginate", f"{base}/{map_no}/sub_issues") or []
    blockers = {
        c["number"]: [b for b in gh("api", "--paginate", f"{base}/{c['number']}/dependencies/blocked_by") or []]
        for c in children
    }
    return root, children, blockers


def render(root, map_no, children, blockers):
    order = [c["number"] for c in children]
    nodes = {c["number"]: c for c in children}

    def closed(n):
        return nodes[n]["state"] == "closed"

    def status(n):
        if closed(n):
            return "✅"
        if nodes[n]["assignees"]:
            return "🔵"
        if all(b["state"] == "closed" for b in blockers[n]):
            return "🟢"
        return "⛔"

    # Depth = longest blocker chain inside the map; a node hangs under its deepest blocker.
    depth = {}

    def d(n, seen=()):
        if n not in depth:
            inside = [b["number"] for b in blockers[n] if b["number"] in nodes and b["number"] not in seen]
            depth[n] = 1 + max((d(b, seen + (n,)) for b in inside), default=-1)
        return depth[n]

    parent = {}
    for n in order:
        inside = [b["number"] for b in blockers[n] if b["number"] in nodes]
        if inside:
            parent[n] = max(inside, key=lambda b: (d(b), order.index(b)))

    kids = {n: [c for c in order if parent.get(c) == n] for n in order}
    refs = {n: [c for c in order if parent.get(c) != n and n in [b["number"] for b in blockers[c]]] for n in order}

    def label(n):
        i = nodes[n]
        kind = next((l["name"].split(":", 1)[1] for l in i["labels"] if l["name"].startswith("wayfinder:")), "?")
        s = f"{status(n)} {i['title']} (#{n}) [{kind}]"
        if i["assignees"] and not closed(n):
            s += f" @{','.join(a['login'] for a in i['assignees'])}"
        extra = [
            f"#{b['number']} {'✅' if b['state'] == 'closed' else '⛔'}"
            + ("" if b["number"] in nodes else " outside map")
            for b in blockers[n]
            if b["number"] != parent.get(n)
        ]
        if extra:
            s += f"  [also needs {', '.join(extra)}]"
        return s

    lines = [f"{root['title']} (map #{map_no})"]

    def walk(n, prefix, last):
        lines.append(f"{prefix}{'└──' if last else '├──'} {label(n)}")
        sub = prefix + ("    " if last else "│   ")
        items = [("node", c) for c in kids[n]] + [("ref", c) for c in refs[n]]
        for i, (kind, c) in enumerate(items):
            end = i == len(items) - 1
            if kind == "node":
                walk(c, sub, end)
            else:
                lines.append(f"{sub}{'└──' if end else '├──'}▶ (#{c}, shown under #{parent.get(c)})")

    tops = [n for n in order if n not in parent]
    for i, n in enumerate(tops):
        walk(n, "", i == len(tops) - 1)

    frontier = [n for n in order if status(n) == "🟢"]
    done = sum(closed(n) for n in order)
    lines += [
        "",
        "✅ closed · 🔵 claimed · 🟢 frontier · ⛔ blocked · child sits under its deepest blocker",
        f"{done}/{len(order)} closed · frontier: "
        + (", ".join(f"{nodes[n]['title']} (#{n})" for n in frontier) or "none"),
    ]
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: render.py <map-number> [--repo owner/name]")
    map_no = int(args[0].lstrip("#"))
    repo = args[args.index("--repo") + 1] if "--repo" in args else gh(
        "repo", "view", "--json", "nameWithOwner"
    )["nameWithOwner"]
    root, children, blockers = fetch(repo, map_no)
    print(render(root, map_no, children, blockers))


if __name__ == "__main__":
    main()
