---
name: wayfinder-map
description: Show a /wayfinder map's current state as a tree — tickets, status, blocking edges, frontier. Use when the user asks to show/view/visualise a wayfinder map, "map #N", or which ticket is on the frontier. Read-only.
argument-hint: [map-number]
---

# Wayfinder Map

Read-only view of a `/wayfinder` map on GitHub Issues (map issue + sub-issues + native blocked-by).

1. Run `python3 <this skill's base directory>/render.py <map-number>` from inside the repo (add `--repo owner/name` when elsewhere). Map number: `$ARGUMENTS`; if empty, find it with `gh issue list --label wayfinder:map --state open`.
2. Print the script output verbatim in a code block.
3. Below it, one line: the frontier ticket(s) by name and the `/wayfinder #<map> #<ticket>` to work next. Nothing else.
