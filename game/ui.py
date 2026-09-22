# -*- coding: utf-8 -*-
"""通用 UI：字体、按钮、文字与面板绘制。"""

import os

import pygame

from . import settings as S

_FONT_CACHE = {}
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 Bold
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
]


def get_font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            font = pygame.font.Font(path, size)
            break
    else:
        font = pygame.font.SysFont("microsoftyahei,simhei,sans", size, bold=bold)
    _FONT_CACHE[key] = font
    return font


def draw_text(surf, text, pos, size=22, color=S.CREAM, bold=False,
              center=False, shadow=True, shadow_color=(20, 22, 44)):
    font = get_font(size, bold)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    if shadow:
        sh = font.render(text, True, shadow_color)
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def draw_rounded_panel(surf, rect, fill=(28, 32, 60, 215), border=S.GOLD,
                       radius=18, border_width=2):
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    surf.blit(panel, rect.topleft)
    if border:
        pygame.draw.rect(surf, border, rect, border_width, border_radius=radius)


class Button:
    """金色描边按钮，支持悬停高亮。"""

    def __init__(self, rect, label, size=24, primary=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.size = size
        self.primary = primary
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surf):
        fill = (58, 64, 108, 235) if self.hover else (34, 38, 72, 225)
        if not self.primary:
            fill = (40, 44, 78, 180) if self.hover else (28, 32, 60, 150)
        draw_rounded_panel(surf, self.rect, fill=fill,
                           border=S.GOLD_HI if self.hover else S.GOLD,
                           radius=14, border_width=2)
        color = S.GOLD_HI if self.hover else S.CREAM
        draw_text(surf, self.label, self.rect.center, self.size, color,
                  bold=True, center=True, shadow=False)


def star_points(center, radius_outer, radius_inner=None, points=5, rotation=-90):
    """五角星顶点列表。"""
    import math
    if radius_inner is None:
        radius_inner = radius_outer * 0.45
    cx, cy = center
    out = []
    for i in range(points * 2):
        r = radius_outer if i % 2 == 0 else radius_inner
        ang = math.radians(rotation + i * 180 / points)
        out.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return out


def draw_star(surf, center, radius=18, filled=True, color=None):
    color = color or S.GOLD_HI
    pts = star_points(center, radius)
    if filled:
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, S.GOLD_DARK, pts, 2)
        # 高光
        pygame.draw.circle(surf, (255, 250, 225),
                           (center[0] - radius // 3, center[1] - radius // 3),
                           max(1, radius // 7))
    else:
        pygame.draw.polygon(surf, (86, 90, 120), pts, 3)


def draw_lock(surf, center, size=22):
    """简单的挂锁图案（未解锁关卡用）。"""
    x, y = center
    body = pygame.Rect(x - size // 2, y - size // 6, size, int(size * 0.62))
    pygame.draw.arc(surf, (150, 156, 188),
                    (x - size // 3, y - size // 2, int(size * 0.66), size),
                    3.4, 6.1, 4)
    pygame.draw.rect(surf, (120, 126, 160), body, border_radius=4)
    pygame.draw.circle(surf, (40, 44, 72), (x, y + size // 6), 3)


def draw_heart(surf, center, radius=11, filled=True):
    """画一颗菱形元素心（剩余失误次数）。"""
    x, y = center
    pts = [(x, y + radius), (x + radius, y), (x, y - radius), (x - radius, y)]
    color = S.HEART if filled else S.HEART_EMPTY
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, (60, 40, 60), pts, 1)
    if filled:
        pygame.draw.circle(surf, (255, 200, 205),
                           (x - radius // 3, y - radius // 3), max(1, radius // 5))
