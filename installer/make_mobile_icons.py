# -*- coding: utf-8 -*-
"""PNG-иконки для мобильной PWA из того же макета, что и assets/neon_snake.ico.

Запуск: python installer/make_mobile_icons.py
Зависимостей нет: PNG собирается вручную через zlib/struct.
"""

import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "icons")
sys.path.insert(0, HERE)
import make_icon  # noqa: E402


def _chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload +
            struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def _png(width, height, rows):
    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(raw, 9)) +
            _chunk(b"IEND", b""))


def _rgba(size):
    """Возвращает строки RGBA сверху вниз из BGRA-рендера make_icon."""
    data = make_icon.render(size)
    stride = size * 4
    rows = []
    for y in range(size - 1, -1, -1):
        src = data[y * stride:(y + 1) * stride]
        row = bytearray(stride)
        for x in range(size):
            b, g, r, a = src[x * 4:x * 4 + 4]
            row[x * 4:x * 4 + 4] = bytes((r, g, b, a))
        rows.append(bytes(row))
    return rows


def _write(name, width, height, rows):
    path = os.path.join(OUT, name)
    with open(path, "wb") as fh:
        fh.write(_png(width, height, rows))
    print("%-24s %dx%d  %d bytes" % (name, width, height, os.path.getsize(path)))


def _maskable(size=512, inset_ratio=0.10):
    """Иконка с полями: содержимое в безопасной зоне 80%."""
    bg = bytes((4, 7, 15, 255))
    canvas = [bytearray(bg * size) for _ in range(size)]
    inner = size - 2 * int(size * inset_ratio)
    small = _rgba(inner)
    off = (size - inner) // 2
    for y in range(inner):
        row = canvas[off + y]
        row[off * 4:(off + inner) * 4] = small[y]
    return [bytes(r) for r in canvas]


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = {
        "favicon.png": 32,
        "icon-192.png": 192,
        "icon-512.png": 512,
        "apple-touch-icon.png": 180,
    }
    for name, size in sizes.items():
        _write(name, size, size, _rgba(size))
    _write("icon-maskable-512.png", 512, 512, _maskable(512))


if __name__ == "__main__":
    main()
