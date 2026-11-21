# -*- coding: utf-8 -*-
"""NEON SNAKE — установщик и средство восстановления.

Собирается в NeonSnakeSetup.exe вместе с игрой (dist/NeonSnake.exe).

Команды:
    NeonSnakeSetup.exe               установить и подождать Enter
    NeonSnakeSetup.exe --install     установить / восстановить
    NeonSnakeSetup.exe --verify      проверить целостность
    NeonSnakeSetup.exe --remove      удалить игру (сохранения остаются)
"""

import ctypes
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time

APP_NAME = "NeonSnake"
VERSION = "1.2.1"
GAME_NAME = "NeonSnake.exe"
SETUP_NAME = "NeonSnakeSetup.exe"

HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
DETACHED_PROCESS = 0x00000008


# ---------------------------------------------------------------- пути
def _paths():
    home = os.environ.get("NEON_SNAKE_HOME")
    if not home:
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        home = os.path.join(local, APP_NAME)
    home = os.path.abspath(home)

    data = os.environ.get("NEON_SNAKE_DATA")
    if not data:
        roam = os.environ.get("APPDATA") or os.path.expanduser("~")
        data = os.path.join(roam, APP_NAME)
    return home, os.path.abspath(data)


HOME, DATA_DIR = _paths()
BIN_DIR = os.path.join(HOME, "bin")
GAME_EXE = os.path.join(HOME, GAME_NAME)
SETUP_EXE = os.path.join(HOME, SETUP_NAME)
MANIFEST = os.path.join(HOME, "manifest.json")
SAVE_NAME = "neon_snake_save.json"
LEGACY_NAME = "neon_snake_best.json"


def say(text=""):
    print(text, flush=True)


def header(title):
    say("=" * 52)
    say("  NEON SNAKE  ·  " + title)
    say("=" * 52)


# ---------------------------------------------------------------- файлы
def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _clear_readonly(path):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def install_file(src, dst):
    """Копирует файл, заменяя старый, и ставит атрибут "только чтение"."""
    tmp = dst + ".new"
    try:
        os.remove(tmp)
    except OSError:
        pass
    shutil.copyfile(src, tmp)
    if os.path.exists(dst):
        _clear_readonly(dst)
        try:
            os.remove(dst)
        except OSError:
            pass
    os.replace(tmp, dst)
    try:
        os.chmod(dst, stat.S_IREAD)
    except OSError:
        pass


