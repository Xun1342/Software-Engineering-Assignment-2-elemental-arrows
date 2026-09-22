# -*- coding: utf-8 -*-
"""随机关卡生成与自动求解（逆向摆放 + DFS）。

生成原理：从空棋盘开始逐个放箭头，每次保证新箭头朝向上到边界之间
没有已存在的箭头，则它在正向流程中一定可以按“摆放顺序的逆序”飞出，
因此生成的关卡必然可通关；再用 DFS 求解器独立验证一遍。
"""

import random

from . import settings as S

VEC = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def _ray_clear(occupied, r, c, d, rows, cols):
    dr, dc = VEC[d]
    rr, cc = r + dr, c + dc
    while 0 <= rr < rows and 0 <= cc < cols:
        if (rr, cc) in occupied:
            return False
        rr += dr
        cc += dc
    return True


def generate_arrows(rows, cols, count, seed=None):
    """逆向摆放生成一组保证可通关的箭头 (row, col, dir)。"""
    rng = random.Random(seed)
    arrows = []
    occupied = set()
    guard = 0
    while len(arrows) < count and guard < 200000:
        guard += 1
        r, c = rng.randrange(rows), rng.randrange(cols)
        if (r, c) in occupied:
            continue
        dirs = list(VEC)
        rng.shuffle(dirs)
        missing = [x for x in "UDLR"
                   if x not in {a[2] for a in arrows}]
        if missing:
            dirs = missing + [x for x in dirs if x not in missing]
        for d in dirs:
            if _ray_clear(occupied, r, c, d, rows, cols):
                arrows.append((r, c, d))
                occupied.add((r, c))
                break
    return arrows


def generate_level(rows=7, cols=7, count=15, seed=None):
    """生成一个完整关卡 dict（可直接传给 Board / App.load_level）。"""
    if seed is None:
        seed = random.randrange(10 ** 8)
    arrows = generate_arrows(rows, cols, count, seed)
    return {
        "name": "随机试炼 · 元素幻境",
        "rows": rows,
        "cols": cols,
        "mistakes": 4,
        "accent": seed % len(S.ELEMENTS),
        "arrows": arrows,
        "seed": seed,
    }


def solve(arrows, rows, cols):
    """DFS 求一个通关顺序 [(r,c,d), ...]，无解返回 None。"""
    occ = {(r, c): d for r, c, d in arrows}

    def dfs(state, path):
        if not state:
            return path
        for (r, c), d in list(state.items()):
            dr, dc = VEC[d]
            rr, cc = r + dr, c + dc
            blocked = False
            while 0 <= rr < rows and 0 <= cc < cols:
                if (rr, cc) in state:
                    blocked = True
                    break
                rr += dr
                cc += dc
            if not blocked:
                nxt = dict(state)
                nxt.pop((r, c))
                result = dfs(nxt, path + [(r, c, d)])
                if result is not None:
                    return result
        return None

    return dfs(occ, [])
