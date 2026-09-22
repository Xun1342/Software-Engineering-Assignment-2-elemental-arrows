# -*- coding: utf-8 -*-
"""游戏主程序：开始 / 游戏 / 通关 / 失败界面，计时、步数、提示、撤销。"""

import os

import pygame

from . import settings as S
from .audio import SoundManager
from .board import Board
from .levels import LEVELS
from . import ui

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
    PLAYING = "playing"
    FAILING = "failing"      # 最后一次碰撞动画播放中
    FAILED = "failed"
    CLEARING = "clearing"    # 最后一支箭头飞出动画播放中
    CLEAR = "clear"          # 本关通关结算
    ALL_CLEAR = "all_clear"  # 全部关卡通关

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.bg = self._load_bg()

        # —— 菜单 / 结算按钮 ——
        self.start_btn = ui.Button((170, 708, 200, 58), "开始试炼", size=26)
        self.next_btn = ui.Button((170, 500, 200, 54), "下一关", size=24)
        self.again_btn = ui.Button((60, 500, 190, 54), "再玩一次", size=22)
        self.over_menu_btn = ui.Button((290, 500, 190, 54), "返回菜单",
                                       size=22, primary=False)
        self.fail_restart_btn = ui.Button((60, 500, 190, 54), "重新开始", size=22)
        self.fail_menu_btn = ui.Button((290, 500, 190, 54), "返回菜单",
                                       size=22, primary=False)

        # —— 游戏内按钮（棋盘下方一排）——
        self.hint_btn = ui.Button((20, 628, 118, 46), "提 示", size=20)
        self.undo_btn = ui.Button((146, 628, 118, 46), "撤 销", size=20)
        self.restart_btn = ui.Button((272, 628, 118, 46), "重 开", size=20)
        self.menu_btn = ui.Button((398, 628, 122, 46), "菜 单", size=20)

        self.now = 0.0
        self.floaters = []
        self.flash_t = 0.0
        self.state = self.MENU
        self.mode = "campaign"          # campaign / random
        self.level_index = 0
        self.level = LEVELS[0]
        self.board = Board(self.level)
        self.mistakes_left = self.level["mistakes"]
        self.elapsed = 0.0
        self.moves = 0
        self.history = []               # [(棋盘快照, 失误数, 步数), ...]

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
        """装载关卡：index 为关卡编号；level_data 可传自定义（如随机关卡）。"""
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

    def back_to_menu(self):
        self.state = self.MENU
        self.floaters.clear()
        self.flash_t = 0.0

    def add_floater(self, text, pos, color=(255, 150, 150)):
        self.floaters.append([text, pos[0], pos[1], 0.0, color])

    # —— 功能按钮 ——
    def do_hint(self):
        if self.board.is_animating() or self.state != self.PLAYING:
            return
        if self.board.show_hint(self.now):
            self.sound.play("click")
            self.add_floater("金色脉动的箭头可以飞出",
                             (S.WINDOW_W // 2, 620), color=S.GOLD_HI)
        else:
            self.add_floater("当前没有可飞出的箭头",
                             (S.WINDOW_W // 2, 620), color=(255, 170, 170))

    def do_undo(self):
        if self.board.is_animating() or self.state != self.PLAYING:
            return
        if not self.history:
            self.add_floater("没有可撤销的步骤",
                             (S.WINDOW_W // 2, 620), color=(200, 206, 230))
            return
        snap, mistakes, moves = self.history.pop()
        self.board.restore(snap)
        self.mistakes_left = mistakes
        self.moves = moves
        self.sound.play("click")
        self.add_floater("撤销一步", (S.WINDOW_W // 2, 620), color=S.GOLD_HI)

    # —— 事件 ——
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.back_to_menu()
                    continue
                if self.state == self.PLAYING:
                    if event.key == pygame.K_h:
                        self.do_hint()
                    elif event.key == pygame.K_z:
                        self.do_undo()
                    elif event.key == pygame.K_r:
                        self.load_level(
                            self.level_index,
                            None if self.mode == "campaign" else self.level)

            if self.state == self.MENU:
                if self.start_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(0)

            elif self.state in (self.PLAYING, self.FAILING):
                if self.hint_btn.handle_event(event):
                    self.do_hint()
                elif self.undo_btn.handle_event(event):
                    self.do_undo()
                elif self.restart_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(self.level_index,
                                   None if self.mode == "campaign" else self.level)
                elif self.menu_btn.handle_event(event):
                    self.sound.play("click")
                    self.back_to_menu()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                else:
                    for btn in (self.hint_btn, self.undo_btn,
                                self.restart_btn, self.menu_btn):
                        btn.handle_event(event)

            elif self.state == self.FAILED:
                if self.fail_restart_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(self.level_index,
                                   None if self.mode == "campaign" else self.level)
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
                    self.load_level(0)
                elif self.over_menu_btn.handle_event(event):
                    self.sound.play("click")
                    self.back_to_menu()
        return True

    def on_click(self, pos):
        """点击箭头：无阻挡则飞出；被阻挡则碰撞反馈并消耗一次失误。"""
        if self.board.is_animating() or self.state != self.PLAYING:
            return
        arrow = self.board.arrow_at(pos)
        if arrow is None:
            return
        if self.board.is_clear_to_edge(arrow):
            # 记录撤销快照（飞出前的局面）
            self.history.append(
                (self.board.snapshot(), self.mistakes_left, self.moves))
            arrow.launch()
            self.moves += 1
            self.sound.play("fly")
            self.add_floater("飞出", self.board.cell_center(arrow.row, arrow.col),
                             color=S.GOLD_HI)
        else:
            arrow.bump()
            self.mistakes_left -= 1
            self.flash_t = 0.45
            self.sound.play("blocked")
            self.add_floater("阻挡！", self.board.cell_center(arrow.row, arrow.col))
            if self.mistakes_left <= 0:
                self.fail_at = self.now + S.SHAKE_DURATION + 0.15
                self.state = self.FAILING
                self.sound.play("fail")

    # —— 更新 ——
    def update(self, dt):
        self.now += dt
        if self.state != self.MENU:
            self.board.update(dt, self.now)
        if self.state == self.PLAYING:
            self.elapsed += dt
        if self.flash_t > 0:
            self.flash_t = max(0.0, self.flash_t - dt)
        for f in self.floaters:
            f[2] -= 34 * dt
            f[3] += dt
        self.floaters = [f for f in self.floaters if f[3] < 0.9]

        if self.state == self.FAILING and self.now >= self.fail_at:
            self.state = self.FAILED
        elif self.state == self.PLAYING and self.board.remaining() == 0:
            self.state = self.CLEARING
            self.clear_at = self.now + 0.55
            self.sound.play("win")
        elif self.state == self.CLEARING and self.now >= self.clear_at:
            if self.mode == "campaign" and self.level_index + 1 < len(LEVELS):
                self.state = self.CLEAR
            else:
                self.state = self.ALL_CLEAR

    # —— 绘制 ——
    def draw(self):
        if self.state == self.MENU:
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    # —— 开始界面 ——
    def draw_menu(self):
        if self.bg is not None:
            self.screen.blit(self.bg, (0, 0))
        else:
            self.screen.fill((18, 22, 44))
        veil = pygame.Surface((S.WINDOW_W, 420), pygame.SRCALPHA)
        veil.fill((14, 18, 42, 150))
        self.screen.blit(veil, (0, S.WINDOW_H - 420))

        ui.draw_text(self.screen, "元素之箭", (S.WINDOW_W // 2, 120),
                     size=60, color=S.GOLD_HI, bold=True, center=True)
        ui.draw_text(self.screen, "七元素 · 一箭又一箭", (S.WINDOW_W // 2, 188),
                     size=24, color=S.CREAM, center=True)

        x0 = 70
        gap = (S.WINDOW_W - 2 * x0) / 6
        for i, (name, main, light, dark) in enumerate(S.ELEMENTS):
            cx = int(x0 + i * gap)
            cy = 268
            pts = [(cx, cy - 16), (cx + 13, cy), (cx, cy + 16), (cx - 13, cy)]
            pygame.draw.polygon(self.screen, main, pts)
            pygame.draw.polygon(self.screen, light, pts, 2)
            ui.draw_text(self.screen, name, (cx, cy + 30), size=18,
                         color=S.CREAM, center=True, shadow=False)

        panel = pygame.Rect(40, 360, S.WINDOW_W - 80, 270)
        ui.draw_rounded_panel(self.screen, panel, fill=(20, 24, 52, 205))
        ui.draw_text(self.screen, "玩法说明", (S.WINDOW_W // 2, 388),
                     size=24, color=S.GOLD_HI, bold=True, center=True)
        lines = [
            "· 点击棋盘上的元素箭头",
            "· 箭头朝向到边界之间没有其他箭头时，即可飞出棋盘",
            "· 被其他箭头挡住会晃动警示，并消耗一次失误",
            "· 清空全部箭头通关；失误耗尽则本关失败",
            "· 善用提示与撤销，零失误通关可获得三星评价",
        ]
        for i, line in enumerate(lines):
            ui.draw_text(self.screen, line, (66, 432 + i * 36),
                         size=18, color=S.CREAM, shadow=False)

        self.start_btn.draw(self.screen)
        ui.draw_text(self.screen, "美术背景由 AI 生成、音效与界面由程序原创合成",
                     (S.WINDOW_W // 2, 812), size=15, color=(190, 196, 220),
                     center=True, shadow=False)

    # —— 游戏界面 ——
    def draw_game(self):
        self.screen.fill((18, 22, 44))
        self.draw_hud()
        self.board.draw(self.screen, self.now, hover_pos=pygame.mouse.get_pos())
        self.draw_floaters()
        for btn in (self.hint_btn, self.undo_btn,
                    self.restart_btn, self.menu_btn):
            btn.draw(self.screen)
        ui.draw_text(self.screen, "提示：金色脉动描边的箭头当前可以飞出",
                     (S.WINDOW_W // 2, 700), size=16,
                     color=(180, 188, 216), center=True, shadow=False)
        ui.draw_text(self.screen, "快捷键：H 提示　Z 撤销　R 重开　Esc 菜单",
                     (S.WINDOW_W // 2, 726), size=15,
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
        panel = pygame.Rect(0, 0, 440, 340)
        panel.center = (S.WINDOW_W // 2, 380)
        ui.draw_rounded_panel(self.screen, panel)
        ui.draw_text(self.screen, heading, (panel.centerx, panel.y + 70),
                     size=38, color=heading_color, bold=True, center=True)
        return panel

    def draw_clear(self):
        self._draw_overlay("关卡通过！", S.GOLD_HI)
        ui.draw_text(self.screen, "全部箭头已飞出棋盘",
                     (S.WINDOW_W // 2, 386), size=20, color=S.CREAM, center=True)
        ui.draw_text(self.screen,
                     f"用时 {fmt_time(self.elapsed)}　步数 {self.moves}",
                     (S.WINDOW_W // 2, 424), size=19,
                     color=S.GOLD_HI, center=True)
        self.next_btn.draw(self.screen)

    def draw_all_clear(self):
        self._draw_overlay("七元素试炼完成！", S.GOLD_HI)
        ui.draw_text(self.screen, "你解开了全部关卡",
                     (S.WINDOW_W // 2, 386), size=20, color=S.CREAM, center=True)
        ui.draw_text(self.screen,
                     f"本局用时 {fmt_time(self.elapsed)}　步数 {self.moves}",
                     (S.WINDOW_W // 2, 424), size=19,
                     color=S.GOLD_HI, center=True)
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
