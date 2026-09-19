# -*- coding: utf-8 -*-
"""游戏主程序：窗口、主循环、HUD、碰撞反馈、失误与失败/重开（第三阶段）。"""

import pygame

from . import settings as S
from .audio import SoundManager
from .board import Board
from .levels import LEVELS
from . import ui


class App:
    # 场景状态：playing（游戏中）/ failed（本关失败）
    STATE_PLAYING = "playing"
    STATE_FAILED = "failed"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()

        self.level_index = 0
        self.now = 0.0
        self.floaters = []        # 飘字提示 [(文字, x, y, t, 颜色)]
        self.flash_t = 0.0        # 红屏闪烁计时
        self.restart_btn = ui.Button((180, 742, 180, 52), "重新开始")
        self.load_level(0)

    # —— 关卡装载 / 重开 ——
    def load_level(self, index):
        self.level_index = index
        self.level = LEVELS[index]
        self.board = Board(self.level)
        self.mistakes_left = self.level["mistakes"]
        self.state = self.STATE_PLAYING
        self.floaters.clear()
        self.flash_t = 0.0
        self.restart_btn.rect = pygame.Rect(180, 742, 180, 52)

    def add_floater(self, text, pos, color=(255, 150, 150)):
        self.floaters.append([text, pos[0], pos[1], 0.0, color])

    # —— 事件 ——
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.state == self.STATE_FAILED:
                if self.restart_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(self.level_index)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.restart_btn.handle_event(event):
                    self.sound.play("click")
                    self.load_level(self.level_index)
                else:
                    self.on_click(event.pos)
            else:
                self.restart_btn.handle_event(event)
        return True

    def on_click(self, pos):
        """点击箭头：无阻挡则飞出；被阻挡则碰撞反馈并消耗一次失误。"""
        if self.board.is_animating() or self.state != self.STATE_PLAYING:
            return
        arrow = self.board.arrow_at(pos)
        if arrow is None:
            return
        if self.board.is_clear_to_edge(arrow):
            arrow.launch()
            self.sound.play("fly")
            self.add_floater("飞出", self.board.cell_center(arrow.row, arrow.col),
                             color=S.GOLD_HI)
        else:
            # 碰撞：箭头晃动 + 红屏 + 飘字 + 消耗失误
            arrow.bump()
            self.mistakes_left -= 1
            self.flash_t = 0.45
            self.sound.play("blocked")
            self.add_floater("阻挡！", self.board.cell_center(arrow.row, arrow.col))
            if self.mistakes_left <= 0:
                # 等晃动动画播完再弹失败界面
                self.fail_at = self.now + S.SHAKE_DURATION + 0.15
                self.state = "failing"
                self.sound.play("fail")

    # —— 更新 ——
    def update(self, dt):
        self.now += dt
        self.board.update(dt, self.now)
        if self.flash_t > 0:
            self.flash_t = max(0.0, self.flash_t - dt)
        for f in self.floaters:
            f[2] -= 34 * dt
            f[3] += dt
        self.floaters = [f for f in self.floaters if f[3] < 0.9]

        if self.state == "failing" and self.now >= self.fail_at:
            self.state = self.STATE_FAILED

    # —— 绘制 ——
    def draw(self):
        self.screen.fill((18, 22, 44))
        self.draw_hud()
        self.board.draw(self.screen, self.now, hover_pos=pygame.mouse.get_pos())
        self.draw_floaters()
        self.restart_btn.draw(self.screen)
        if self.flash_t > 0:
            alpha = int(110 * (self.flash_t / 0.45))
            veil = pygame.Surface((S.WINDOW_W, S.WINDOW_H), pygame.SRCALPHA)
            veil.fill((210, 60, 70, alpha))
            self.screen.blit(veil, (0, 0))
        if self.state == self.STATE_FAILED:
            self.draw_failed()
        pygame.display.flip()

    def draw_hud(self):
        accent = S.ELEMENTS[self.level["accent"]][1]
        ui.draw_text(self.screen, self.level["name"],
                     (S.WINDOW_W // 2, 46), size=30, color=S.GOLD_HI,
                     bold=True, center=True)
        ui.draw_text(self.screen, f"剩余箭头 {self.board.remaining()}",
                     (30, 108), size=22, color=accent, bold=True)
        # 失误次数：元素心
        total = self.level["mistakes"]
        x0 = S.WINDOW_W - 34 - (total - 1) * 30
        ui.draw_text(self.screen, "失误", (x0 - 52, 108), size=20,
                     color=S.CREAM, bold=True)
        for i in range(total):
            ui.draw_heart(self.screen, (x0 + i * 30, 119),
                          radius=11, filled=i < self.mistakes_left)

    def draw_floaters(self):
        for text, x, y, t, color in self.floaters:
            alpha = max(0, 1 - t / 0.9)
            font = ui.get_font(22, bold=True)
            img = font.render(text, True, color)
            img.set_alpha(int(255 * alpha))
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)

    def draw_failed(self):
        veil = pygame.Surface((S.WINDOW_W, S.WINDOW_H), pygame.SRCALPHA)
        veil.fill((10, 12, 30, 200))
        self.screen.blit(veil, (0, 0))
        panel = pygame.Rect(0, 0, 380, 250)
        panel.center = (S.WINDOW_W // 2, 380)
        ui.draw_rounded_panel(self.screen, panel)
        ui.draw_text(self.screen, "挑战失败", panel.move(0, -70).center,
                     size=38, color=(255, 120, 130), bold=True, center=True)
        ui.draw_text(self.screen, "失误次数已耗尽，再试一次吧",
                     panel.move(0, -18).center, size=20, color=S.CREAM,
                     center=True)
        self.restart_btn.rect.center = panel.move(0, 58).center
        self.restart_btn.draw(self.screen)

    # —— 主循环 ——
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(S.FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
