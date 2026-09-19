# -*- coding: utf-8 -*-
"""关卡与核心规则测试（不依赖 pytest，直接 python tests/test_levels.py 运行）。

覆盖：
1. 四个方向的路径检测（含贴边边界情况）；
2. 每个关卡都包含上/下/左/右四种箭头；
3. DFS 求解器证明每个关卡存在通关顺序，并与 Board.is_clear_to_edge 交叉验证；
4. 按通关顺序模拟点击，可正常进入下一关 / 全部通关；
5. 连续误触被阻挡箭头会扣减失误并最终失败，重新开始可复位。
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game.app import App  # noqa: E402
from game.board import Board  # noqa: E402
from game.levels import LEVELS  # noqa: E402
from game.settings import DIRS  # noqa: E402


# —— 参考实现：与游戏代码相互独立的路径检测 ——
def ref_is_clear(occupied, r, c, d, rows, cols):
    dc, dr = DIRS[d]
    rr, cc = r + dr, c + dc
    while 0 <= rr < rows and 0 <= cc < cols:
        if (rr, cc) in occupied:
            return False
        rr += dr
        cc += dc
    return True


def ref_solve(arrows, rows, cols):
    """DFS 返回一个通关顺序列表，无解返回 None。"""
    occupied = {(r, c): d for r, c, d in arrows}

    def dfs(occ, path):
        if not occ:
            return path
        for (r, c), d in list(occ.items()):
            if ref_is_clear(occ, r, c, d, rows, cols):
                nxt = dict(occ)
                nxt.pop((r, c))
                res = dfs(nxt, path + [(r, c, d)])
                if res is not None:
                    return res
        return None

    return dfs(occupied, [])


def settle(app, frames=40):
    for _ in range(frames):
        app.update(1 / 60)


def test_path_detection_four_directions():
    # 每个方向两枚箭头：一枚被挡、一枚朝向边界无阻挡
    # 上：(4,2)U 向上遇到 (2,2) => False；(2,2)U 向上到边界无箭头 => True
    board = Board({"rows": 5, "cols": 5, "arrows": [(4, 2, "U"), (2, 2, "U")]})
    assert board.is_clear_to_edge(board.arrows[(4, 2)]) is False
    assert board.is_clear_to_edge(board.arrows[(2, 2)]) is True
    # 下：(2,2)D 向下遇到 (4,2) => False；(4,2)D 贴边 => True
    board = Board({"rows": 5, "cols": 5, "arrows": [(2, 2, "D"), (4, 2, "D")]})
    assert board.is_clear_to_edge(board.arrows[(2, 2)]) is False
    assert board.is_clear_to_edge(board.arrows[(4, 2)]) is True
    # 左：(2,2)L 向左遇到 (2,0) => False；(2,0)L 贴边 => True
    board = Board({"rows": 5, "cols": 5, "arrows": [(2, 2, "L"), (2, 0, "L")]})
    assert board.is_clear_to_edge(board.arrows[(2, 2)]) is False
    assert board.is_clear_to_edge(board.arrows[(2, 0)]) is True
    # 右：(2,2)R 向右遇到 (2,4) => False；(2,4)R 贴边 => True
    board = Board({"rows": 5, "cols": 5, "arrows": [(2, 2, "R"), (2, 4, "R")]})
    assert board.is_clear_to_edge(board.arrows[(2, 2)]) is False
    assert board.is_clear_to_edge(board.arrows[(2, 4)]) is True
    print("ok 四方向路径检测与边界判定")


def test_levels_complete_and_cross_check():
    for idx, level in enumerate(LEVELS):
        rows, cols = level["rows"], level["cols"]
        dirs_present = {d for _, _, d in level["arrows"]}
        assert dirs_present == {"U", "D", "L", "R"}, f"关卡{idx+1}四方向不全"

        solution = ref_solve(level["arrows"], rows, cols)
        assert solution is not None, f"关卡{idx+1}无解！"

        # 用游戏内 Board 实现交叉验证每一步
        board = Board(level)
        for (r, c, d) in solution:
            arrow = board.arrows[(r, c)]
            assert arrow.direction == d
            assert board.is_clear_to_edge(arrow), f"关卡{idx+1} {(r,c,d)} 应可飞出"
            # 与参考实现一致
            occupied = {(a.row, a.col): a.direction
                        for a in board.arrows.values() if a.state == "idle"}
            assert ref_is_clear(occupied, r, c, d, rows, cols)
            arrow.state = "gone"
            board.arrows.pop((r, c))
        assert board.remaining() == 0
        print(f"ok 关卡{idx+1}《{level['name']}》可通关，"
              f"共 {len(level['arrows'])} 支箭头")


def test_full_playthrough():
    app = App()
    app.load_level(0)
    for idx, level in enumerate(LEVELS):
        solution = ref_solve(level["arrows"], level["rows"], level["cols"])
        assert app.mistakes_left == level["mistakes"], "失误数应初始化为关卡配置"
        for (r, c, d) in solution:
            assert app.state in (App.PLAYING,), f"异常状态 {app.state}"
            x, y = app.board.cell_center(r, c)
            app.on_click((x, y))
            settle(app)
        # 通关动画后进入结算
        settle(app, 60)
        if idx + 1 < len(LEVELS):
            assert app.state == App.CLEAR, f"关卡{idx+1}后应进入通关结算"
            app.load_level(idx + 1)
        else:
            assert app.state == App.ALL_CLEAR, "最后一关后应全部通关"
    print("ok 三关完整通关流程（零失误）")


def test_mistakes_fail_restart():
    app = App()
    app.load_level(0)
    # (4,2) 的向上箭头被 (2,2) 挡住
    x, y = app.board.cell_center(4, 2)
    total = LEVELS[0]["mistakes"]
    for left in range(total - 1, -1, -1):
        app.on_click((x, y))
        settle(app, 30)
        assert app.mistakes_left == left
    settle(app, 60)
    assert app.state == App.FAILED
    # 重新开始复位
    app.load_level(0)
    assert app.mistakes_left == total
    assert app.board.remaining() == len(LEVELS[0]["arrows"])
    assert app.state == App.PLAYING
    print("ok 失误耗尽失败与重新开始复位")


def test_wrong_click_does_not_remove():
    app = App()
    app.load_level(0)
    before = app.board.remaining()
    x, y = app.board.cell_center(4, 2)
    app.on_click((x, y))
    settle(app)
    assert app.board.remaining() == before, "被阻挡的箭头不应消失"
    print("ok 被阻挡箭头不会被消除")


if __name__ == "__main__":
    test_path_detection_four_directions()
    test_levels_complete_and_cross_check()
    test_full_playthrough()
    test_mistakes_fail_restart()
    test_wrong_click_does_not_remove()
    print("\n全部测试通过 ✔")
    pygame.quit()