def _same_file(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def find_embedded_game():
    """Возвращает путь к упакованной игре или None."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        packed = os.path.join(base, "payload", GAME_NAME)
        if os.path.isfile(packed):
            return packed
    env = os.environ.get("NEON_SNAKE_GAME_EXE")
    if env and os.path.isfile(env):
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.abspath(os.path.join(here, os.pardir, "dist", GAME_NAME))
    if os.path.isfile(local):
        return local
    return None


# ---------------------------------------------------------------- PATH
def _read_user_path():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            value, kind = winreg.QueryValueEx(key, "Path")
        except OSError:
            return "", winreg.REG_EXPAND_SZ
    return value, kind


def _write_user_path(value, kind):
    import winreg
    if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
        kind = winreg.REG_EXPAND_SZ
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, kind, value)


def _norm_path(value):
    return os.path.normcase(os.path.normpath(value.strip().strip('"')))


def _broadcast_change():
    try:
        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            ctypes.c_wchar_p("Environment"),
            SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))
    except Exception:
        pass


def path_add():
    """Ставит папку bin в начало пользовательского PATH (без дублей)."""
    if os.environ.get("NEON_SNAKE_NO_PATH") == "1":
        say("  PATH не изменялся (NEON_SNAKE_NO_PATH=1).")
        return
    try:
        value, kind = _read_user_path()
        parts = [p for p in value.split(";") if p.strip()]
        target = _norm_path(BIN_DIR)
        parts = [p for p in parts if _norm_path(p) != target]
        new_value = ";".join([BIN_DIR] + parts)
        if new_value == value:
            say("  PATH: уже настроен.")
            return
        _write_user_path(new_value, kind)
        _broadcast_change()
        say("  PATH: добавлено " + BIN_DIR)
    except Exception as exc:  # noqa: BLE001 - установка не должна падать
        say("  ВНИМАНИЕ: не удалось изменить PATH: %s" % exc)
        say("  Запускайте игру по полному пути: " + GAME_EXE)


def path_remove():
    try:
        value, kind = _read_user_path()
        parts = [p for p in value.split(";") if p.strip()]
        target = _norm_path(BIN_DIR)
        kept = [p for p in parts if _norm_path(p) != target]
        if len(kept) != len(parts):
            _write_user_path(";".join(kept), kind)
            _broadcast_change()
            say("  PATH: удалено " + BIN_DIR)
        else:
            say("  PATH: записи не было.")
    except Exception as exc:  # noqa: BLE001
        say("  ВНИМАНИЕ: не удалось изменить PATH: %s" % exc)


# ---------------------------------------------------------------- ярлыки
SNAKE_CMD = """@echo off
rem NEON SNAKE launcher. Created by %(setup)s.
setlocal EnableExtensions
set "GAME=%%~dp0..\\%(game)s"
if not exist "%%GAME%%" (
    echo [snake] Game files not found.
    echo [snake] Run: install snake
    exit /b 1
)
start "" "%%GAME%%" %%*
exit /b 0
""" % {"setup": SETUP_NAME, "game": GAME_NAME}

INSTALL_CMD = """@echo off
setlocal EnableExtensions
rem "install snake" - repair / verify / remove NEON SNAKE.
set "SETUP=%%~dp0..\\%(setup)s"
if /i "%%~1"=="snake" goto snake
echo.
echo   NEON SNAKE maintenance
echo     install snake            reinstall / repair
echo     install snake --remove   uninstall
echo.
exit /b 1
:snake
if not exist "%%SETUP%%" (
    echo [install] Installer not found:
    echo   %%SETUP%%
    echo Download %(setup)s and run it once, then try again.
    exit /b 1
)
if /i "%%~2"=="--remove" goto remove
if /i "%%~2"=="remove" goto remove
"%%SETUP%%" --install
exit /b %%errorlevel%%
:remove
"%%SETUP%%" --remove
exit /b %%errorlevel%%
""" % {"setup": SETUP_NAME}


def write_text(path, text):
    with open(path, "w", encoding="ascii", newline="\r\n") as fh:
        fh.write(text)


# ---------------------------------------------------------------- сохранения
def import_saves():
    """Переносит сохранения из папки запуска, если у игры их ещё нет."""
    target = os.path.join(DATA_DIR, SAVE_NAME)
    if os.path.exists(target):
        return
    candidates = [os.getcwd()]
    try:
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
    except Exception:
        pass
    seen = set()
    for folder in candidates:
        folder = os.path.abspath(folder)
        if folder in seen:
            continue
        seen.add(folder)
        source = os.path.join(folder, SAVE_NAME)
        if not os.path.isfile(source):
            continue
        shutil.copyfile(source, target)
        legacy_src = os.path.join(folder, LEGACY_NAME)
        legacy_dst = os.path.join(DATA_DIR, LEGACY_NAME)
        if os.path.isfile(legacy_src) and not os.path.exists(legacy_dst):
            shutil.copyfile(legacy_src, legacy_dst)
        say("  Сохранения перенесены: " + source)
        return


# ---------------------------------------------------------------- проверка
def read_manifest():
    try:
        with open(MANIFEST, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def collect_problems():
    problems = []
    if not os.path.isfile(GAME_EXE):
        problems.append("нет файла игры: " + GAME_EXE)
    if not os.path.isfile(SETUP_EXE):
        problems.append("нет установщика: " + SETUP_EXE)
    if not os.path.isfile(os.path.join(BIN_DIR, "snake.cmd")):
        problems.append("нет команды snake.cmd")
    if not os.path.isfile(os.path.join(BIN_DIR, "install.cmd")):
        problems.append("нет команды install.cmd")
    manifest = read_manifest()
    if not manifest:
        problems.append("нет manifest.json")
        return problems
    for key, path in (("game", GAME_EXE), ("setup", SETUP_EXE)):
        item = manifest.get(key) or {}
        if not os.path.isfile(path):
            continue
        try:
            if item.get("size") != os.path.getsize(path):
                problems.append("размер не совпадает: " + os.path.basename(path))
            elif item.get("sha256") != sha256_file(path):
                problems.append("файл изменён: " + os.path.basename(path))
        except OSError as exc:
            problems.append("не читается %s: %s" % (os.path.basename(path), exc))
    return problems


def write_manifest():
    data = {
        "app": APP_NAME,
        "version": VERSION,
        "installed": time.strftime("%Y-%m-%d %H:%M:%S"),
        "game": {"file": GAME_NAME, "size": os.path.getsize(GAME_EXE),
                 "sha256": sha256_file(GAME_EXE)},
        "setup": {"file": SETUP_NAME, "size": os.path.getsize(SETUP_EXE),
                  "sha256": sha256_file(SETUP_EXE)},
    }
    tmp = MANIFEST + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=True, indent=1)
    os.replace(tmp, MANIFEST)


# ---------------------------------------------------------------- действия
def do_install():
    header("установка")
    say("  Папка игры : " + HOME)
    say("  Сохранения : " + DATA_DIR)
    say()

    source = find_embedded_game()
    if not source:
        say("ОШИБКА: в установщике нет игры (%s)." % GAME_NAME)
        say("Скачайте NeonSnakeSetup.exe заново.")
        return 1

    os.makedirs(HOME, exist_ok=True)
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        install_file(source, GAME_EXE)
        say("  Игра установлена.")
    except OSError as exc:
        say("ОШИБКА: не удалось записать игру: %s" % exc)
        say("Закройте запущенную игру и повторите: install snake")
        return 1

    running = os.path.abspath(sys.executable)
    if getattr(sys, "frozen", False) and not _same_file(running, SETUP_EXE):
        try:
            install_file(running, SETUP_EXE)
            say("  Установщик сохранён для команды install snake.")
        except OSError as exc:
            say("  ВНИМАНИЕ: не удалось сохранить установщик: %s" % exc)
    elif not os.path.isfile(SETUP_EXE):
        say("  ВНИМАНИЕ: установщик не сохранён, команда install snake")
        say("  сможет только сообщить об ошибке.")

    write_text(os.path.join(BIN_DIR, "snake.cmd"), SNAKE_CMD)
    write_text(os.path.join(BIN_DIR, "install.cmd"), INSTALL_CMD)

    try:
        write_manifest()
    except OSError as exc:
        say("ОШИБКА: не удалось записать manifest.json: %s" % exc)
        return 1

    import_saves()
    path_add()

    problems = collect_problems()
    if problems:
        say()
        say("Проверка выявила проблемы:")
        for item in problems:
            say("  - " + item)
        return 1

    say()
    say("ГОТОВО. Игра установлена.")
    say()
    say("  snake                    запустить игру")
    say("  install snake            проверить / восстановить")
    say("  install snake --remove   удалить игру")
    say()
    say("Откройте НОВОЕ окно CMD, чтобы команды появились.")
    say("Если Windows покажет предупреждение SmartScreen,")
    say("нажмите «Подробнее» -> «Выполнить в любом случае».")
    return 0


def do_verify():
    header("проверка")
    manifest = read_manifest()
    if manifest:
        say("  Версия: %s" % manifest.get("version", "?"))
        say("  Установлено: %s" % manifest.get("installed", "?"))
    problems = collect_problems()
    if problems:
        say()
        say("Обнаружены проблемы:")
        for item in problems:
            say("  - " + item)
        say()
        say("Восстановление:  install snake")
        return 1
    say()
    say("  Все файлы на месте, контрольные суммы совпадают.")
    say("  Игра: " + GAME_EXE)
    return 0


def _safe_home_for_delete():
    """Рекурсивно удаляем только папку, которая называется NeonSnake."""
    try:
        path = os.path.abspath(HOME)
        if os.path.dirname(path) == path:        # корень диска
            return False
        return os.path.basename(path).lower() == APP_NAME.lower()
    except Exception:
        return False


def _delete_home_later():
    """Удаляет папку игры после выхода установщика (он сам заблокирован)."""
    if not _safe_home_for_delete():
        say("  Папка игры не удалена: небезопасный путь")
        say("  " + HOME)
        return
    args = ["cmd", "/c", "ping", "-n", "3", "127.0.0.1", ">nul", "&",
            "rmdir", "/s", "/q", HOME, ">nul", "2>nul", "&",
            "ping", "-n", "2", "127.0.0.1", ">nul", "&",
            "rmdir", "/s", "/q", HOME, ">nul", "2>nul"]
    try:
        subprocess.Popen(args, creationflags=DETACHED_PROCESS, close_fds=True,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _running_from_home():
    """Запущен ли установщик из установленной папки (а не из загрузок)."""
    try:
        exe = os.path.abspath(sys.executable)
        root = os.path.abspath(HOME)
        return os.path.commonpath([exe, root]) == root
    except Exception:
        return False


def do_remove():
    header("удаление")
    path_remove()

    if _running_from_home():
        # Не трогаем файлы сейчас: cmd ещё читает install.cmd из этой папки.
        _delete_home_later()
        say("  Папка игры будет удалена после закрытия установщика.")
        say()
        say("  Игра удалена. Сохранения оставлены в:")
        say("  " + DATA_DIR)
        return 0

    for path in (os.path.join(BIN_DIR, "snake.cmd"),
                 os.path.join(BIN_DIR, "install.cmd"),
                 MANIFEST, GAME_EXE, SETUP_EXE):
        try:
            if _same_file(os.path.abspath(sys.executable), path):
                continue
            _clear_readonly(path)
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            say("  Не удалось удалить %s: %s" % (path, exc))

    for folder in (BIN_DIR, HOME):
        try:
            os.rmdir(folder)
        except OSError:
            pass

    if os.path.isdir(HOME):
        if _safe_home_for_delete():
            _delete_home_later()
            say("  Папка игры будет удалена после закрытия установщика.")
        else:
            say("  Остались файлы в папке: " + HOME)

    say()
    say("  Игра удалена. Сохранения оставлены в:")
    say("  " + DATA_DIR)
    return 0


def main(argv):
    args = [a.lower() for a in argv[1:]]
    if "--help" in args or "-h" in args or "/?" in args:
        say(__doc__.strip())
        return 0

    pause = not args or "--pause" in args
    try:
        if "--remove" in args or "remove" in args:
            code = do_remove()
        elif "--verify" in args or "verify" in args:
            code = do_verify()
        else:
            code = do_install()
    except Exception:
        import traceback
        say()
        say("НЕОЖИДАННАЯ ОШИБКА:")
        say(traceback.format_exc())
        code = 1

    if pause:
        say()
        try:
            input("Нажмите Enter, чтобы закрыть окно...")
        except Exception:
            pass
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
