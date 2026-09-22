# -*- coding: utf-8 -*-
"""棋盘与箭头：网格坐标、单格箭头绘制与动画状态。

规则口径（基础版）：网格中的箭头占据单个格子；点击后只判断同一行/同一列上、
箭头朝向到棋盘边界之间是否还存在其他箭头。
"""

import math

import pygame

from . import settings as S

# 箭头表面缓存：(元素下标, 方向, 边长, 是否警示红) -> Surface
_TILE_CACHE = {}


def _rounded(surf, rect, radius, color, width=0):
    """pygame.draw.rect 的圆角封装。"""
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def _arrow_polygon_points(size):
    """朝上箭头的多边形顶点（归一化坐标 × size）。"""
    p = [
        (0.50, 0.12), (0.82, 0.46), (0.63, 0.46),
        (0.63, 0.84), (0.37, 0.84), (0.37, 0.46),
        (0.18, 0.46),
    ]
    return [(x * size, y * size) for x, y in p]


def make_tile(element_idx, direction, size, blocked_style=False):
    """绘制一枚元素宝石风格的单格箭头（带透明通道）。"""
    key = (element_idx, direction, int(size), blocked_style)
    cached = _TILE_CACHE.get(key)
    if cached is not None:
        return cached

    if blocked_style:
        _, light, dark = S.BLOCK_MAIN, S.BLOCK_LIGHT, S.BLOCK_DARK
        main = S.BLOCK_MAIN
    else:
        _, main, light, dark = S.ELEMENTS[element_idx]

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    radius = int(size * 0.22)

    # 宝石底座（主色 + 底部暗色）
    _rounded(surf, (0, 0, size, size), radius, main)
    shade = pygame.Surface((size, size), pygame.SRCALPHA)
    _rounded(shade, (0, size // 2, size, size // 2), radius, (*dark, 90))
    surf.blit(shade, (0, 0))

    # 顶部椭圆高光
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(
        glow, (*light, 95),
        (int(size * 0.12), int(size * 0.06), int(size * 0.76), int(size * 0.5)),
    )
    surf.blit(glow, (0, 0))

    # 描边
    _rounded(surf, (1, 1, size - 2, size - 2), radius, light, width=max(2, size // 22))

    # 左上角一点星光
    pygame.draw.circle(surf, (255, 255, 255, 180),
                       (int(size * 0.26), int(size * 0.24)), max(1, size // 22))

    # 中央箭头：先画暗色投影，再画乳白色箭头，整体按方向旋转
    glyph = pygame.Surface((size, size), pygame.SRCALPHA)
    pts = _arrow_polygon_points(size)
    shadow = [(x + size * 0.02, y + size * 0.03) for x, y in pts]
    pygame.draw.polygon(glyph, (*dark, 180), shadow)
    pygame.draw.polygon(glyph, (250, 250, 246, 245), pts)
    glyph = pygame.transform.rotate(glyph, S.ANGLE[direction])
    rect = glyph.get_rect(center=(size // 2, size // 2))
    surf.blit(glyph, rect)

    _TILE_CACHE[key] = surf
    return surf


class Arrow:
    """单格箭头。动画状态：idle（待机）/ flying（飞出）/ shaking（碰撞晃动）/ gone。"""

    def __init__(self, row, col, direction, element_idx):
        self.row = row
        self.col = col
        self.direction = direction
        self.element_idx = element_idx
        self.state = "idle"
        self.t = 0.0
        self.phase = (row * 7 + col * 3) * 0.37  # 待机动画错相

    # —— 动画触发 ——
    def launch(self):
        self.state = "flying"
        self.t = 0.0

    def bump(self):
        self.state = "shaking"
        self.t = 0.0

    # —— 每帧更新 ——
    def update(self, dt, now):
        self.t += dt
        if self.state == "flying" and self.t >= S.FLY_DURATION:
            self.state = "gone"
        if self.state == "shaking" and self.t >= S.SHAKE_DURATION:
            self.state = "idle"
            self.t = 0.0

    def draw(self, surf, center, cell, now, hovered=False):
        """center 为格子中心像素坐标。"""
        size = int(cell * 0.80)
        dx = dy = 0.0
        scale = 1.0
        alpha = 255

        if self.state == "idle":
            # 轻微上下浮动
            dy = math.sin(now * 2.0 + self.phase) * 2.0
            if hovered:
                scale = 1.10
        elif self.state == "flying":
            p = min(self.t / S.FLY_DURATION, 1.0)
            travel = 820.0 * p * p           # 加速飞出
            vx, vy = S.DIRS[self.direction]
            dx, dy = vx * travel, vy * travel
            scale = 1.0 + 0.22 * p
            alpha = 255 if p < 0.55 else int(255 * max(0.0, 1.0 - (p - 0.55) / 0.45))
        elif self.state == "shaking":
            p = min(self.t / S.SHAKE_DURATION, 1.0)
            vx, vy = S.DIRS[self.direction]
            mag = math.sin(self.t * 46.0) * 10.0 * (1.0 - p)
            dx, dy = vx * mag, vy * mag

        tile = make_tile(self.element_idx, self.direction,
                         max(8, int(size * scale)),
                         blocked_style=self.state == "shaking")
        if alpha < 255:
            tile = tile.copy()
            tile.set_alpha(alpha)

        pos = (int(center[0] + dx), int(center[1] + dy))
        rect = tile.get_rect(center=pos)
        surf.blit(tile, rect)

        # 悬停描金圈
        if hovered and self.state == "idle":
            _rounded(surf, rect.inflate(10, 10), int(size * 0.30),
                     (*S.GOLD_HI, 200), width=3)


class Board:
    """棋盘：维护箭头集合、网格几何与绘制。"""

    def __init__(self, level):
        self.rows = level["rows"]
        self.cols = level["cols"]
        self.arrows = {}
        for i, (r, c, d) in enumerate(level["arrows"]):
            # 元素色按七元素循环分布
            self.arrows[(r, c)] = Arrow(r, c, d, i % len(S.ELEMENTS))
        self.set_panel_rect(pygame.Rect(S.PANEL_RECT))
        self.hint_until = 0.0  # 提示高亮截止时刻

    # —— 快照 / 恢复（撤销功能）——
    def snapshot(self):
        """保存当前所有待机箭头的位置、方向与元素色。"""
        return [(a.row, a.col, a.direction, a.element_idx)
                for a in self.arrows.values() if a.state == "idle"]

    def restore(self, data):
        """根据 snapshot 的数据重建棋盘（撤销到上一步）。"""
        self.arrows = {}
        for r, c, d, element_idx in data:
            self.arrows[(r, c)] = Arrow(r, c, d, element_idx)
        self.hint_until = 0.0

    def show_hint(self, now, duration=S.HINT_DURATION):
        """高亮当前所有可以飞出的箭头。"""
        if self.removable_arrows():
            self.hint_until = now + duration
            return True
        return False

    def set_panel_rect(self, panel_rect):
        self.panel_rect = pygame.Rect(panel_rect)
        w = (self.panel_rect.width - 2 * S.PANEL_PAD) / self.cols
        h = (self.panel_rect.height - 2 * S.PANEL_PAD) / self.rows
        self.cell = min(w, h, S.CELL_MAX)
        gw = self.cell * self.cols
        gh = self.cell * self.rows
        self.origin_x = self.panel_rect.centerx - gw / 2
        self.origin_y = self.panel_rect.centery - gh / 2

    # —— 坐标换算 ——
    def cell_center(self, r, c):
        return (int(self.origin_x + (c + 0.5) * self.cell),
                int(self.origin_y + (r + 0.5) * self.cell))

    def arrow_at(self, pos):
        """根据像素坐标返回该格上的待机箭头，没有则 None。"""
        x, y = pos
        c = int((x - self.origin_x) // self.cell)
        r = int((y - self.origin_y) // self.cell)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            arrow = self.arrows.get((r, c))
            if arrow is not None and arrow.state == "idle":
                return arrow
        return None

    def remaining(self):
        """尚未飞出棋盘的箭头数（含正在飞的）。"""
        return sum(1 for a in self.arrows.values() if a.state != "gone")

    def is_animating(self):
        """是否有箭头正在播放飞出/碰撞动画（动画期间锁定输入）。"""
        return any(a.state in ("flying", "shaking") for a in self.arrows.values())

    def is_clear_to_edge(self, arrow):
        """路径检测（基础版核心规则）。

        判断与箭头同一行（左/右）或同一列（上/下）、沿箭头朝向到棋盘
        边界之间，是否还存在其他箭头：没有阻挡返回 True，可以飞出。
        """
        dc, dr = S.DIRS[arrow.direction]
        r, c = arrow.row + dr, arrow.col + dc
        while 0 <= r < self.rows and 0 <= c < self.cols:
            other = self.arrows.get((r, c))
            if other is not None and other.state != "gone":
                return False
            r += dr
            c += dc
        return True

    def removable_arrows(self):
        """当前所有满足飞出条件的箭头（测试与提示功能使用）。"""
        return [a for a in self.arrows.values()
                if a.state == "idle" and self.is_clear_to_edge(a)]

    # —— 帧更新 ——
    def update(self, dt, now):
        for arrow in list(self.arrows.values()):
            arrow.update(dt, now)
        self.arrows = {
            k: a for k, a in self.arrows.items() if a.state != "gone"
        }

    # —— 绘制 ——
    def draw(self, surf, now, hover_pos=None):
        self._draw_panel(surf)
        hovered = self.arrow_at(hover_pos) if hover_pos else None
        hint_on = now < self.hint_until
        hint_set = set()
        if hint_on:
            hint_set = {id(a) for a in self.removable_arrows()}
        for arrow in self.arrows.values():
            center = self.cell_center(arrow.row, arrow.col)
            arrow.draw(surf, center, self.cell, now, hovered=arrow is hovered)
            if hint_on and id(arrow) in hint_set and arrow.state == "idle":
                pulse = 0.5 + 0.5 * math.sin(now * 8.0 + arrow.phase)
                # 外层柔光 + 内层亮框，双层金色脉动
                for size, alpha, width in (
                    (int(self.cell * 1.02), int(50 + 60 * pulse), 7),
                    (int(self.cell * 0.86), int(150 + 100 * pulse), 3),
                ):
                    rect = pygame.Rect(0, 0, size, size)
                    rect.center = center
                    ring = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(ring, (*S.GOLD_HI, alpha),
                                     ring.get_rect(), width, border_radius=14)
                    surf.blit(ring, rect.topleft)

    def _draw_panel(self, surf):
        r = self.panel_rect
        # 竖向渐变底
        grad = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        for y in range(r.height):
            t = y / r.height
            color = tuple(int(S.PANEL_TOP[i] + (S.PANEL_BOTTOM[i] - S.PANEL_TOP[i]) * t)
                          for i in range(3))
            pygame.draw.line(grad, color, (0, y), (r.width, y))
        panel = grad.copy()
        pygame.draw.rect(panel, (0, 0, 0, 90), panel.get_rect(),
                         border_radius=18, width=0)
        surf.blit(grad, r.topleft)
        pygame.draw.rect(surf, (*S.GOLD, 180), r.inflate(0, 0), 2,
                         border_radius=18)

        # 网格点阵
        dot_color = (120, 130, 170, 90)
        for i in range(self.rows + 1):
            for j in range(self.cols + 1):
                x = int(self.origin_x + j * self.cell)
                y = int(self.origin_y + i * self.cell)
                pygame.draw.circle(surf, dot_color, (x, y), S.DOT_RADIUS)
