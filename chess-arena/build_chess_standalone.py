"""Build docs/chess/standalone.html - one offline HTML file with the game.

Run from the repository root:
    python chess-arena/build_chess_standalone.py
"""

from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CHESS = REPO / "docs" / "chess"


def read(name: str) -> str:
    return (CHESS / name).read_text(encoding="utf-8")


def inline_script(source: str) -> str:
    if "</script" in source.lower():
        raise RuntimeError("JavaScript contains </script> and cannot be inlined as-is")
    return source


def main() -> None:
    html = read("index.html")
    css = read("css/chess.css")
    engine = inline_script(read("js/engine.js"))
    puzzles = inline_script(read("js/puzzles.js"))
    generator = inline_script(read("js/puzzle-generator.js"))
    app = inline_script(read("js/app.js"))

    worker_body = read("js/ai-worker.js").replace(
        "importScripts('engine.js');",
        "/* engine.js is already inlined above */",
    )
    worker = inline_script(engine + "\n" + worker_body)

    html = html.replace(
        '<link rel="manifest" href="manifest.webmanifest">\n', ""
    )
    html = html.replace(
        '<link rel="icon" href="icons/favicon.png" sizes="32x32" type="image/png">\n', ""
    )
    html = html.replace(
        '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">\n', ""
    )
    html = html.replace(
        '<link rel="stylesheet" href="css/chess.css">',
        "<style>\n" + css + "\n</style>",
    )
    html = html.replace(
        '<a class="brand" href="./" title="CHESS ARENA">',
        '<a class="brand" href="#" title="CHESS ARENA">',
    )
    html = html.replace(
        '<script src="js/stockfish-client.js"></script>\n', ""
    )

    html = html.replace(
        '<script src="js/engine.js"></script>',
        "<script>\n" + engine + "\n</script>",
    )
    html = html.replace(
        '<script src="js/puzzles.js"></script>',
        "<script>\n" + puzzles + "\n</script>",
    )
    html = html.replace(
        '<script src="js/puzzle-generator.js"></script>',
        "<script>\n" + generator + "\n</script>",
    )

    worker_block = (
        '<script type="text/plain" id="chess-worker-source">\n'
        + worker
        + "\n</script>\n"
        + "<script>\n"
        + "(function () {\n"
        + "  try {\n"
        + "    var source = document.getElementById('chess-worker-source').textContent;\n"
        + "    window.CHESS_WORKER_URL = URL.createObjectURL(\n"
        + "      new Blob([source], { type: 'text/javascript' })\n"
        + "    );\n"
        + "  } catch (error) {\n"
        + "    window.CHESS_WORKER_URL = null;\n"
        + "  }\n"
        + "})();\n"
        + "</script>\n"
        + "<script>\n"
        + "window.CHESS_STOCKFISH_URL = null;\n"
        + app
        + "\n</script>"
    )
    html = html.replace('<script src="js/app.js"></script>', worker_block)

    if "src=\"js/" in html or 'href="css/' in html:
        raise RuntimeError("Standalone build still references external assets")

    out = CHESS / "standalone.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    size_kb = out.stat().st_size / 1024
    print(f"Wrote {out} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
