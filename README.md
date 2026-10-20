# wayfinder-map

[![test](https://github.com/johnLitoBardinas/wayfinder-map/actions/workflows/test.yml/badge.svg)](https://github.com/johnLitoBardinas/wayfinder-map/actions/workflows/test.yml)

A Claude Code plugin that shows a [`/wayfinder`](https://github.com/mattpocock/skills) map as a tree in your terminal. You see every ticket, its status, what blocks it and what is on the frontier, without opening a dozen GitHub issues.

```
Ship offline mode (map #1)
├── ✅ Decide which data must work offline (#2) [grilling]
│   ├── 🔵 Pin the sync conflict rule (#4) [grilling] @octocat
│   │   └──▶ (#6, shown under #5)
│   └── 🟢 Prototype the offline banner (#5) [prototype]
│       └── ⛔ Assemble the offline spec (#6) [task]  [also needs #3 ✅, #4 ⛔]
└── ✅ Research IndexedDB storage limits on iOS Safari (#3) [research]
    └──▶ (#6, shown under #5)

✅ closed · 🔵 claimed · 🟢 frontier · ⛔ blocked · child sits under its deepest blocker
2/5 closed · frontier: Prototype the offline banner (#5)
```

Claude then names the next ticket to work and the `/wayfinder` command for it.

## Install

In Claude Code:

```
/plugin marketplace add johnLitoBardinas/wayfinder-map
/plugin install wayfinder-map@wayfinder-map
```

## Use

From inside the repo that holds the map:

```
/wayfinder-map:wayfinder-map 1
```

Leave out the number and Claude finds open maps (`wayfinder:map` label) for you. It also triggers on plain requests like "show me map #1" or "what's on the frontier?".

The script also runs on its own, with no Claude involved:

```
python3 skills/wayfinder-map/render.py <map-number> [--repo owner/name]
```

## How to read the tree

- Each ticket hangs under its **deepest blocker**, so you read the tree top-down in the order the work can happen.
- A ticket with more than one blocker shows the others as `[also needs #n ✅/⛔]`. Under those other blockers it shows up again as a `▶` pointer, not drawn a second time.
- 🟢 means **frontier**: open, unclaimed and every blocker closed. Those are the tickets you can take now.
- `[grilling]`, `[research]`… is the ticket's `wayfinder:<type>` label.

Read-only: it never edits, claims or closes an issue.

## Requirements

- A map made by Matt Pocock's [`/wayfinder`](https://github.com/mattpocock/skills) skill on **GitHub Issues**. The tree is built from GitHub's native sub-issues and blocked-by links.
- [`gh`](https://cli.github.com/) CLI, signed in, with read access to the repo.
- Python 3. Standard library only.

## Development

The tests need pytest. The script itself stays standard library only.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

`tests/test_render.py` feeds hand-built issue data to `render()`, so no `gh` call or network is needed. The README example above is a golden test: change one and the other must match.

## Credits

`/wayfinder` and its map-and-ticket model are [Matt Pocock's](https://github.com/mattpocock/skills). This plugin only draws the map.

Made with ❤️ by [John Lito Bardinas](https://github.com/johnLitoBardinas). MIT licensed.
