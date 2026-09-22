# -*- coding: utf-8 -*-
"""验收自动化测试：对应作业要求 T01–T06，并覆盖新增功能 T07–T13。

无头环境运行（不弹窗、不发声）：
    set SDL_VIDEODRIVER=dummy
    set SDL_AUDIODRIVER=dummy
    python -m unittest tests.test_acceptance -v
或直接： python tests/test_acceptance.py
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game.app import App  # noqa: E402
from game.levelgen import generate_level, solve  # noqa: E402
from game.levels import LEVELS  # noqa: E402
from game import save as save_mod  # noqa: E402


def pump(app, frames):
    """推进指定帧数。"""
    for _ in range(frames):
        app.update(1 / 60)


def settle(app, frames=60):
    """推进到飞出/碰撞动画结束。"""
    pump(app, frames)


def click_xy(app, r, c):
    x, y = app.board.cell_center(r, c)
    app.on_click((x, y))


def post_click(rect_or_pos):
    if hasattr(rect_or_pos, "center"):
        pos = rect_or_pos.center
    else:
        pos = rect_or_pos
    pygame.event.post(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.load_level(0)  # 第一关·风起，5x5，6 箭，3 次失误

    def tearDown(self):
        pygame.event.clear()

    # —— 作业规定的 T01–T06 ——
    def test_T01_click_unblocked_flies_out(self):
        """T01 点击前方无阻挡的箭头：飞出棋盘并消失。"""
        app = self.app
        before = app.board.remaining()
        # (0,1) 朝左，位于顶行，向左到边界无箭头
        r, c = (0, 1)
        self.assertTrue(app.board.is_clear_to_edge(app.board.arrows[(r, c)]))
        click_xy(app, r, c)
        self.assertEqual(app.board.arrows[(r, c)].state, "flying")
        settle(app)
        self.assertNotIn((r, c), app.board.arrows)
        self.assertEqual(app.board.remaining(), before - 1)
        self.assertEqual(app.mistakes_left, 3)

    def test_T02_click_blocked_kept_and_mistake(self):
        """T02 点击前方有阻挡的箭头：不消失，失误次数减 1。"""
        app = self.app
        before = app.board.remaining()
        r, c = (4, 2)  # 朝上，(2,2) 挡在前方
        self.assertFalse(app.board.is_clear_to_edge(app.board.arrows[(r, c)]))
        click_xy(app, r, c)
        settle(app)
        self.assertIn((r, c), app.board.arrows)
        self.assertEqual(app.board.remaining(), before)
        self.assertEqual(app.mistakes_left, 2)

    def test_T03_edge_outward_arrow_no_oob(self):
        """T03 箭头飞出棋盘边缘时正常消失，不发生越界错误。

        所有可飞出的箭头最终都会越过某条棋盘边界；逐关按求解顺序点击，
        飞行过程逐帧推进，任何越界索引都会立刻抛异常。
        """
        # 六个关卡中应确实存在“位于边缘且朝向棋盘外”的箭头
        outward = []
        for level in LEVELS:
            for r, c, d in level["arrows"]:
                if ((d == "U" and r == 0)
                        or (d == "D" and r == level["rows"] - 1)
                        or (d == "L" and c == 0)
                        or (d == "R" and c == level["cols"] - 1)):
                    outward.append((r, c, d))
        self.assertTrue(outward, "关卡中应包含边缘朝外的箭头")

        for index, level in enumerate(LEVELS):
            app = App()
            app.load_level(index)
            rows, cols = app.board.rows, app.board.cols
            solution = solve(level["arrows"], rows, cols)
            self.assertIsNotNone(solution, f"第{index + 1}关无解")
            for r, c, _ in solution:
                arrow = app.board.arrows[(r, c)]
                # 位于边缘的箭头是本用例的重点检查对象
                click_xy(app, r, c)
                for _ in range(45):
                    app.update(1 / 60)
                    for a in app.board.arrows.values():
                        if a.state == "idle":
                            self.assertTrue(0 <= a.row < rows)
                            self.assertTrue(0 <= a.col < cols)
                self.assertNotIn((r, c), app.board.arrows)
            self.assertEqual(app.board.remaining(), 0)

    def test_T04_clear_all_shows_clear_and_next(self):
        """T04 消除本关全部箭头：显示通关并可进入下一关。"""
        app = self.app
        solution = solve(app.level["arrows"], app.board.rows, app.board.cols)
        for r, c, _ in solution:
            click_xy(app, r, c)
            settle(app)
        settle(app, 80)
        self.assertEqual(app.state, App.CLEAR)
        # 点击“下一关”按钮（真实鼠标事件）
        post_click(app.next_btn.rect)
        app.handle_events()
        self.assertEqual(app.state, App.PLAYING)
        self.assertEqual(app.level_index, 1)
        self.assertEqual(app.board.remaining(),
                         len(LEVELS[1]["arrows"]))

    def test_T05_mistakes_exhausted_fail_and_restart(self):
        """T05 失误次数耗尽：显示失败并允许重新开始。"""
        app = self.app
        r, c = (4, 2)  # 始终被 (2,2) 挡住
        for _ in range(3):
            click_xy(app, r, c)
            settle(app)
        settle(app, 60)
        self.assertEqual(app.state, App.FAILED)
        # 点击“重新开始”
        post_click(app.fail_restart_btn.rect)
        app.handle_events()
        self.assertEqual(app.state, App.PLAYING)
        self.assertEqual(app.mistakes_left, 3)
        self.assertEqual(app.board.remaining(), 6)

    def test_T06_restart_midgame_restores_layout(self):
        """T06 游戏进行中重新开始：箭头布局与失误次数恢复。"""
        app = self.app
        # 先飞出一支、再失误一次
        click_xy(app, 0, 1)
        settle(app)
        click_xy(app, 4, 2)
        settle(app)
        self.assertEqual(app.board.remaining(), 5)
        self.assertEqual(app.mistakes_left, 2)
        # 点击“重开”按钮
        post_click(app.restart_btn.rect)
        app.handle_events()
        self.assertEqual(app.state, App.PLAYING)
        self.assertEqual(app.board.remaining(), 6)
        self.assertEqual(app.mistakes_left, 3)
        self.assertEqual(app.moves, 0)
        initial = {(r, c): d for r, c, d in LEVELS[0]["arrows"]}
        current = {(r, c): a.direction
                   for (r, c), a in app.board.arrows.items()}
        self.assertEqual(current, initial)

    # —— 新增功能测试 ——
    def test_T07_hint_highlights_removable(self):
        """T07 提示按钮高亮的集合与可飞出箭头集合一致。"""
        app = self.app
        removable = {(a.row, a.col) for a in app.board.removable_arrows()}
        self.assertTrue(app.board.show_hint(app.now))
        self.assertGreaterEqual(len(removable), 4)
        # 被挡住的 (4,2) 不在提示集合中
        self.assertNotIn((4, 2), removable)

    def test_T08_undo_restores_board(self):
        """T08 撤销：飞出后撤销，箭头、步数与失误数恢复。"""
        app = self.app
        click_xy(app, 0, 1)
        settle(app)
        self.assertEqual(app.board.remaining(), 5)
        app.do_undo()
        self.assertEqual(app.board.remaining(), 6)
        self.assertEqual(app.moves, 0)
        self.assertEqual(app.mistakes_left, 3)

    def test_T09_timer_and_move_counter(self):
        """T09 计时只在游戏中累计，步数等于成功飞出次数。"""
        app = self.app
        pump(app, 60)
        self.assertAlmostEqual(app.elapsed, 1.0, delta=0.05)
        click_xy(app, 4, 2)  # 被挡，步数不增
        settle(app)
        self.assertEqual(app.moves, 0)
        click_xy(app, 0, 1)  # 成功，步数 +1
        settle(app)
        self.assertEqual(app.moves, 1)

    def test_T10_random_levels_solvable(self):
        """T10 随机关卡保证可通关。"""
        for seed in range(10):
            lv = generate_level(7, 7, 15, seed=seed)
            self.assertIsNotNone(solve(lv["arrows"], 7, 7))
            self.assertEqual(len(lv["arrows"]), 15)
        app = self.app
        app.start_random()
        self.assertEqual(app.mode, "random")
        self.assertEqual(app.board.remaining(), 15)
        solution = solve(app.level["arrows"], 7, 7)
        for r, c, _ in solution:
            click_xy(app, r, c)
            settle(app)
        settle(app, 80)
        self.assertEqual(app.state, App.ALL_CLEAR)

    def test_T11_auto_demo_clears_level(self):
        """T11 自动演示：精灵按求解顺序自动清空棋盘。"""
        app = self.app
        app.load_level(2)  # 第三关 14 箭
        app.toggle_demo()
        self.assertTrue(app.demo)
        for _ in range(900):
            app.update(1 / 60)
            if app.state in (App.CLEAR, App.ALL_CLEAR):
                break
        self.assertEqual(app.state, App.CLEAR)
        self.assertEqual(app.board.remaining(), 0)

    def test_T12_stars_and_save_unlock(self):
        """T12 零失误通关记三星并解锁下一关，存档可重新读取。"""
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        try:
            with mock.patch.object(save_mod, "SAVE_PATH", path):
                app = App()
                app.load_level(0)
                solution = solve(app.level["arrows"], 5, 5)
                for r, c, _ in solution:
                    click_xy(app, r, c)
                    settle(app)
                settle(app, 80)
                self.assertEqual(app.last_stars, 3)
                data = save_mod.load()
                self.assertEqual(data["stars"]["0"], 3)
                self.assertGreaterEqual(data["unlocked"], 2)
                # 失误一次应为两星
                app = App()
                app.load_level(0)
                click_xy(app, 4, 2)
                settle(app)
                solution = solve(
                    [(a.row, a.col, a.direction)
                     for a in app.board.arrows.values() if a.state == "idle"],
                    5, 5)
                for r, c, _ in solution:
                    if (r, c) in app.board.arrows:
                        click_xy(app, r, c)
                        settle(app)
                settle(app, 80)
                self.assertEqual(app.last_stars, 2)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_T13_locked_level_not_playable(self):
        """T13 选关界面中未解锁关卡点击无效。"""
        app = self.app
        app.save_data["unlocked"] = 1
        app.state = App.SELECT
        app.draw()  # 生成卡片矩形
        locked_rect = app.card_rects[3]
        post_click(locked_rect.center)
        app.handle_events()
        self.assertEqual(app.state, App.SELECT)
        # 已解锁关卡可以进入
        post_click(app.card_rects[0].center)
        app.handle_events()
        self.assertEqual(app.state, App.PLAYING)
        self.assertEqual(app.level_index, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
