# -*- coding: utf-8 -*-
"""第四关以后的关卡生成/挑选脚本（开发期工具）。

复用“逆向摆放 + DFS 求解器”，并按行列覆盖度、内部格占比挑选分布
均匀的布局，输出可直接粘进 levels.py 的元组。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from design_levels import gen, solve  # noqa: E402


def score(ar, R, C):
    rs = {a[0] for a in ar}
    cs = {a[1] for a in ar}
    interior = sum(1 for r, c, _ in ar if 0 < r < R - 1 and 0 < c < C - 1)
    return len(rs) + len(cs) + 1.5 * interior


def search(R, C, n, seeds=range(1, 1200)):
    best = []
    for seed in seeds:
        ar = gen(R, C, n, seed)
        if len(ar) != n or {x[2] for x in ar} != {"U", "D", "L", "R"}:
            continue
        if solve(ar, [], R, C) is None:
            continue
        best.append((score(ar, R, C), seed, ar))
    best.sort(reverse=True, key=lambda x: x[0])
    return best[0]


def show(tag, R, C, n):
    sc, seed, ar = search(R, C, n)
    glyph = {"U": "↑", "D": "↓", "L": "←", "R": "→"}
    g = [["·"] * C for _ in range(R)]
    for r, c, d in ar:
        g[r][c] = glyph[d]
    print(f"{tag} seed={seed} score={sc}")
    for row in g:
        print("    " + " ".join(row))
    print("    arrows =", ar)
    print()


if __name__ == "__main__":
    show("L4 7x7x16", 7, 7, 16)
    show("L5 8x8x18", 8, 8, 18)
    show("L6 8x8x22", 8, 8, 22)
