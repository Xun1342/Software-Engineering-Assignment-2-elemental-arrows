# -*- coding: utf-8 -*-
"""游戏主程序：窗口、主循环与场景绘制（第一阶段：棋盘与箭头显示）。"""

import pygame

from . import settings as S
from .audio import SoundManager
from .board import Board
from .levels import LEVELS
from . import ui


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.font = pygame.font.Font(None, 24)

        self.level_index = 0
        self.board = Board(LEVELS[self.level_index])
        self.now = 0.0

    # —— 事件 ——
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    # —— 更新 ——
    def update(self, dt):
        self.now += dt
        self.board.update(dt, self.now)

    # —— 绘制 ——
    def draw(self):
        self.screen.fill((18, 22, 44))
        level = LEVELS[self.level_index]
        accent = S.ELEMENTS[level["accent"]][1]

        ui.draw_text(self.screen, level["name"],
                     (S.WINDOW_W // 2, 46), size=30, color=S.GOLD_HI,
                     bold=True, center=True)
        ui.draw_text(self.screen, f"剩余箭头 {self.board.remaining()}",
                     (34, 108), size=22, color=accent, bold=True)
        self.board.draw(self.screen, self.now, hover_pos=pygame.mouse.get_pos())
        ui.draw_text(self.screen, "观察箭头方向，点击让它飞出棋盘",
                     (S.WINDOW_W // 2, 710), size=20, color=S.CREAM,
                     center=True)
        pygame.display.flip()

    # —— 主循环 ——
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(S.FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
