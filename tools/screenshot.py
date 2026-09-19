# -*- coding: utf-8 -*-
"""无头渲染截图工具：在 dummy 视频/音频驱动下实例化游戏并保存当前画面。

用法：
    python tools/screenshot.py [shot_name]
用于在无显示器环境下检查界面布局。
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game.app import App  # noqa: E402


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "screen"
    app = App()
    # 推进若干帧，让待机动画稳定
    for _ in range(30):
        app.update(1 / 60)
    app.draw()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.png")
    pygame.image.save(app.screen, path)
    print("saved:", path)


if __name__ == "__main__":
    main()
