#!/usr/bin/env python3
"""
Matchstick puzzle solver (run by the inherited GitHub Actions workflow).
Writes results to output.txt and commits them back to the repository.

MODEL
-----
Unit segment on the integer lattice: (x, y, o), o in {'H','V'}
    H: (x,y) -> (x+1,y)
    V: (x,y) -> (x,y+1)
A square of side s has perimeter drawn with 4*s unit segments.

QUESTIONS
---------
Q0  Exhaustive census: over ALL 12-match configurations that fit in a 3x3
    cell box, how many squares (by size) can exist at most?  Can 12 matches
    ever hold 6 squares of side 2?  Of any size?
Q1  Start = 2x2 grid of unit cells (12 matches, the classic "square, 4 panes").
    Exactly 3 moves -> exactly 6 squares of side 2, with every moved match
    touching at least one unmoved match.  All solutions + symmetry classes.
Q2  Start = perimeter of a 3x3 cell box (hollow square, 3 per side, 12
    matches).  Same question.
Q3  4x4 grid of unit cells (40 matches) -> 6 squares of side 2:
    minimum matches REMOVED, and minimum matches RELOCATED.
"""

import os
import json
import base64
import urllib.request
import unittest
from itertools import combinations, permutations
from collections import defaultdict


def H(x, y): return (x, y, 'H')
def V(x, y): return (x, y, 'V')


def endpoints(s):
    x, y, o = s
    if o == 'H':
        return frozenset(((x, y), (x + 1, y)))
    return frozenset(((x, y), (x, y + 1)))


def square_sides(cx, cy, s):
    out = []
    for i in range(s):
        out.append(H(cx + i, cy))
        out.append(H(cx + i, cy + s))
        out.append(V(cx, cy + i))
        out.append(V(cx + s, cy + i))
    return frozenset(out)


def grid_config(nx, ny):
    cfg = set()
    for y in range(ny + 1):
        for x in range(nx):
            cfg.add(H(x, y))
    for x in range(nx + 1):
        for y in range(ny):
            cfg.add(V(x, y))
    return frozenset(cfg)


def lattice(nx, ny):
    """All unit segments of an nx x ny cell box (nx+1 by ny+1 lattice)."""
    out = []
    for y in range(ny + 1):
        for x in range(nx):
            out.append(H(x, y))
    for x in range(nx + 1):
        for y in range(ny):
            out.append(V(x, y))
    return out


def count_squares(cfg, sizes=(1, 2, 3)):
    """counts by size; only squares fully inside cfg"""
    hs = [s for s in cfg if s[2] == 'H']
    vs = [s for s in cfg if s[2] == 'V']
    counts = defaultdict(int)
    if not hs:
        return counts
    xs = [s[0] for s in hs] + [s[0] + 1 for s in hs] + [s[0] for s in vs]
    ys = [s[1] for s in hs] + [s[1] for s in vs]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    for size in sizes:
        for cx in range(x0 - size, x1 + size + 1):
            for cy in range(y0 - size, y1 + size + 1):
                if square_sides(cx, cy, size) <= cfg:
                    counts[size] += 1
    return counts


def all_squares(cfg, sizes=(1, 2, 3)):
    res = defaultdict(list)
    hs = [s for s in cfg if s[2] == 'H']
    vs = [s for s in cfg if s[2] == 'V']
    if not hs:
        return res
    xs = [s[0] for s in hs] + [s[0] + 1 for s in hs] + [s[0] for s in vs]
    ys = [s[1] for s in hs] + [s[1] for s in vs]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    for size in sizes:
        for cx in range(x0 - size, x1 + size + 1):
            for cy in range(y0 - size, y1 + size + 1):
                if square_sides(cx, cy, size) <= cfg:
                    res[size].append((cx, cy))
    return res


def touches(a, b):
    return bool(endpoints(a) & endpoints(b))


