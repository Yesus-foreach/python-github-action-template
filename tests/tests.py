#!/usr/bin/env python3
"""
Matchstick puzzle solver, run as a "unit test" by the inherited GitHub
Actions workflow.  Results are written to output.txt AND committed back to
the repository via the GitHub Contents API using the auto-provided
GITHUB_TOKEN, so the answer can be read directly from the repo.

Puzzle
------
  * A "unit segment" on the integer lattice is (x, y, o), o in {'H','V'}:
        H: (x,y) -> (x+1,y)
        V: (x,y) -> (x,y+1)
  * A "square of size s" is a square of side s units, perimeter drawn with
    unit segments (4*s of them).

  PART A: start = 2x2 grid of unit cells (12 matches).
          Goal: exactly 6 squares of size 2, reached with EXACTLY 3 moves
          (each move = lift one match, place it elsewhere; total matches
          stays 12).  Extra constraint: every moved match must end up
          touching (sharing an endpoint with) at least one match that was
          NOT moved.
  PART B: minimum number of matches to move (relocate) starting from the
          4x4 grid of unit cells (40 matches) so that the result contains
          6 squares of size 2.
  PART C: reference numbers -- max size-2 squares with 12 matches, and the
          square census of the 4x4 grid.
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


def all_squares(cfg, sizes=(1, 2, 3)):
    res = defaultdict(list)
    hs = [s for s in cfg if s[2] == 'H']
    vs = [s for s in cfg if s[2] == 'V']
    if not hs:
        return res
    xs = [s[0] for s in hs] + [s[0] + 1 for s in hs] + [s[0] for s in vs]
    ys = [s[1] for s in hs] + [s[1] for s in vs] + [s[1] + 1 for s in vs]
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


def lattice(xmax, ymax):
    out = []
    for y in range(ymax + 1):
        for x in range(xmax):
            out.append(H(x, y))
    for x in range(xmax + 1):
        for y in range(ymax):
            out.append(V(x, y))
    return out


START = grid_config(2, 2)
POOL = lattice(7, 7)
OUT = []


def emit(line=""):
    OUT.append(line)


def partA():
    emit("=" * 78)
    emit("PART A: exactly 3 moves from 12-match 2x2 grid -> 6 squares of size 2")
    emit("=" * 78)
    n = len(START)
    start_set = set(START)
    results = []
    for R in combinations(sorted(START), 3):
        remaining = start_set - set(R)
        holes = [s for s in POOL if s not in remaining]
        for A in combinations(holes, 3):
            final = frozenset(remaining | set(A))
            if len(final) != n:
                continue
            sq = all_squares(final, sizes=(2,))
            if len(sq[2]) != 6:
                continue
            unmoved = set(remaining)
            ok = False
            for perm in permutations(A):
                good = True
                for dest in perm:
                    if not any(touches(dest, u) for u in unmoved):
                        good = False
                        break
                if good:
                    ok = True
                    break
            if ok:
                results.append((frozenset(R), frozenset(A), final, sorted(sq[2])))
    emit("raw candidates (goal + touch constraint): %d" % len(results))

    # dedupe by final configuration
    uniq = []
    seen = set()
    for r in results:
        if r[2] in seen:
            continue
        seen.add(r[2])
        uniq.append(r)
    emit("distinct final configurations: %d" % len(uniq))

    # also: how many candidates WITHOUT the touch constraint?
    total_goal = 0
    for R in combinations(sorted(START), 3):
        remaining = start_set - set(R)
        holes = [s for s in POOL if s not in remaining]
        for A in combinations(holes, 3):
            final = frozenset(remaining | set(A))
            if len(final) != n:
                continue
            if len(all_squares(final, sizes=(2,))[2]) == 6:
                total_goal += 1
    emit("candidates meeting goal WITHOUT touch constraint: %d" % total_goal)

    for i, (R, A, final, sqs) in enumerate(uniq):
        emit("")
        emit("--- solution %d ---" % (i + 1))
        emit("moved-from (x,y,o): " + ", ".join(str(s) for s in sorted(R)))
        emit("moved-to   (x,y,o): " + ", ".join(str(s) for s in sorted(A)))
        emit("size-2 squares at: %s" % (sqs,))
        emit(render(final, "final:"))
        emit("all squares by size: %s" % {k: len(v) for k, v in all_squares(final).items()})
    return uniq


def max_size2():
    emit("")
    emit("=" * 78)
    emit("INFO: max number of size-2 squares obtainable with 12 matches")
    emit("=" * 78)
    best = (0, None)
    pool = lattice(5, 5)
    for combo in combinations(pool, 12):
        cfg = frozenset(combo)
        c = len(all_squares(cfg, sizes=(2,))[2])
        if c > best[0]:
            best = (c, cfg)
    emit("max size-2 squares with 12 matches: %d" % best[0])
    if best[1]:
        emit(render(best[1], "witness:"))
    return best


def bfs_min_moves(start, target_count, sizes, xmax=6, ymax=6, max_moves=20):
    start = frozenset(start)
    n = len(start)
    pool = lattice(xmax, ymax)

    def ok(cfg):
        if len(cfg) != n:
            return False
        sq = all_squares(cfg, sizes=sizes)
        return sum(len(v) for v in sq.values()) >= target_count

    seen = {start}
    frontier = [start]
    for depth in range(max_moves + 1):
        for cfg in frontier:
            if ok(cfg):
                return depth, cfg
        nxt = []
        for cfg in frontier:
            cur = set(cfg)
            for s in list(cur):
                rest = cur - {s}
                for t in pool:
                    if t in rest:
                        continue
                    new = frozenset(rest | {t})
                    if new not in seen:
                        seen.add(new)
                        nxt.append(new)
        frontier = nxt
        if not frontier:
            break
    return None


def partB():
    emit("")
    emit("=" * 78)
    emit("PART B: minimum moves from 4x4 grid (40 matches) to 6 size-2 squares")
    emit("=" * 78)
    g = grid_config(4, 4)
    emit("4x4 grid size: %d" % len(g))
    sq = all_squares(g)
    emit("squares in 4x4 grid by size: %s" % {k: len(v) for k, v in sq.items()})
    emit("size-2 squares present: %d" % len(sq[2]))
    emit(render(g, "4x4 grid:"))
    res = bfs_min_moves(g, 6, (2,))
    if res is None:
        emit("NOT REACHABLE within move budget")
    else:
        d, cfg = res
        emit("min moves (relocate): %d" % d)
        emit(render(cfg, "witness:"))
        emit("squares by size: %s" % {k: len(v) for k, v in all_squares(cfg).items()})
    return res


def commit_output(text):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        emit("(no GITHUB_TOKEN; skipping commit-back)")
        return
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF", "refs/heads/main").split("/")[-1]
    if not repo:
        emit("(no GITHUB_REPOSITORY; skipping commit-back)")
        return
    url = "https://api.github.com/repos/%s/contents/output.txt" % repo
    # fetch existing sha if any
    sha = None
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            sha = data.get("sha")
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
        emit("START (12 matches, 2x2 grid of unit cells):")
        emit(render(START))
        emit("squares in start by size: %s" % {k: len(v) for k, v in all_squares(START).items()})
        emit("")
        partA()
        max_size2()
        partB()
        text = "\n".join(OUT) + "\n"
        with open("output.txt", "w") as f:
            f.write(text)
        print(text)
        commit_output(text)


if __name__ == "__main__":
    unittest.main()
