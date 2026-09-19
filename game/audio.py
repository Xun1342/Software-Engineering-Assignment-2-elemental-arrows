# -*- coding: utf-8 -*-
"""音效管理：加载 assets/sounds 下由 tools/gen_sounds.py 合成的原创 WAV。

音频设备不可用时自动静音，不影响游戏运行。
"""

import os

import pygame

_SOUND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "sounds",
)


class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False
        if self.enabled:
            for name in ("click", "fly", "blocked", "win", "fail"):
                path = os.path.join(_SOUND_DIR, f"{name}.wav")
                if os.path.exists(path):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(path)
                    except pygame.error:
                        pass

    def play(self, name):
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()
