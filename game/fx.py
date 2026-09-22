# -*- coding: utf-8 -*-
"""奇幻粒子特效：环境光点、飞出星光爆发、碰撞火星、通关彩屑。

全部由程序绘制，不使用任何外部素材。
"""

import math
import random

import pygame

from . import settings as S
from . import ui


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size",
                 "color", "kind", "spin", "gravity")

    def __init__(self, x, y, vx, vy, life, size, color, kind="dot",
                 gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.kind = kind
        self.spin = random.uniform(0, math.tau)
        self.gravity = gravity


class ParticleManager:
    def __init__(self, w, h, n_ambient=26, seed=7):
        self.w = w
        self.h = h
        rng = random.Random(seed)
        self.rng = rng
        self.particles = []
        self.ambient = []
        for _ in range(n_ambient):
            color = S.ELEMENTS[rng.randrange(len(S.ELEMENTS))][1]
            self.ambient.append({
                "x": rng.uniform(0, w), "y": rng.uniform(0, h),
                "speed": rng.uniform(6, 18),
                "sway": rng.uniform(4, 14), "phase": rng.uniform(0, math.tau),
                "size": rng.uniform(1.6, 3.2), "color": color,
            })

    # —— 生成事件 ——
    def burst(self, pos, colors=None, n=16, speed=150, stars=True):
        """箭头飞出时的星光爆发。"""
        colors = colors or [S.GOLD_HI, S.GOLD, (255, 246, 200)]
        for i in range(n):
            ang = self.rng.uniform(0, math.tau)
            spd = self.rng.uniform(speed * 0.3, speed)
            kind = "star" if stars and i % 3 == 0 else "dot"
            self.particles.append(Particle(
                pos[0], pos[1], math.cos(ang) * spd, math.sin(ang) * spd,
                self.rng.uniform(0.4, 0.8), self.rng.uniform(2, 4.5),
                self.rng.choice(colors), kind=kind, gravity=60))

    def blocked_burst(self, pos):
        """被阻挡时的红色火星。"""
        for i in range(12):
            ang = self.rng.uniform(math.pi * 1.1, math.pi * 1.9)
            spd = self.rng.uniform(50, 150)
            self.particles.append(Particle(
                pos[0], pos[1], math.cos(ang) * spd, math.sin(ang) * spd,
                self.rng.uniform(0.3, 0.6), self.rng.uniform(2, 4),
                self.rng.choice([(255, 110, 110), (255, 160, 90),
                                 (255, 200, 120)]),
                kind="dot", gravity=220))

    def confetti(self, n=70):
        """通关彩屑，从屏幕顶部洒落。"""
        for _ in range(n):
            color = S.ELEMENTS[self.rng.randrange(len(S.ELEMENTS))][1]
            self.particles.append(Particle(
                self.rng.uniform(0, self.w),
                self.rng.uniform(-80, -10),
                self.rng.uniform(-25, 25), self.rng.uniform(50, 110),
                self.rng.uniform(2.2, 4.0), self.rng.uniform(3, 6),
                color, kind="confetti", gravity=24))

    def clear_front(self):
        self.particles.clear()

    # —— 更新 ——
    def update(self, dt):
        for m in self.ambient:
            m["y"] -= m["speed"] * dt
            m["phase"] += dt
            if m["y"] < -6:
                m["y"] = self.h + 6
                m["x"] = self.rng.uniform(0, self.w)
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            if p.kind == "confetti":
                p.x += p.vx * dt + math.sin(p.spin + p.life * 4) * 18 * dt
                p.spin += dt * 5
            else:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx *= 0.96
                p.vy *= 0.96
            alive.append(p)
        self.particles = alive

    # —— 绘制 ——
    def draw_behind(self, surf, now):
        """环境光点：画在棋盘下层。"""
        for m in self.ambient:
            x = m["x"] + math.sin(now * 0.8 + m["phase"]) * m["sway"] * 0.4
            alpha = int(90 + 80 * (0.5 + 0.5 * math.sin(now * 2 + m["phase"])))
            r = m["size"]
            glow = pygame.Surface((int(r * 6), int(r * 6)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*m["color"], alpha // 3),
                               glow.get_rect().center, int(r * 3))
            pygame.draw.circle(glow, (*m["color"], alpha),
                               glow.get_rect().center, int(r))
            surf.blit(glow, (x - r * 3, m["y"] - r * 3))

    def draw_front(self, surf):
        """爆发粒子与彩屑：画在棋盘上层。"""
        for p in self.particles:
            t = max(0.0, p.life / p.max_life)
            alpha = int(255 * t)
            if p.kind == "star":
                pts = ui.star_points((p.x, p.y), p.size * 1.6,
                                     radius_inner=p.size * 0.7, points=4,
                                     rotation=p.spin)
                s = pygame.Surface((int(p.size * 4), int(p.size * 4)),
                                   pygame.SRCALPHA)
                shifted = [(x - p.x + p.size * 2, y - p.y + p.size * 2)
                           for x, y in pts]
                pygame.draw.polygon(s, (*p.color, alpha), shifted)
                surf.blit(s, (p.x - p.size * 2, p.y - p.size * 2))
            elif p.kind == "confetti":
                w = p.size * (1 + 0.6 * math.sin(p.spin))
                s = pygame.Surface((max(1, int(w * 2)), max(1, int(p.size * 2))),
                                   pygame.SRCALPHA)
                s.fill((*p.color, alpha))
                surf.blit(s, (p.x - w, p.y - p.size))
            else:
                s = pygame.Surface((int(p.size * 2), int(p.size * 2)),
                                   pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.color, alpha),
                                   (int(p.size), int(p.size)), int(p.size))
                surf.blit(s, (p.x - p.size, p.y - p.size))