def render(cfg, label=""):
    hs = [s for s in cfg if s[2] == 'H']
    vs = [s for s in cfg if s[2] == 'V']
    if not cfg:
        return label + " (empty)"
    xs = [s[0] for s in hs] + [s[0] + 1 for s in hs] + [s[0] for s in vs]
    ys = [s[1] for s in hs] + [s[1] for s in vs]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    g = [[' '] * (2 * (x1 - x0) + 1) for _ in range(2 * (y1 - y0) + 1)]
    for (x, y, o) in hs:
        g[2 * (y - y0)][2 * (x - x0)] = '-'
    for (x, y, o) in vs:
        g[2 * (y - y0)][2 * (x - x0)] = '|'
    body = "\n".join("".join(r).rstrip() for r in g)
    return (label + "\n" + body) if label else body


OUT = []


def emit(line=""):
    OUT.append(line)


# ---------------------------------------------------------------- Q0

def q0():
    emit("=" * 78)
    emit("Q0: EXHAUSTIVE census of 12-match configurations in a 3x3 cell box")
    emit("=" * 78)
    segs = lattice(3, 3)
    emit("lattice segments in 3x3 cell box: %d" % len(segs))
    emit("enumerating C(%d,12) = %d configurations ..." % (len(segs), len(list(combinations(range(12), 12)))))
    best_total = -1
    best_cfg = None
    best_by_size = defaultdict(int)
    # also: best config for each individual size
    best_for_size = {}
    for combo in combinations(segs, 12):
        cfg = frozenset(combo)
        c = count_squares(cfg, sizes=(1, 2, 3))
        tot = c[1] + c[2] + c[3]
        for k, v in c.items():
            if v > best_by_size[k]:
                best_by_size[k] = v
                best_for_size[k] = cfg
        if tot > best_total:
            best_total = tot
            best_cfg = cfg
    emit("max squares of each size with 12 matches: %s" % dict(best_by_size))
    emit("max TOTAL squares (sizes 1..3): %d" % best_total)
    emit(render(best_cfg, "witness for max total:"))
    emit("  counts: %s" % dict(count_squares(best_cfg, sizes=(1, 2, 3))))
    for k in sorted(best_for_size):
        emit(render(best_for_size[k], "witness for max size-%d squares:" % k))
        emit("  counts: %s" % dict(count_squares(best_for_size[k], sizes=(1, 2, 3))))
    emit("")
    emit("CONCLUSION: 6 squares of side 2 need >= 8*6 segments unless heavily")
    emit("shared; the max side-2 count achievable with 12 matches is %d."
         % best_by_size[2])
    return best_total, best_cfg


# ---------------------------------------------------------------- Q1 / Q2

def search_three_moves(start, goal_size2=None, exact_total_squares=None,
                       pool=None, label=""):
    """Enumerate all final configs reachable in exactly 3 moves from `start`.
    A move = lift one segment, place it elsewhere (count preserved).
    Returns list of (R, A, final) with R=removed-from, A=added-to."""
    if pool is None:
        pool = lattice(5, 5)
    start = frozenset(start)
    start_set = set(start)
    out = []
    for R in combinations(sorted(start), 3):
        remaining = start_set - set(R)
        holes = [s for s in pool if s not in remaining]
        for A in combinations(holes, 3):
            final = frozenset(remaining | set(A))
            if len(final) != len(start):
                continue
            if goal_size2 is not None:
                if count_squares(final, sizes=(goal_size2,))[goal_size2] != 6:
                    continue
            if exact_total_squares is not None:
                c = count_squares(final, sizes=(1, 2, 3))
                if c[1] + c[2] + c[3] != exact_total_squares:
                    continue
            out.append((frozenset(R), frozenset(A), final))
    return out


def touch_ok(R, A, start):
    """Is there an assignment of the 3 moved matches to the 3 final slots
    such that every moved match touches at least one unmoved match?"""
    start_set = set(start)
    unmoved = start_set - set(R)
    for perm in permutations(sorted(A)):
        if all(any(touches(d, u) for u in unmoved) for d in perm):
            return True
    return False


def canon(cfg):
    """Canonical form of a config under the dihedral group of the square
    (rotations by 90 deg + reflections), to identify symmetry classes."""
    best = None
    for k in range(8):
        t = set()
        for (x, y, o) in cfg:
            if k < 4:
                rot = k
            else:
                rot = k - 4
            # rotate by 90*rot
            rx, ry = x, y
            for _ in range(rot):
                rx, ry = ry, -rx
            if o == 'H':
                t.add(H(rx, ry))
            else:
                t.add(V(rx, ry))
        if k >= 4:
            # reflect: (x,y) -> (-x, y)
            t2 = set()
            for (x, y, o) in t:
                t2.add(H(-x, y) if o == 'H' else V(-x, y))
            t = t2
        f = frozenset(t)
        if best is None or sorted(f) < sorted(best):
            best = f
    return best


