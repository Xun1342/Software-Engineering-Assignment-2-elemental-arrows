# -*- coding: utf-8 -*-
"""游戏主程序：菜单 / 选关 / 游戏 / 通关 / 失败界面。

包含：计时、步数、提示、撤销、星级评价、本地存档、随机关卡与自动求解演示。
"""

import os

import pygame

from . import settings as S
from . import ui
from . import save as save_mod
from .audio import SoundManager
from .board import Board
from .levelgen import generate_level, solve as solve_level
from .levels import LEVELS

_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "images",
)


def fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class App:
    # 场景状态
    MENU = "menu"
    SELECT = "select"
    PLAYING = "playing"
    FAILING = "failing"
    FAILED = "failed"
    CLEARING = "clearing"
    CLEAR = "clear"
    ALL_CLEAR = "all_clear"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.bg = self._load_bg()
        self.save_data = save_mod.load()

        # —— 菜单按钮 ——
        self.select_entry_btn = ui.Button((60, 600, 200, 54), "关卡选择", size=24)
        self.random_entry_btn = ui.Button((280, 600, 200, 54), "随机试炼", size=24)

        # —— 选关界面 ——
        self.card_rects = []
        self.random_card_rect = pygame.Rect(36, 500, 300, 90)
        self.select_back_btn = ui.Button((354, 500, 150, 90), "返 回", size=22)

        # —— 游戏内按钮 ——
        self.hint_btn = ui.Button((20, 628, 118, 46), "提 示", size=20)
        self.undo_btn = ui.Button((146, 628, 118, 46), "撤 销", size=20)
        self.restart_btn = ui.Button((272, 628, 118, 46), "重 开", size=20)
        self.menu_btn = ui.Button((398, 628, 122, 46), "菜 单", size=20)
        self.demo_btn = ui.Button((20, 688, 170, 40), "演示解法", size=18,
                                  primary=False)
        self.to_select_btn = ui.Button((350, 688, 170, 40), "选 关", size=18,
                                       primary=False)

        # —— 结算按钮（统一放在弹窗面板下方）——
        self.next_btn = ui.Button((170, 556, 200, 50), "下一关", size=24)
        self.again_btn = ui.Button((60, 556, 190, 50), "再玩一次", size=22)
        self.over_menu_btn = ui.Button((290, 556, 190, 50), "返回菜单",
                                       size=22, primary=False)
        self.fail_restart_btn = ui.Button((60, 556, 190, 50), "重新开始", size=22)
        self.fail_menu_btn = ui.Button((290, 556, 190, 50), "返回菜单",
                                       size=22, primary=False)

        self.now = 0.0
        self.floaters = []
        self.flash_t = 0.0
        self.state = self.MENU
        self.mode = "campaign"
        self.level_index = 0
        self.level = LEVELS[0]
        self.board = Board(self.level)
        self.mistakes_left = self.level["mistakes"]
        self.elapsed = 0.0
        self.moves = 0
        self.history = []
        self.last_stars = 0
        self.demo = False
        self.demo_queue = []
        self.demo_at = 0.0

    def _load_bg(self):
        path = os.path.join(_ASSET_DIR, "bg_menu.png")
        if not os.path.exists(path):
            return None
        img = pygame.image.load(path).convert_alpha()
        scale = max(S.WINDOW_W / img.get_width(), S.WINDOW_H / img.get_height())
        img = pygame.transform.smoothscale(
            img, (int(img.get_width() * scale), int(img.get_height() * scale)))
        rect = img.get_rect(center=(S.WINDOW_W // 2, S.WINDOW_H // 2))
        out = pygame.Surface((S.WINDOW_W, S.WINDOW_H))
        out.blit(img, rect)
        return out

    # —— 流程 ——
    def load_level(self, index, level_data=None):
        self.level_index = index
        self.level = level_data if level_data is not None else LEVELS[index]
        self.mode = "random" if level_data is not None else "campaign"
        self.board = Board(self.level)
        self.mistakes_left = self.level["mistakes"]
        self.state = self.PLAYING
        self.floaters.clear()
        self.flash_t = 0.0
        self.elapsed = 0.0
        self.moves = 0
        self.history.clear()
        self.last_stars = 0
        self._stop_demo()

    def start_random(self):
        data = generate_level(rows=7, cols=7, count=15)
        self.load_level(-1, data)

    def back_to_menu(self):
        self.state = self.MENU
        self.floaters.clear()
        self.flash_t = 0.0
        self._stop_demo()

    def add_floater(self, text, pos, color=(255, 150, 150)):
        self.floaters.append([text, pos[0], pos[1], 0.0, color])

    # —— 功能按钮 ——
    def do_hint(self):
        if self.board.is_animating() or self.state != self.PLAYING or self.demo:
            return
        if self.board.show_hint(self.now):
            self.sound.play("click")
            self.add_floater("金色脉动的箭头可以飞出",
                             (S.WINDOW_W // 2, 612), color=S.GOLD_HI)
        else:
            self.add_floater("当前没有可飞出的箭头",
                             (S.WINDOW_W // 2, 612), color=(255, 170, 170))

    def do_undo(self):
        if self.board.is_animating() or self.state != self.PLAYING or self.demo:
            return
        if not self.history:
            self.add_floater("没有可撤销的步骤",
                             (S.WINDOW_W // 2, 612), color=(200, 206, 230))
            return
        snap, mistakes, moves = self.history.pop()
        self.board.restore(snap)
        self.mistakes_left = mistakes
        self.moves = moves
        self.sound.play("click")
        self.add_floater("撤销一步", (S.WINDOW_W // 2, 612), color=S.GOLD_HI)

    # —— 自动求解演示 ——
    def toggle_demo(self):
        if self.state != self.PLAYING or self.board.is_animating():
            return
        if self.demo:
            self._stop_demo()
            self.add_floater("已停止演示", (S.WINDOW_W // 2, 612),
                             color=(200, 206, 230))
            return
        arrows = [(a.row, a.col, a.direction)
                  for a in self.board.arrows.values() if a.state == "idle"]
        solution = solve_level(arrows, self.board.rows, self.board.cols)
        if solution is None:
            self.add_floater("当前局面无解", (S.WINDOW_W // 2, 612),
                             color=(255, 170, 170))
            return
        self.demo = True
        self.demo_queue = solution
        self.demo_at = self.now + 0.45
        self.demo_btn.label = "停止演示"
        self.sound.play("click")
        self.add_floater("精灵将自动演示解法", (S.WINDOW_W // 2, 612),
                         color=S.GOLD_HI)

    def _stop_demo(self):
        self.demo = False
        self.demo_queue = []
        self.demo_btn.label = "演示解法"

    def _launch(self, arrow):
        """一支箭头飞出（玩家点击与自动演示共用）。"""
        self.history.append(
            (self.board.snapshot(), self.mistakes_left, self.moves))
        arrow.launch()
        self.moves += 1
        self.sound.play("fly")
        self.add_floater("飞出", self.board.cell_center(arrow.row, arrow.col),
                         color=S.GOLD_HI)

    # —— 事件 ——
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.SELECT:
                        self.state = self.MENU
                    else:
                        self.back_to_menu()
                    continue
                if self.state == self.PLAYING and not self.demo:
                    if event.key == pygame.K_h:
                        self.do_hint()
                    elif event.key == pygame.K_z:
                        self.do_undo()
                    elif event.key == pygame.K_r:
                        self._reload_current()

            if self.state == self.MENU:
                if self.select_entry_btn.handle_event(event):
                    self.sound.play("click")
                    self.state = self.SELECT
                elif self.random_entry_btn.handle_event(event):
                    self.sound.play("click")
                    self.start_random()

            elif self.state == self.SELECT:
                self._handle_select_event(event)

            elif self.state in (self.PLAYING, self.FAILING):
                if self.hint_btn.handle_event(event):
                    self.do_hint()
                elif self.undo_btn.handle_event(event):
                    self.do_undo()
                elif self.restart_btn.handle_event(event):
                    self.sound.play("click")
                    self._reload_current()
                elif self.menu_btn.handle_event(event):
                    self.sound.play("click")
                    self.back_to_menu()
                elif self.demo_btn.handle_event(event):
                    self.toggle_demo()
                elif self.to_select_btn.handle_event(event):
                    self.sound.play("click")
                    self._stop_demo()
                    self.state = self.SELECT
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                else:
                    for btn in (self.hint_btn, self.undo_btn, self.restart_btn,
                                self.menu_btn, self.demo_btn, self.to_select_btn):
                        btn.handle_event(event)

            elif self.state == self.FAILED:
                if self.fail_restart_btn.handle_event(event):
                    self.sound.play("click")
                    self._reload_current()
                elif self.fail_menu_btn.handle_event(event):
                    self.sound.play("click")
                    self.back_to_menu()

            elif self.state == self.CLEAR:
                if self.next_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(self.level_index + 1)

            elif self.state == self.ALL_CLEAR:
                if self.again_btn.handle_event(event):
                    self.sound.play("click")
                    if self.mode == "random":
                        self.start_random()
                    else:
                        self.load_level(0)
                elif self.over_menu_btn.handle_event(event):
                    self.sound.play("click")
                    self.back_to_menu()
        return True

    def _reload_current(self):
        if self.mode == "random":
            self.load_level(-1, self.level)
        else:
            self.load_level(self.level_index)

    def _handle_select_event(self, event):
        if self.select_back_btn.handle_event(event):
            self.sound.play("click")
            self.state = self.MENU
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            self.select_back_btn.handle_event(event)
            return
        if self.random_card_rect.collidepoint(event.pos):
            self.sound.play("click")
            self.start_random()
            return
        for i, rect in enumerate(self.card_rects):
            if rect.collidepoint(event.pos):
                if i < self.save_data["unlocked"]:
                    self.sound.play("click")
                    self.load_level(i)
                else:
                    self.sound.play("blocked")

    def on_click(self, pos):
        """点击箭头：无阻挡则飞出；被阻挡则碰撞反馈并消耗一次失误。"""
        if self.demo or self.board.is_animating() or self.state != self.PLAYING:
            return
        arrow = self.board.arrow_at(pos)
        if arrow is None:
            return
        if self.board.is_clear_to_edge(arrow):
            self._launch(arrow)
        else:
            arrow.bump()
            self.mistakes_left -= 1
            self.flash_t = 0.45
            self.sound.play("blocked")
            self.add_floater("阻挡！", self.board.cell_center(arrow.row, arrow.col))
            if self.mistakes_left <= 0:
                self.fail_at = self.now + S.SHAKE_DURATION + 0.15
                self.state = self.FAILING
                self._stop_demo()
                self.sound.play("fail")

    # —— 更新 ——
    def update(self, dt):
        self.now += dt
        if self.state != self.MENU and self.state != self.SELECT:
            self.board.update(dt, self.now)
        if self.state == self.PLAYING:
            self.elapsed += dt
        if self.flash_t > 0:
            self.flash_t = max(0.0, self.flash_t - dt)
        for f in self.floaters:
            f[2] -= 34 * dt
            f[3] += dt
        self.floaters = [f for f in self.floaters if f[3] < 0.9]

        # 自动演示：按求解顺序逐支飞出
        if (self.demo and self.state == self.PLAYING
                and not self.board.is_animating()
                and self.now >= self.demo_at):
            if self.demo_queue:
                r, c, d = self.demo_queue.pop(0)
                arrow = self.board.arrows.get((r, c))
                if arrow is not None and arrow.state == "idle":
                    self._launch(arrow)
                self.demo_at = self.now + 0.55
            else:
                self._stop_demo()

        if self.state == self.FAILING and self.now >= self.fail_at:
            self.state = self.FAILED
        elif self.state == self.PLAYING and self.board.remaining() == 0:
            self.state = self.CLEARING
            self.clear_at = self.now + 0.55
            self.sound.play("win")
        elif self.state == self.CLEARING and self.now >= self.clear_at:
            self._finish_level()

    def _finish_level(self):
        """通关结算：评星、写存档并决定进入下一关还是全部通关。"""
        if self.mode == "campaign":
            self.last_stars = save_mod.compute_stars(
                self.level["mistakes"], self.mistakes_left)
            save_mod.record_clear(
                self.save_data, self.level_index, self.last_stars,
                self.elapsed, self.moves, len(LEVELS))
            if self.level_index + 1 < len(LEVELS):
                self.state = self.CLEAR
                return
        self.state = self.ALL_CLEAR

    # —— 绘制 ——
    def draw(self):
        if self.state == self.MENU:
            self.draw_menu()
        elif self.state == self.SELECT:
            self.draw_select()
        else:
            self.draw_game()
        pygame.display.flip()

    # —— 开始界面 ——
    def draw_menu(self):
        if self.bg is not None:
            self.screen.blit(self.bg, (0, 0))
        else:
            self.screen.fill((18, 22, 44))
        veil = pygame.Surface((S.WINDOW_W, 470), pygame.SRCALPHA)
        veil.fill((14, 18, 42, 155))
        self.screen.blit(veil, (0, S.WINDOW_H - 470))

        ui.draw_text(self.screen, "元素之箭", (S.WINDOW_W // 2, 110),
                     size=60, color=S.GOLD_HI, bold=True, center=True)
        ui.draw_text(self.screen, "七元素 · 一箭又一箭", (S.WINDOW_W // 2, 178),
                     size=24, color=S.CREAM, center=True)

        x0 = 70
        gap = (S.WINDOW_W - 2 * x0) / 6
        for i, (name, main, light, dark) in enumerate(S.ELEMENTS):
            cx = int(x0 + i * gap)
            cy = 250
            pts = [(cx, cy - 16), (cx + 13, cy), (cx, cy + 16), (cx - 13, cy)]
            pygame.draw.polygon(self.screen, main, pts)
            pygame.draw.polygon(self.screen, light, pts, 2)
            ui.draw_text(self.screen, name, (cx, cy + 30), size=18,
                         color=S.CREAM, center=True, shadow=False)

        panel = pygame.Rect(40, 322, S.WINDOW_W - 80, 250)
        ui.draw_rounded_panel(self.screen, panel, fill=(20, 24, 52, 205))
        ui.draw_text(self.screen, "玩法说明", (S.WINDOW_W // 2, 348),
                     size=24, color=S.GOLD_HI, bold=True, center=True)
        lines = [
            "· 点击箭头，朝向到边界之间无其他箭头即可飞出",
            "· 被挡住会晃动警示并消耗一次失误",
            "· 提示可高亮当前能飞出的箭头，撤销可回退一步",
            "· 共六个关卡，另有随机试炼与自动演示",
            "· 零失误通关获得三星，进度自动保存",
        ]
        for i, line in enumerate(lines):
            ui.draw_text(self.screen, line, (60, 392 + i * 34),
                         size=17, color=S.CREAM, shadow=False)

        self.select_entry_btn.draw(self.screen)
        self.random_entry_btn.draw(self.screen)
        ui.draw_text(self.screen, "美术背景由 AI 生成、音效与界面由程序原创合成",
                     (S.WINDOW_W // 2, 818), size=15, color=(190, 196, 220),
                     center=True, shadow=False)

    # —— 选关界面 ——
    def draw_select(self):
        self.screen.fill((18, 22, 44))
        if self.bg is not None:
            veil = pygame.Surface((S.WINDOW_W, S.WINDOW_H), pygame.SRCALPHA)
            veil.fill((14, 18, 42, 150))
            self.screen.blit(self.bg, (0, 0))
            self.screen.blit(veil, (0, 0))
        ui.draw_text(self.screen, "选择关卡", (S.WINDOW_W // 2, 70),
                     size=40, color=S.GOLD_HI, bold=True, center=True)

        self.card_rects = []
        card_w, card_h = 150, 140
        xs = [36, 195, 354]
        ys = [130, 290]
        for i, level in enumerate(LEVELS):
            x = xs[i % 3]
            y = ys[i // 3]
            rect = pygame.Rect(x, y, card_w, card_h)
            self.card_rects.append(rect)
            unlocked = i < self.save_data["unlocked"]
            accent = S.ELEMENTS[level["accent"]][1]
            fill = (40, 46, 84, 235) if unlocked else (28, 30, 50, 220)
            ui.draw_rounded_panel(
                self.screen, rect, fill=fill,
                border=accent if unlocked else (70, 74, 100),
                radius=16, border_width=2)
            ui.draw_text(self.screen, f"第 {i + 1} 关",
                         rect.move(0, 10).center, size=20,
                         color=S.CREAM if unlocked else (130, 134, 160),
                         bold=True, center=True)
            if unlocked:
                ui.draw_text(self.screen, level["name"].split(" · ")[-1],
                             rect.move(0, 42).center, size=18, color=accent,
                             center=True, shadow=False)
                stars = self.save_data["stars"].get(str(i), 0)
                for k in range(3):
                    ui.draw_star(
                        self.screen,
                        (rect.centerx - 30 + k * 30, rect.bottom - 34),
                        radius=13, filled=k < stars)
                best = self.save_data["best"].get(str(i))
                if best:
                    ui.draw_text(self.screen, f"最佳 {fmt_time(best['time'])}",
                                 (rect.centerx, rect.bottom - 12),
                                 size=12, color=(170, 178, 210),
                                 center=True, shadow=False)
            else:
                ui.draw_lock(self.screen,
                             (rect.centerx, rect.centery + 26), size=30)
                ui.draw_text(self.screen, "通关前一关解锁",
                             (rect.centerx, rect.bottom - 24),
                             size=13, color=(120, 126, 156),
                             center=True, shadow=False)

        # 随机关卡与返回
        ui.draw_rounded_panel(self.screen, self.random_card_rect,
                              fill=(40, 46, 84, 235), border=S.GOLD,
                              radius=16, border_width=2)
        ui.draw_text(self.screen, "随机试炼",
                     self.random_card_rect.move(0, -14).center,
                     size=22, color=S.GOLD_HI, bold=True, center=True)
        ui.draw_text(self.screen, "每次生成全新可通关棋盘",
                     self.random_card_rect.move(0, 16).center,
                     size=15, color=S.CREAM, center=True, shadow=False)
        self.select_back_btn.draw(self.screen)

    # —— 游戏界面 ——
    def draw_game(self):
        self.screen.fill((18, 22, 44))
        self.draw_hud()
        self.board.draw(self.screen, self.now, hover_pos=pygame.mouse.get_pos())
        self.draw_floaters()
        for btn in (self.hint_btn, self.undo_btn, self.restart_btn, self.menu_btn,
                    self.demo_btn, self.to_select_btn):
            btn.draw(self.screen)
        ui.draw_text(self.screen, "提示：金色脉动描边的箭头当前可以飞出",
                     (S.WINDOW_W // 2, 744), size=15,
                     color=(180, 188, 216), center=True, shadow=False)
        ui.draw_text(self.screen, "快捷键：H 提示　Z 撤销　R 重开　Esc 菜单",
                     (S.WINDOW_W // 2, 770), size=15,
                     color=(150, 158, 190), center=True, shadow=False)
        if self.flash_t > 0:
            alpha = int(95 * (self.flash_t / 0.45))
            veil = pygame.Surface((S.WINDOW_W, S.WINDOW_H), pygame.SRCALPHA)
            veil.fill((210, 60, 70, alpha))
            self.screen.blit(veil, (0, 0))
        if self.state == self.FAILED:
            self.draw_failed()
        elif self.state == self.CLEAR:
            self.draw_clear()
        elif self.state == self.ALL_CLEAR:
            self.draw_all_clear()

    def draw_hud(self):
        accent = S.ELEMENTS[self.level["accent"]][1]
        ui.draw_text(self.screen, self.level["name"],
                     (S.WINDOW_W // 2, 38), size=26, color=S.GOLD_HI,
                     bold=True, center=True)
        ui.draw_text(self.screen, f"时间 {fmt_time(self.elapsed)}",
                     (26, 96), size=19, color=S.CREAM, bold=True)
        ui.draw_text(self.screen, f"步数 {self.moves}",
                     (132, 96), size=19, color=S.CREAM, bold=True)
        ui.draw_text(self.screen, f"剩余 {self.board.remaining()}",
                     (222, 96), size=19, color=accent, bold=True)
        total = self.level["mistakes"]
        gap = 24
        x0 = S.WINDOW_W - 28 - (total - 1) * gap
        ui.draw_text(self.screen, "失误", (x0 - 46, 96), size=18,
                     color=S.CREAM, bold=True)
        for i in range(total):
            ui.draw_heart(self.screen, (x0 + i * gap, 106),
                          radius=9, filled=i < self.mistakes_left)

    def draw_floaters(self):
        for text, x, y, t, color in self.floaters:
            alpha = max(0, 1 - t / 0.9)
            font = ui.get_font(20, bold=True)
            img = font.render(text, True, color)
            img.set_alpha(int(255 * alpha))
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)

    def _draw_overlay(self, heading, heading_color):
        veil = pygame.Surface((S.WINDOW_W, S.WINDOW_H), pygame.SRCALPHA)
        veil.fill((10, 12, 30, 205))
        self.screen.blit(veil, (0, 0))
        panel = pygame.Rect(0, 0, 440, 330)
        panel.center = (S.WINDOW_W // 2, 365)
        ui.draw_rounded_panel(self.screen, panel)
        ui.draw_text(self.screen, heading, (panel.centerx, panel.y + 60),
                     size=38, color=heading_color, bold=True, center=True)
        return panel

    def _draw_stars_big(self, cy):
        for k in range(3):
            filled = k < self.last_stars
            # 简单的依次弹出效果
            pop = min(1.0, max(0.0, (self.now - self.clear_at) * 3 - k * 0.25))
            radius = int(26 * (0.6 + 0.4 * pop)) if pop > 0 else 16
            ui.draw_star(self.screen,
                         (S.WINDOW_W // 2 - 64 + k * 64, cy),
                         radius=radius, filled=filled)

    def draw_clear(self):
        self._draw_overlay("关卡通过！", S.GOLD_HI)
        self._draw_stars_big(320)
        ui.draw_text(self.screen,
                     f"用时 {fmt_time(self.elapsed)}　步数 {self.moves}",
                     (S.WINDOW_W // 2, 390), size=20,
                     color=S.CREAM, center=True)
        ui.draw_text(self.screen, "零失误三星，失误一次两星",
                     (S.WINDOW_W // 2, 428), size=15,
                     color=(180, 188, 216), center=True, shadow=False)
        self.next_btn.draw(self.screen)

    def draw_all_clear(self):
        self._draw_overlay(
            "七元素试炼完成！" if self.mode == "campaign" else "随机试炼完成！",
            S.GOLD_HI)
        if self.mode == "campaign":
            total = sum(self.save_data["stars"].values())
            ui.draw_text(self.screen, f"累计星级 {total} / {len(LEVELS) * 3}",
                         (S.WINDOW_W // 2, 386), size=20,
                         color=S.GOLD_HI, center=True)
        else:
            ui.draw_text(self.screen, "你解开了这局随机棋盘",
                         (S.WINDOW_W // 2, 386), size=20,
                         color=S.CREAM, center=True)
        ui.draw_text(self.screen,
                     f"本局用时 {fmt_time(self.elapsed)}　步数 {self.moves}",
                     (S.WINDOW_W // 2, 424), size=19,
                     color=S.CREAM, center=True)
        self.again_btn.label = "再来一局" if self.mode == "random" else "再玩一次"
        self.again_btn.draw(self.screen)
        self.over_menu_btn.draw(self.screen)

    def draw_failed(self):
        self._draw_overlay("挑战失败", (255, 120, 130))
        ui.draw_text(self.screen, "失误次数已耗尽，再试一次吧",
                     (S.WINDOW_W // 2, 392), size=20, color=S.CREAM, center=True)
        self.fail_restart_btn.draw(self.screen)
        self.fail_menu_btn.draw(self.screen)

    # —— 主循环 ——
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(S.FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
