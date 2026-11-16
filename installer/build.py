# -*- coding: utf-8 -*-
"""Сборка NEON SNAKE: игра + установщик в dist/.

Запуск из папки проекта:
    python installer/build.py
"""

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
GAME_SRC = os.path.join(ROOT, "neon_snake.py")
SETUP_SRC = os.path.join(ROOT, "installer", "setup_app.py")
ICON = os.path.join(ROOT, "assets", "neon_snake.ico")
GAME_EXE = os.path.join(DIST, "NeonSnake.exe")
SETUP_EXE = os.path.join(DIST, "NeonSnakeSetup.exe")


def run(args):
    print("+ " + " ".join(args), flush=True)
    code = subprocess.call(args, cwd=ROOT)
    if code != 0:
        raise SystemExit("build failed with code %d" % code)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main():
    os.makedirs(DIST, exist_ok=True)

    if not os.path.isfile(ICON):
        run([sys.executable, os.path.join(ROOT, "installer", "make_icon.py")])

    common = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
              "--onefile", "--noupx", "--distpath", DIST]

    run(common + ["--windowed", "--name", "NeonSnake",
                  "--icon", ICON,
                  "--workpath", os.path.join(BUILD, "game"),
                  "--specpath", os.path.join(BUILD, "game"),
                  GAME_SRC])

    run(common + ["--console", "--name", "NeonSnakeSetup",
                  "--icon", ICON,
                  "--add-data", GAME_EXE + ";payload",
                  "--workpath", os.path.join(BUILD, "setup"),
                  "--specpath", os.path.join(BUILD, "setup"),
                  SETUP_SRC])

    for path in (GAME_EXE, SETUP_EXE):
        if not os.path.isfile(path):
            raise SystemExit("missing build result: " + path)
        print("%s  %8.1f MB  %s" % (sha256(path), os.path.getsize(path) / 1e6, path))


if __name__ == "__main__":
    main()
