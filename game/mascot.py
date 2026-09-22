# -*- coding: utf-8 -*-
"""原创白色小精灵「灵灵」——游戏向导。

形象为程序绘制的赛璐璐风白色漂浮精灵：圆身体、两只小翅膀、
头顶四角星天线（非光环），会眨眼、扑翅、浮动，带有 idle/happy/
alert/sad/celebrate 五种状态，全部由几何图形原创绘制，不使用任何
商业游戏素材。
"""

import math

import pygame

from . import settings as S
from . import ui

BODY = (250, 250, 253)
BODY_2 = (226, 236, 252)
OUTLINE = (74, 84, 122)
PINK = (255, 168, 190)
STAR_C = (255, 214, 92)

# 状态常量
IDLE = "idle"
HAPPY = "happy"
ALERT = "alert"
SAD = "sad"
CELEBRATE = "celebrate"


class Mascot:
    def __init__(self):
        self.state = IDLE
        self.until = 0.0
        self.bubble_text = None
        self.bubble_until = 0.0

    def set_state(self, state, now, duration=1.4):
        self.state = state
        self.until = now + duration

    def say(self, text, now, duration=2.2):
        self.bubble_text = text
        self.bubble_until = now + duration

    def _resolve_state(self, now):
        if self.state != IDLE and now >= self.until:
            self.state = IDLE
        return self.state

    # —— 绘制 ——
    def draw(self, surf, center, now, state=None, scale=1.0):
        if state is not None:
            self.state = state
        st = self._resolve_state(now)
        cx, cy = center
        bob = math.sin(now * 2.2) * 3
        cy += bob
        cx = int(cx)
        cy = int(cy)
        r = int(24 * scale)

        # 地面柔光
        glow = pygame.Surface((r * 4, r * 2), pygame.SRCALPHA)
        for i, a in enumerate((26, 18, 10)):
            pygame.draw.ellipse(
                glow, (120, 150, 220, a),
                (i * 6, r // 2 + i * 4, r * 4 - i * 12, r // 2 - i * 2))
        surf.blit(glow, (cx - r * 2, cy + r - r // 4))

        # 翅膀（在身体之前画，像从背后伸出）
        flap = math.sin(now * 6.5) * 0.25 + (0.3 if st == HAPPY else 0.0) \
            + (0.5 if st == CELEBRATE else 0.0)
        self._draw_wing(surf, cx - r + 2, cy - r // 3, r, -1, flap, now)
        self._draw_wing(surf, cx + r - 2, cy - r // 3, r, 1, flap, now)

        # 天线 + 四角星
        sway = math.sin(now * 1.8) * 0.12
        tx = cx + int(math.sin(sway) * 6)
        ty = cy - r - int(14 * scale)
        pygame.draw.line(surf, OUTLINE, (cx, cy - r + 2), (tx, ty + 4), 2)
        sp = ui.star_points((tx, ty), int(7 * scale),
                            radius_inner=int(3 * scale), points=4, rotation=now*40)
        twinkle = 0.7 + 0.3 * math.sin(now * 5)
        star_surf = pygame.Surface((24 * scale, 24 * scale), pygame.SRCALPHA)
        pts = [(x - tx + 12 * scale, y - ty + 12 * scale) for x, y in sp]
        pygame.draw.polygon(star_surf,
                            (255, 224, 120, int(255 * twinkle)), pts)
        pygame.draw.polygon(star_surf, OUTLINE, pts, 1)
        surf.blit(star_surf, (tx - 12 * scale, ty - 12 * scale))

        # 身体（描边 + 白色椭圆 + 右下赛璐璐阴影）
        pygame.draw.circle(surf, OUTLINE, (cx, cy), r + 2)
        pygame.draw.circle(surf, BODY, (cx, cy), r)
        shade = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(shade, (*BODY_2, 200), (r + 3, r + 5), r - 2)
        mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
        shade.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(shade, (cx - r, cy - r))
        # 头顶高光
        hl = pygame.Surface((r * 2, r), pygame.SRCALPHA)
        pygame.draw.ellipse(hl, (255, 255, 255, 130),
                            (r // 2, 3, r, r // 2))
        surf.blit(hl, (cx - r, cy - r))

        # 两只小脚
        for sgn in (-1, 1):
            pygame.draw.ellipse(
                surf, OUTLINE,
                (cx + sgn * r // 2 - 6, cy + r - 4, 12, 8))
            pygame.draw.ellipse(
                surf, BODY,
                (cx + sgn * r // 2 - 5, cy + r - 5, 10, 7))

        # 腮红
        for sgn in (-1, 1):
            cheek = pygame.Surface((14, 9), pygame.SRCALPHA)
            pygame.draw.ellipse(cheek, (*PINK, 150), cheek.get_rect())
            surf.blit(cheek, (cx + sgn * r // 2 - 7 + sgn * 6, cy + 4))

        self._draw_face(surf, cx, cy, r, st, now)

    def _draw_wing(self, surf, x, y, r, side, flap, now):
        """side: -1 左 / 1 右。"""
        w = int(r * 0.95)
        h = int(r * 0.62)
        wing = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
        ang = -side * (0.5 + flap)
        pts = [(0, 0),
               (side * w, -h * 0.7 * math.cos(ang)),
               (side * w * 0.7, h * 0.5)]
        pts = [(int(px + w), int(py + h)) for px, py in pts]
        pygame.draw.polygon(wing, OUTLINE, pts)
        inner = [(w, h),
                 (int(w + side * w * 0.86), int(h - h * 0.5)),
                 (int(w + side * w * 0.58), int(h + h * 0.34))]
        pygame.draw.polygon(wing, BODY, inner)
        # 羽毛分隔线
        pygame.draw.line(wing, BODY_2,
                         (w, h),
                         (int(w + side * w * 0.8), int(h - h * 0.1)), 2)
        surf.blit(wing, (x - w, y - h))

    def _draw_face(self, surf, cx, cy, r, st, now):
        eye_dx, eye_y = int(r * 0.38), -int(r * 0.12)
        blink = (now % 3.6) < 0.12 and st in (IDLE, ALERT)
        if st == HAPPY or st == CELEBRATE or blink:
            # ^ ^ 笑眼
            for sgn in (-1, 1):
                ex = cx + sgn * eye_dx
                pygame.draw.arc(surf, OUTLINE,
                                (ex - 6, eye_y - 6, 12, 12),
                                math.radians(200), math.radians(340), 3)
        elif st == SAD:
            for sgn in (-1, 1):
                ex = cx + sgn * eye_dx
                pygame.draw.arc(surf, OUTLINE,
                                (ex - 6, eye_y - 2, 12, 12),
                                math.radians(20), math.radians(160), 3)
            # 泪珠
            if int(now * 2) % 3 == 0:
                ty = eye_y + 10 + int((now * 22) % 12)
                pygame.draw.circle(surf, (130, 190, 255), (cx - eye_dx, ty), 3)
        else:
            for sgn in (-1, 1):
                ex = cx + sgn * eye_dx
                pygame.draw.circle(surf, OUTLINE, (ex, eye_y), 5)
                pygame.draw.circle(surf, (30, 36, 60), (ex, eye_y), 4)
                pygame.draw.circle(surf, (255, 255, 255), (ex - 1, eye_y - 2), 2)
            if st == ALERT:
                # 惊讶：抬高眉毛
                for sgn in (-1, 1):
                    ex = cx + sgn * eye_dx
                    pygame.draw.line(surf, OUTLINE,
                                     (ex - 6, eye_y - 10), (ex + 5, eye_y - 12), 2)

        # 嘴
        mx, my = cx, cy + int(r * 0.28)
        if st == CELEBRATE:
            pygame.draw.circle(surf, (150, 70, 90), (mx, my - 1), 5)
            pygame.draw.circle(surf, (255, 190, 200), (mx, my + 1), 3)
        elif st == HAPPY:
            pygame.draw.arc(surf, OUTLINE, (mx - 7, my - 8, 14, 14),
                            math.radians(20), math.radians(160), 2)
        elif st == SAD:
            pygame.draw.arc(surf, OUTLINE, (mx - 6, my + 2, 12, 10),
                            math.radians(200), math.radians(340), 2)
        else:
            pygame.draw.arc(surf, OUTLINE, (mx - 6, my - 6, 12, 10),
                            math.radians(20), math.radians(160), 2)

    # —— 对话气泡 ——
    def draw_bubble(self, surf, now, center, width=210):
        if self.bubble_text is None or now >= self.bubble_until:
            return
        t_left = self.bubble_until - now
        alpha = 255 if t_left > 0.35 else int(255 * t_left / 0.35)
        font = ui.get_font(17)
        lines = ui.wrap_text(self.bubble_text, font, width - 24)
        lh = 24
        h = 18 + lh * len(lines)
        rect = pygame.Rect(0, 0, width, h)
        rect.center = center
        layer = pygame.Surface((width + 40, h + 30), pygame.SRCALPHA)
        lr = rect.move(20 - rect.x, 12 - rect.y)
        pygame.draw.rect(layer, (255, 255, 255, alpha), lr,
                         border_radius=14)
        pygame.draw.rect(layer, (90, 100, 140, alpha), lr, 2,
                         border_radius=14)
        # 小尾巴
        tail = [(lr.centerx - 8, lr.bottom - 1),
                (lr.centerx + 8, lr.bottom - 1),
                (lr.centerx, lr.bottom + 12)]
        pygame.draw.polygon(layer, (255, 255, 255, alpha), tail)
        pygame.draw.lines(layer, (90, 100, 140, alpha), False,
                          [tail[0], tail[2], tail[1]], 2)
        for i, line in enumerate(lines):
            img = font.render(line, True, (50, 56, 86))
            img.set_alpha(alpha)
            layer.blit(img, (lr.x + 12, lr.y + 9 + i * lh))
        surf.blit(layer, (rect.x - 20, rect.y - 12))
