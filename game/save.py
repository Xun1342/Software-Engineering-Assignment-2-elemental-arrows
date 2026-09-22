# -*- coding: utf-8 -*-
"""本地存档：关卡星级、最佳成绩与解锁进度（项目根目录 save.json）。"""

import json
import os

SAVE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "save.json",
)

_DEFAULT = {"stars": {}, "best": {}, "unlocked": 1}


def load():
    """读取存档，文件缺失或损坏时返回默认值。"""
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("stars", {})
        data.setdefault("best", {})
        data.setdefault("unlocked", 1)
        return data
    except (OSError, ValueError):
        return dict(_DEFAULT)


def save(data):
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def compute_stars(mistakes_total, mistakes_left):
    """按失误次数评星：零失误三星，失误一次两星，其余一星。"""
    used = mistakes_total - mistakes_left
    if used <= 0:
        return 3
    if used == 1:
        return 2
    return 1


def record_clear(data, index, stars, elapsed, moves, total_levels):
    """记录一次通关：更新最高星级、最佳成绩、解锁进度，返回是否新纪录。"""
    key = str(index)
    old_stars = data["stars"].get(key, 0)
    data["stars"][key] = max(old_stars, stars)
    best = data["best"].get(key)
    record = {"time": round(elapsed, 1), "moves": moves}
    new_record = best is None or elapsed < best.get("time", 1e9)
    if new_record:
        data["best"][key] = record
    data["unlocked"] = max(data["unlocked"],
                           min(index + 2, total_levels))
    save(data)
    return new_record
