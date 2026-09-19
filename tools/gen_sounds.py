# -*- coding: utf-8 -*-
"""
gen_sounds.py —— 使用 Python 标准库合成游戏所需的全部音效（原创素材）。

不使用任何商业游戏音频，所有声音均由数学波形（正弦波 / 包络 / 频率扫频）
实时合成并写入 assets/sounds 目录，可重复运行。

依赖：仅 Python 标准库（wave, math, struct）。
"""

import math
import os
import struct
import wave

SR = 44100  # 采样率


def _env(t, dur, attack=0.008, release=0.08):
    """简单的起音/释音包络，避免爆音。"""
    if t < attack:
        return t / attack
    if t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0


def tone(freq_func, dur, volume=0.35, harmonics=((1.0, 1.0),)):
    """生成一段单音，freq_func 可以是固定频率或随时间变化的函数。"""
    n = int(SR * dur)
    frames = []
    for i in range(n):
        t = i / SR
        f = freq_func(t) if callable(freq_func) else freq_func
        v = 0.0
        for mul, amp in harmonics:
            v += amp * math.sin(2 * math.pi * f * mul * t)
        v *= volume * _env(t, dur)
        frames.append(v)
    return frames


def seq(*parts):
    """首尾拼接多段声音。"""
    out = []
    for p in parts:
        out.extend(p)
    return out


def save(name, samples):
    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        frames = b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples
        )
        wf.writeframes(frames)
    print("written:", path)


def main():
    # 1. 点击：短促轻柔的水滴声
    click = tone(lambda t: 660 - 200 * (t / 0.07), 0.07, volume=0.25)
    save("click.wav", click)

    # 2. 飞出：明亮的上扬滑音（成功消除）
    fly = tone(
        lambda t: 420 + 980 * (t / 0.32) ** 1.4,
        0.32,
        volume=0.3,
        harmonics=((1.0, 1.0), (2.0, 0.25)),
    )
    save("fly.wav", fly)

    # 3. 碰撞：两声低沉的闷响（被阻挡）
    thud1 = tone(lambda t: 150 * 2 ** (-1.2 * t / 0.1), 0.1, volume=0.4)
    thud2 = tone(lambda t: 120 * 2 ** (-1.2 * t / 0.12), 0.12, volume=0.4)
    gap = [0.0] * int(SR * 0.03)
    save("blocked.wav", seq(thud1, gap, thud2))

    # 4. 通关：明亮的上行琶音 C5-E5-G5-C6
    notes = [523.25, 659.25, 783.99, 1046.5]
    arp = []
    for i, f in enumerate(notes):
        part = tone(
            f,
            0.16,
            volume=0.3,
            harmonics=((1.0, 1.0), (2.0, 0.3), (3.0, 0.12)),
        )
        arp.extend(part)
    save("win.wav", arp)

    # 5. 失败：下行小调音 E4-C4-A3-F3
    notes = [329.63, 261.63, 220.0, 174.61]
    desc = []
    for f in notes:
        desc.extend(tone(f, 0.2, volume=0.3, harmonics=((1.0, 1.0), (2.0, 0.2))))
    save("fail.wav", desc)


if __name__ == "__main__":
    main()
