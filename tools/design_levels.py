# -*- coding: utf-8 -*-
"""
design_levels.py —— 关卡设计辅助工具（开发期使用，不参与游戏运行）。

思路：
1. 用“逆向摆放”生成可通关布局：从空棋盘开始逐个放箭头，每次保证新箭头
   朝向上到边界之间没有已存在的箭头，则它在正向流程中一定可以按
   “摆放顺序的逆序”依次飞出。
2. 再用 DFS 求解器独立验证布局确实可通关（双重保险）。
"""

import random

VEC = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def ray_clear(arrows, r, c, d, rows, cols):
    """箭头 (r,c) 朝向 d 的方向上，到边界之间是否没有其他箭头。"""
    dr, dc = VEC[d]
    rr, cc = r + dr, c + dc
    occupied = {(a[0], a[1]) for a in arrows}
    while 0 <= rr < rows and 0 <= cc < cols:
        if (rr, cc) in occupied:
            return False
        rr += dr
        cc += dc
    return True


def gen(rows, cols, count, seed, need_dirs="UDLR"):
    random.seed(seed)
    arrows = []
    guard = 0
    while len(arrows) < count and guard < 100000:
        guard += 1
        r, c = random.randrange(rows), random.randrange(cols)
        if any(a[0] == r and a[1] == c for a in arrows):
            continue
        dirs = list(VEC)
        random.shuffle(dirs)
        # 前期优先补齐必须出现的方向
        missing = [x for x in need_dirs if x not in {a[2] for a in arrows}]
        if missing:
            dirs = missing + [x for x in dirs if x not in missing]
        for d in dirs:
            if ray_clear(arrows, r, c, d, rows, cols):
                arrows.append((r, c, d))
                break
    return arrows


def removable(state, rows, cols):
    """当前状态下所有可以飞出的箭头。"""
    out = []
    occupied = {(a[0], a[1]): a for a in state}
    for a in state:
        r, c, d = a
        dr, dc = VEC[d]
        rr, cc = r + dr, c + dc
        ok = True
        while 0 <= rr < rows and 0 <= cc < cols:
            if (rr, cc) in occupied:
                ok = False
                break
            rr += dr
            cc += dc
        if ok:
            out.append(a)
    return out


def solve(state, path, rows, cols):
    """DFS 求一个通关顺序。"""
    if not state:
        return path
    for a in removable(state, rows, cols):
        nxt = [x for x in state if x != a]
        res = solve(nxt, path + [a], rows, cols)
        if res is not None:
            return res
    return None


def show(arrows, rows, cols, solution):
    grid = [["·" for _ in range(cols)] for _ in range(rows)]
    glyph = {"U": "↑", "D": "↓", "L": "←", "R": "→"}
    for r, c, d in arrows:
        grid[r][c] = glyph[d]
    for row in grid:
        print("  " + " ".join(row))
    print("  箭头数:", len(arrows), " 方向分布:",
          {d: sum(1 for a in arrows if a[2] == d) for d in "UDLR"})
    print("  求解顺序:", [(r, c, d) for r, c, d in solution])
    print()


if __name__ == "__main__":
    # 关卡 1：手工设计的教学关
    lvl1 = [(0, 1, "L"), (0, 3, "R"), (2, 0, "U"), (2, 4, "D"),
            (2, 2, "U"), (4, 2, "U")]
    ROWS, COLS = 5, 5
    print("关卡1 (5x5):")
    show(lvl1, 5, 5, solve(lvl1, [], 5, 5))

    # 关卡 2：6x6
    ROWS, COLS = 6, 6
    lvl2 = gen(6, 6, 10, seed=20260919)
    print("关卡2 (6x6):")
    show(lvl2, 6, 6, solve(lvl2, [], 6, 6))

    # 关卡 3：7x7
    ROWS, COLS = 7, 7
    lvl3 = gen(7, 7, 14, seed=777)
    print("关卡3 (7x7):")
    show(lvl3, 7, 7, solve(lvl3, [], 7, 7))