def q1():
    emit("")
    emit("=" * 78)
    emit("Q1: start = 2x2 grid of unit cells (12 matches)")
    emit("=" * 78)
    start = grid_config(2, 2)
    emit(render(start, "START:"))
    emit("squares in start: %s" % dict(count_squares(start, sizes=(1, 2, 3))))
    emit("")

    emit("-- Q1a: exactly 3 moves -> exactly 6 squares of side 2 --")
    res = search_three_moves(start, goal_size2=2)
    emit("final configs with exactly 6 side-2 squares (3 moves): %d" % len(res))
    res_touch = [r for r in res if touch_ok(r[0], r[1], start)]
    emit("  of which satisfy the 'touches an unmoved match' rule: %d"
         % len(res_touch))
    uniq = []
    seen = set()
    for r in res_touch:
        if r[2] in seen:
            continue
        seen.add(r[2])
        uniq.append(r)
    emit("  distinct final configurations: %d" % len(uniq))
    classes = defaultdict(list)
    for r in uniq:
        classes[canon(r[2])].append(r)
    emit("  symmetry classes (under D4 of the square): %d" % len(classes))
    for i, (R, A, final) in enumerate(uniq):
        emit("")
        emit("  --- config %d ---" % (i + 1))
        emit("  moved-from: %s" % (sorted(R),))
        emit("  moved-to  : %s" % (sorted(A),))
        emit("  squares by size: %s" % dict(count_squares(final, sizes=(1, 2, 3))))
        emit(render(final, "  final:"))

    emit("")
    emit("-- Q1b: exactly 3 moves -> exactly 6 squares of ANY size --")
    res6 = search_three_moves(start, exact_total_squares=6)
    emit("final configs with exactly 6 squares total (any size): %d" % len(res6))
    res6t = [r for r in res6 if touch_ok(r[0], r[1], start)]
    emit("  satisfying touch rule: %d" % len(res6t))
    uniq6 = []
    seen6 = set()
    for r in res6t:
        if r[2] in seen6:
            continue
        seen6.add(r[2])
        uniq6.append(r)
    emit("  distinct final configurations: %d" % len(uniq6))
    for i, (R, A, final) in enumerate(uniq6[:10]):
        emit("")
        emit("  --- config %d ---" % (i + 1))
        emit("  moved-from: %s" % (sorted(R),))
        emit("  moved-to  : %s" % (sorted(A),))
        emit("  squares by size: %s" % dict(count_squares(final, sizes=(1, 2, 3))))
        emit(render(final, "  final:"))

    emit("")
    emit("-- Q1c: exactly 3 moves -> MAXIMUM squares achievable --")
    best = (-1, None)
    for R in combinations(sorted(start), 3):
        remaining = set(start) - set(R)
        holes = [s for s in lattice(5, 5) if s not in remaining]
        for A in combinations(holes, 3):
            final = frozenset(remaining | set(A))
            c = count_squares(final, sizes=(1, 2, 3))
            t = c[1] + c[2] + c[3]
            if t > best[0]:
                best = (t, (R, A, final, dict(c)))
    emit("max total squares with 12 matches after 3 moves: %d" % best[0])
    R, A, final, c = best[1]
    emit("  counts: %s" % c)
    emit("  moved-from: %s" % (sorted(R),))
    emit("  moved-to  : %s" % (sorted(A),))
    emit(render(final, "  final:"))
    return res_touch


