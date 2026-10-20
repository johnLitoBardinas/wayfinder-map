import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "wayfinder-map"))

import render  # noqa: E402

LEGEND = "✅ closed · 🔵 claimed · 🟢 frontier · ⛔ blocked · child sits under its deepest blocker"


def issue(n, title=None, state="open", assignees=(), kind="task"):
    return {
        "number": n,
        "title": title or f"Ticket {n}",
        "state": state,
        "assignees": [{"login": a} for a in assignees],
        "labels": [{"name": f"wayfinder:{kind}"}] if kind else [],
    }


def ref(i):
    # blocked_by entries are full issue objects; render only reads number and state.
    return {"number": i["number"], "state": i["state"]}


def draw(children, blocked_by=None, title="Map", map_no=1):
    blocked_by = blocked_by or {}
    blockers = {c["number"]: blocked_by.get(c["number"], []) for c in children}
    return render.render({"title": title}, map_no, children, blockers)


def tree(out):
    # Lines between the map title and the blank line before the legend.
    return out.split("\n\n")[0].splitlines()[1:]


def readme_example():
    text = (ROOT / "README.md").read_text()
    return re.search(r"```\n(Ship offline mode.*?)\n```", text, re.S).group(1)


def test_readme_example():
    t2 = issue(2, "Decide which data must work offline", "closed", kind="grilling")
    t3 = issue(3, "Research IndexedDB storage limits on iOS Safari", "closed", kind="research")
    t4 = issue(4, "Pin the sync conflict rule", assignees=["octocat"], kind="grilling")
    t5 = issue(5, "Prototype the offline banner", kind="prototype")
    t6 = issue(6, "Assemble the offline spec")
    out = draw(
        [t2, t3, t4, t5, t6],
        {4: [ref(t2)], 5: [ref(t2)], 6: [ref(t3), ref(t4), ref(t5)]},
        title="Ship offline mode",
    )
    assert out == readme_example()


@pytest.mark.parametrize(
    "ticket, blocker_state, mark",
    [
        (issue(1, state="closed", assignees=["a"]), "open", "✅"),  # closed beats assignee and open blocker
        (issue(1, assignees=["a"]), "open", "🔵"),  # assignee beats open blocker
        (issue(1, assignees=["a"]), "closed", "🔵"),  # assignee beats frontier
        (issue(1), "closed", "🟢"),
        (issue(1), "open", "⛔"),
    ],
    ids=["closed", "claimed-blocked", "claimed-unblocked", "frontier", "blocked"],
)
def test_status_priority(ticket, blocker_state, mark):
    out = draw([ticket], {1: [{"number": 99, "state": blocker_state}]})
    assert tree(out)[0].startswith(f"└── {mark} Ticket 1 (#1)")


def test_no_blockers_is_frontier():
    out = draw([issue(1)])
    assert tree(out) == ["└── 🟢 Ticket 1 (#1) [task]"]
    assert out.endswith("0/1 closed · frontier: Ticket 1 (#1)")


def test_assignee_hidden_once_closed():
    out = draw([issue(1, state="closed", assignees=["a"])])
    assert tree(out) == ["└── ✅ Ticket 1 (#1) [task]"]


def test_hangs_under_deepest_blocker():
    # 1 -> 2 -> 3; 4 needs 1 and 3, so it sits under 3 (depth 2), not 1 (depth 0).
    t1, t2, t3, t4 = issue(1, state="closed"), issue(2, state="closed"), issue(3), issue(4)
    out = draw([t1, t2, t3, t4], {2: [ref(t1)], 3: [ref(t2)], 4: [ref(t1), ref(t3)]})
    assert tree(out) == [
        "└── ✅ Ticket 1 (#1) [task]",
        "    ├── ✅ Ticket 2 (#2) [task]",
        "    │   └── 🟢 Ticket 3 (#3) [task]",
        "    │       └── ⛔ Ticket 4 (#4) [task]  [also needs #1 ✅]",
        "    └──▶ (#4, shown under #3)",
    ]


