# -*- coding: utf-8 -*-
"""提交辅助脚本（开发工具）：用 dulwich 暂存全部受版本控制的文件并提交。

用法：
    python tools/make_commit.py "feat: 完成游戏棋盘和箭头显示"

仓库不存在时会自动 git init。生成的是标准 Git 仓库，可直接关联 GitHub 远程。
"""

import os
import sys

from dulwich import porcelain
from dulwich.repo import Repo

AUTHOR = b"elemental-dev <dev@local>"


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    message = sys.argv[1]

    git_dir = os.path.join(root, ".git")
    if os.path.isdir(git_dir):
        repo = Repo(root)
    else:
        repo = porcelain.init(root)

    porcelain.add(repo, paths=[root])
    porcelain.commit(
        repo,
        message=message.encode("utf-8"),
        author=AUTHOR,
        committer=AUTHOR,
    )
    new_head = repo.head().decode("ascii")
    print(f"committed {new_head[:10]}  {message}")


if __name__ == "__main__":
    main()
