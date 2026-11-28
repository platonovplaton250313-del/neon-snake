# NEON PROJECTS

Коллекция небольших игр и открыток. Каждый проект лежит в своей папке,
запускается независимо и имеет собственный README с подробностями.

## Проекты

| Проект | Что это | Папка | Быстрый запуск | Онлайн |
| --- | --- | --- | --- | --- |
| **NEON SNAKE** | Неоновая змейка: шесть режимов, магазин, скины, боты и сетевая игра. Windows-версия и мобильная PWA. | `neon-snake/`, `docs/` | `neon-snake\snake.cmd` или `snake` после установки | [PWA](https://platonovplaton250313-del.github.io/neon-snake/) |
| **NEON BRAWL** | Динамичная арена 3×3: шесть бойцов, две команды и неоновые сражения на Python/tkinter. | `neon-brawl/` | `neon-brawl\brawl.cmd` | — |
| **CHESS ARENA** | Шахматы в духе Chess.com: Stockfish 16, шесть уровней, часы, разбор партий, PGN/FEN и задачи. Windows-лаунчер и PWA. | `chess-arena/`, `docs/chess/` | `chess-arena\chess.cmd` или `chess` после установки | [PWA](https://platonovplaton250313-del.github.io/neon-snake/chess/) |
| **С Днём Матери!** | Анимированная открытка на pygame с объёмным сердцем, акварельным фоном и салютом. | `mothers-day/` | `mothers-day\mothers_day.cmd` | — |

Подробная документация: [NEON SNAKE](neon-snake/README.md) ·
[NEON BRAWL](neon-brawl/README.md) · [CHESS ARENA](chess-arena/README.md) ·
[Открытка](mothers-day/README.md).

## Структура репозитория

```text
.
├── neon-snake/      исходники и лаунчеры Windows-версии NEON SNAKE
│   └── installer/   сборка .exe и установщика
├── neon-brawl/      NEON BRAWL целиком
├── chess-arena/     лаунчеры, установщик и сборка CHESS ARENA
├── mothers-day/     открытка, шрифты и готовая картинка
├── docs/            GitHub Pages: PWA NEON SNAKE
│   └── chess/       PWA CHESS ARENA
├── README.md        эта страница
└── .gitignore
```

`docs/` публикуется через GitHub Pages без сборки. Поэтому веб-версии
остаются на своих адресах, а Windows-файлы и исходники лежат по проектам.

## Что нужно для запуска

- **PWA** — любой современный браузер, установка не требуется.
- **Windows-версии** — Windows 10/11. Для запуска из исходников нужен
  Python 3.8+ (`tkinter` входит в стандартную поставку); готовые `.exe`
  для NEON SNAKE Python не требуют.
- **Открытка** — Python 3.9+ и `pygame-ce`; лаунчер предложит установить
  зависимость автоматически.

## GitHub Pages

- NEON SNAKE: <https://platonovplaton250313-del.github.io/neon-snake/>
- CHESS ARENA: <https://platonovplaton250313-del.github.io/neon-snake/chess/>

После изменений в `docs/` обновите версию кэша в `docs/sw.js`
(`const CACHE = 'neon-snake-vN'`).

## Релизы

Готовые сборки и установщики:
<https://github.com/platonovplaton250313-del/neon-snake/releases>.