@pytest.mark.parametrize("listed", [[2, 3], [3, 2]])
def test_depth_tie_goes_to_later_sub_issue(listed):
    # 2 and 3 both have depth 0; 3 comes later in sub-issue order, whatever the blocked_by order.
    t1, t2, t3 = issue(1), issue(2), issue(3)
    by = {2: ref(t2), 3: ref(t3)}
    out = draw([t1, t2, t3], {1: [by[n] for n in listed]})
    assert tree(out) == [
        "├── 🟢 Ticket 2 (#2) [task]",
        "│   └──▶ (#1, shown under #3)",
        "└── 🟢 Ticket 3 (#3) [task]",
        "    └── ⛔ Ticket 1 (#1) [task]  [also needs #2 ⛔]",
    ]


def test_several_blockers():
    t1, t2, t3 = issue(1, state="closed"), issue(2), issue(3)
    out = draw([t1, t2, t3], {3: [ref(t1), ref(t2)]})
    assert tree(out) == [
        "├── ✅ Ticket 1 (#1) [task]",
        "│   └──▶ (#3, shown under #2)",
        "└── 🟢 Ticket 2 (#2) [task]",
        "    └── ⛔ Ticket 3 (#3) [task]  [also needs #1 ✅]",
    ]


def test_blocker_outside_map():
    out = draw([issue(1), issue(2)], {1: [{"number": 99, "state": "open"}, {"number": 98, "state": "closed"}]})
    assert tree(out) == [
        "├── ⛔ Ticket 1 (#1) [task]  [also needs #99 ⛔ outside map, #98 ✅ outside map]",
        "└── 🟢 Ticket 2 (#2) [task]",
    ]


def test_missing_wayfinder_label():
    t = issue(1, kind=None)
    t["labels"] = [{"name": "bug"}]
    assert tree(draw([t])) == ["└── 🟢 Ticket 1 (#1) [?]"]


def test_empty_map():
    assert draw([], title="Nothing yet", map_no=7) == "\n".join(
        ["Nothing yet (map #7)", "", LEGEND, "0/0 closed · frontier: none"]
    )


def test_blocker_cycle_drops_both_tickets():
    # Current behaviour, not desired: 1 and 2 each get the other as parent, so neither is a
    # top-level node and the tree is empty. The counts still include them.
    t1, t2 = issue(1), issue(2)
    out = draw([t1, t2], {1: [ref(t2)], 2: [ref(t1)]})
    assert out == "\n".join(["Map (map #1)", "", LEGEND, "0/2 closed · frontier: none"])


class FakeGh:
    def __init__(self, repo="me/here"):
        self.calls = []
        self.repo = repo

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": self.repo}
        path = args[-1]
        if path.endswith("/sub_issues"):
            return [issue(2)]
        if path.endswith("/blocked_by"):
            return None  # gh prints nothing for an empty paginated list
        return {"title": "Fake map"}


def run_main(monkeypatch, capsys, *argv):
    fake = FakeGh()
    monkeypatch.setattr(render, "gh", fake)
    monkeypatch.setattr(sys, "argv", ["render.py", *argv])
    render.main()
    return fake.calls, capsys.readouterr().out


@pytest.mark.parametrize("arg", ["1", "#1"])
def test_main_map_number(monkeypatch, capsys, arg):
    calls, out = run_main(monkeypatch, capsys, arg)
    assert calls == [
        ("repo", "view", "--json", "nameWithOwner"),
        ("api", "repos/me/here/issues/1"),
        ("api", "--paginate", "repos/me/here/issues/1/sub_issues"),
        ("api", "--paginate", "repos/me/here/issues/2/dependencies/blocked_by"),
    ]
    assert out.startswith("Fake map (map #1)\n└── 🟢 Ticket 2 (#2) [task]\n")


def test_main_repo_flag_skips_repo_view(monkeypatch, capsys):
    calls, _ = run_main(monkeypatch, capsys, "#1", "--repo", "other/repo")
    assert ("repo", "view", "--json", "nameWithOwner") not in calls
    assert calls[0] == ("api", "repos/other/repo/issues/1")


def test_main_without_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["render.py"])
    with pytest.raises(SystemExit, match="usage: render.py <map-number>"):
        render.main()