def q2():
    emit("")
    emit("=" * 78)
    emit("Q2: start = hollow square, 3 per side (perimeter of 3x3 cells, 12 matches)")
    emit("=" * 78)
    g = grid_config(3, 3)
    perim = frozenset(s for s in g
                      if not (s[2] == 'H' and s[1] in (1, 2)) and
                      not (s[2] == 'V' and s[0] in (1, 2)))
    emit(render(perim, "START:"))
    emit("count: %d" % len(perim))
    emit("squares in start: %s" % dict(count_squares(perim, sizes=(1, 2, 3))))
    res = search_three_moves(perim, goal_size2=2)
    emit("3-move finals with exactly 6 side-2 squares: %d" % len(res))
    res_touch = [r for r in res if touch_ok(r[0], r[1], perim)]
    emit("  satisfying touch rule: %d" % len(res_touch))
    uniq = []
    seen = set()
    for r in res_touch:
        if r[2] in seen:
            continue
        seen.add(r[2])
        uniq.append(r)
    for i, (R, A, final) in enumerate(uniq[:10]):
        emit("")
        emit("  --- config %d ---" % (i + 1))
        emit("  moved-from: %s" % (sorted(R),))
        emit("  moved-to  : %s" % (sorted(A),))
        emit("  squares by size: %s" % dict(count_squares(final, sizes=(1, 2, 3))))
        emit(render(final, "  final:"))
    return res_touch


# ---------------------------------------------------------------- Q3

def q3():
    emit("")
    emit("=" * 78)
    emit("Q3: 4x4 grid of unit cells (40 matches) -> 6 squares of side 2")
    emit("=" * 78)
    g = grid_config(4, 4)
    emit("4x4 grid size: %d" % len(g))
    emit("squares in 4x4 grid: %s" % dict(count_squares(g, sizes=(1, 2, 3))))
    emit(render(g, "4x4 grid:"))
    emit("")

    segs = sorted(g)
    # minimum REMOVED
    best_rm = None
    for rm in range(0, 25):
        for combo in combinations(segs, rm):
            keep = frozenset(set(g) - set(combo))
            if count_squares(keep, sizes=(2,))[2] == 6:
                best_rm = (rm, combo, keep)
                break
        if best_rm:
            break
    if best_rm:
        emit("Q3-removed: minimum matches REMOVED to leave exactly 6 side-2 squares: %d"
             % best_rm[0])
        emit("removed: %s" % (list(best_rm[1]),))
        emit("squares by size: %s" % dict(count_squares(best_rm[2], sizes=(1, 2, 3))))
        emit(render(best_rm[2], "result:"))
    else:
        emit("Q3-removed: none found within 24 removals")
    emit("")

    # minimum RELOCATED (count stays 40)
    POOL = lattice(6, 6)
    best_rel = None
    for r in range(0, 11):
        found = None
        for rm in combinations(segs, r):
            base = set(g) - set(rm)
            for add in combinations([s for s in POOL if s not in base], r):
                final = frozenset(base | set(add))
                if len(final) != 40:
                    continue
                if count_squares(final, sizes=(2,))[2] == 6:
                    found = (rm, add, final)
                    break
            if found:
                break
        if found:
            best_rel = (r, found)
            break
    if best_rel:
        r, (rm, add, final) = best_rel
        emit("Q3-relocated: minimum matches RELOCATED to reach exactly 6 side-2 squares: %d"
             % r)
        emit("removed: %s" % (list(rm),))
        emit("added  : %s" % (list(add),))
        emit("squares by size: %s" % dict(count_squares(final, sizes=(1, 2, 3))))
        emit(render(final, "result:"))
    else:
        emit("Q3-relocated: none found within 10 relocations")
    return best_rm, best_rel


def commit_output(text):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF", "refs/heads/main").split("/")[-1]
    if not token or not repo:
        emit("(no token/repo; skipping commit-back)")
        return
    url = "https://api.github.com/repos/%s/contents/output.txt" % repo
    sha = None
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read()).get("sha")
    except Exception:
        sha = None
    body = json.dumps({
        "message": "solver output",
        "branch": branch,
        "content": base64.b64encode(text.encode()).decode(),
        "sha": sha,
    }).encode()
    req = urllib.request.Request(url, data=body, method="PUT", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            emit("committed output.txt OK")
    except Exception as e:
        emit("commit-back failed: %r" % (e,))


class TestMatchstick(unittest.TestCase):
    def test_solve(self):
        q0()
        q1()
        q2()
        q3()
        text = "\n".join(OUT) + "\n"
        with open("output.txt", "w") as f:
            f.write(text)
        print(text)
        commit_output(text)


if __name__ == "__main__":
    unittest.main()
