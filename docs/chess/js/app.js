/* CHESS ARENA — интерфейс, часы, история и связь с движком. */
(function () {
  'use strict';

  const E = window.ChessEngine;
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const FILES = 'abcdefgh';

  const START_COUNTS = { 1: 8, 2: 2, 3: 2, 4: 2, 5: 1, 6: 1 };
  const CAPTURE_ORDER = [5, 4, 3, 2, 1];
  const PAWN_POINTS = { 1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0 };
  const PIECE_KEY = { 1: 'pawn', 2: 'knight', 3: 'bishop', 4: 'rook', 5: 'queen', 6: 'king' };

  const LEVELS = [
    {
      name: 'Пешка', meta: 'Новичок · ≈800', rating: 800, piece: 'pawn',
      engine: 'native', depth: 2, time: 300, randomChance: 0.22, randomness: 90
    },
    {
      name: 'Конь', meta: 'Любитель · ≈1200', rating: 1200, piece: 'knight',
      engine: 'stockfish', elo: 1320, depth: 10, time: 320
    },
    {
      name: 'Слон', meta: 'Клубный игрок · 1600', rating: 1600, piece: 'bishop',
      engine: 'stockfish', elo: 1600, depth: 12, time: 650
    },
    {
      name: 'Ферзь', meta: 'Эксперт · 2000', rating: 2000, piece: 'queen',
      engine: 'stockfish', elo: 2000, depth: 14, time: 950
    },
    {
      name: 'Король', meta: 'Мастер · 2400', rating: 2400, piece: 'king',
      engine: 'stockfish', elo: 2400, depth: 16, time: 1300
    },
    {
      name: 'Своя', meta: 'Диапазон силы', rating: 1600, piece: 'star',
      engine: 'stockfish', custom: true, depth: 12, time: 700
    }
  ];

  const TIME_PRESETS = {
    '10+0': { initial: 600000, inc: 0, label: '10 + 0' },
    '5+3': { initial: 300000, inc: 3000, label: '5 + 3' },
    '3+2': { initial: 180000, inc: 2000, label: '3 + 2' },
    '1+0': { initial: 60000, inc: 0, label: '1 + 0' },
    'none': { initial: 0, inc: 0, label: 'Без часов' }
  };

  const PUZZLE_LEVELS = [1, 2, 3, 4];
  const STORAGE_KEY = 'chess-arena-settings-v1';
  const ARCHIVE_KEY = 'chess-arena-archive-v1';
  const DEFAULT_SETTINGS = {
    mode: 'bot',
    level: 2,
    time: '10+0',
    color: 'w',
    sound: true,
    volume: 70,
    boardTheme: 'green',
    pieceStyle: 'classic',
    coordinates: true,
    showLegal: true,
    showLast: true,
    animations: true,
    animationMs: 180,
    pieceScale: 96,
    autoPromote: false,
    confirmResign: true,
    showEvalBar: true,
    showBestMove: true,
    analysisDepth: 12,
    analysisTime: 350,
    botEloMin: 800,
    botEloMax: 2400
  };

  const state = {
    game: null,
    started: false,
    over: false,
    result: null,
    mode: 'bot',
    level: 2,
    botElo: 1600,
    humanColor: 1,
    botColor: -1,
    orientation: 1,
    colorChoice: 'w',
    timeKey: '10+0',
    clocks: {
      enabled: true,
      initial: 600000,
      inc: 0,
      white: 600000,
      black: 600000,
      running: false,
      last: 0,
      timer: null
    },
    selected: null,
    legalForSelected: [],
    pointer: null,
    dragGhost: null,
    snaps: [],
    lastMove: null,
    viewPly: null,
    reviewGame: null,
    promotion: null,
    botThinking: false,
    botId: 0,
    botTimer: null,
    worker: null,
    stockfish: null,
    stockfishState: 'idle',
    engineName: 'встроенный движок',
    pendingBot: null,
    botWasThinking: false,
    pausedForSetup: false,
    resignArmed: false,
    resignTimer: null,
    resultTimer: null,
    toastTimer: null,
    audio: null,
    analysis: null,
    analysisToken: 0,
    puzzle: null,
    puzzleFilter: 'all',
    puzzleTimer: null,
    solvedPuzzles: [],
    puzzleStats: {
      1: { solved: 0, streak: 0, best: 0 },
      2: { solved: 0, streak: 0, best: 0 },
      3: { solved: 0, streak: 0, best: 0 },
      4: { solved: 0, streak: 0, best: 0 }
    },
    settings: Object.assign({}, DEFAULT_SETTINGS),
    form: {
      mode: 'bot', level: 2, time: '10+0', color: 'w'
    }
  };

  const els = {};

  function init() {
    cacheElements();
    loadSettings();
    loadSolvedPuzzles();
    loadPuzzleStats();
    state.form = {
      mode: state.settings.mode,
      level: state.settings.level,
      time: TIME_PRESETS[state.settings.time] ? state.settings.time : '10+0',
      color: state.settings.color
    };
    if (state.form.color !== 'w' && state.form.color !== 'b' && state.form.color !== 'random') {
      state.form.color = 'w';
    }
    buildLevels();
    bindEvents();
    applySettings(true);
    setupStockfish();

    const preset = TIME_PRESETS[state.form.time] || TIME_PRESETS['10+0'];
    state.clocks.enabled = preset.initial > 0;
    state.clocks.initial = preset.initial;
    state.clocks.inc = preset.inc;
    state.clocks.white = preset.initial;
    state.clocks.black = preset.initial;
    state.timeKey = state.form.time;
    state.settings.sound = state.settings.sound !== false;

    state.game = new E.Game();
    state.snaps = [{ fen: state.game.fen(), move: null, san: null, color: 0 }];
    updateSoundUI();
    refreshPreview(false);
    renderAll();
    showSetup(true);
    registerServiceWorker();
  }

  function cacheElements() {
    els.board = $('#board');
    els.squares = $('#squares');
    els.pieces = $('#pieces');
    els.markers = $('#markers');
    els.promo = $('#promo');
    els.promoPieces = $('#promo-pieces');
    els.barTop = $('#bar-top');
    els.barBottom = $('#bar-bottom');
    els.statusLine = $('#status-line');
    els.statusText = $('#status-text');
    els.moves = $('#moves');
    els.movesEmpty = $('#moves-empty');
    els.reviewBar = $('#review-bar');
    els.gameTags = $('#game-tags');
    els.soundBtn = $('#sound-btn');
    els.setupOverlay = $('#setup-overlay');
    els.setupCancel = $('#setup-cancel');
    els.startBtn = $('#start-btn');
    els.modeSegment = $('#mode-segment');
    els.botSection = $('#bot-section');
    els.colorSection = $('#color-section');
    els.levels = $('#levels');
    els.timeChips = $('#time-chips');
    els.colorChips = $('#color-chips');
    els.resultOverlay = $('#result-overlay');
    els.resultCard = $('.result-card');
    els.resultTitle = $('#result-title');
    els.resultSub = $('#result-sub');
    els.resultScore = $('#result-score');
    els.resultEyebrow = $('#result-eyebrow');
    els.toast = $('#toast');
    els.undoBtn = $('#undo-btn');
    els.flipBtn = $('#flip-btn');
    els.resignBtn = $('#resign-btn');
    els.controls = $('.controls');
    els.panelActions = $('.panel-actions');
    els.analyzeBtn = $('#analyze-btn');
    els.analyzeResultBtn = $('#analyze-result-btn');
    els.analysisPanel = $('#analysis-panel');
    els.analysisProgress = $('#analysis-progress');
    els.analysisSummary = $('#analysis-summary');
    els.analysisCurrent = $('#analysis-current');
    els.evalChart = $('#eval-chart');
    els.evalBar = $('#eval-bar');
    els.evalFill = $('#eval-fill');
    els.evalLabel = $('#eval-label');
    els.arrows = $('#arrows');
    els.enginePill = $('#engine-pill');
    els.settingsBtn = $('#settings-btn');
    els.settingsNav = $('#settings-nav');
    els.settingsOverlay = $('#settings-overlay');
    els.settingsClose = $('#settings-close');
    els.settingsDone = $('#settings-done');
    els.settingsReset = $('#settings-reset');
    els.archiveOverlay = $('#archive-overlay');
    els.archiveClose = $('#archive-close');
    els.archiveList = $('#archive-list');
    els.archiveNav = $('#archive-nav');
    els.archiveBtn = $('#archive-btn');
    els.pgnBtn = $('#pgn-btn');
    els.pgnOverlay = $('#pgn-overlay');
    els.pgnClose = $('#pgn-close');
    els.pgnText = $('#pgn-text');
    els.pgnCopy = $('#pgn-copy');
    els.pgnDownload = $('#pgn-download');
    els.pgnLoad = $('#pgn-load');
    els.pgnFen = $('#pgn-fen');
    els.pgnFenCopy = $('#pgn-fen-copy');
    els.pgnFenLoad = $('#pgn-fen-load');
    els.puzzleNav = $('#puzzle-nav');
    els.puzzleBtn = $('#puzzle-btn');
    els.puzzleOverlay = $('#puzzle-overlay');
    els.puzzleClose = $('#puzzle-close');
    els.endlessLevels = $('#endless-levels');
    els.randomPuzzle = $('#random-puzzle');
    els.endlessCounts = [null, $('#endless-count-1'), $('#endless-count-2'), $('#endless-count-3'), $('#endless-count-4')];
    els.puzzleFilters = $('#puzzle-filters');
    els.puzzleGrid = $('#puzzle-grid');
    els.puzzleCount = $('#puzzle-count');
    els.puzzlePanel = $('#puzzle-panel');
    els.puzzleTheme = $('#puzzle-theme');
    els.puzzleDifficulty = $('#puzzle-difficulty');
    els.puzzleProgress = $('#puzzle-progress');
    els.puzzleInstruction = $('#puzzle-instruction');
    els.puzzleFeedback = $('#puzzle-feedback');
    els.puzzleHint = $('#puzzle-hint');
    els.puzzleRetry = $('#puzzle-retry');
    els.puzzleSolution = $('#puzzle-solution');
    els.puzzleListBtn = $('#puzzle-list-btn');
    els.puzzleSuccess = $('#puzzle-success');
    els.puzzleSuccessSub = $('#puzzle-success-sub');
    els.puzzleSuccessScore = $('#puzzle-success-score');
    els.puzzleNext = $('#puzzle-next');
    els.puzzleAll = $('#puzzle-all');
    els.puzzleSuccessClose = $('#puzzle-success-close');
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object') return;

      if (data.mode === 'bot' || data.mode === 'local') state.settings.mode = data.mode;
      if (Number.isInteger(data.level) && data.level >= 0 && data.level < LEVELS.length) {
        state.settings.level = data.level;
      }
      if (typeof data.time === 'string' && TIME_PRESETS[data.time]) state.settings.time = data.time;
      if (data.color === 'w' || data.color === 'b' || data.color === 'random') {
        state.settings.color = data.color;
      }

      state.settings.sound = data.sound !== false;
      state.settings.volume = clampNumber(data.volume, 0, 100, DEFAULT_SETTINGS.volume);
      state.settings.boardTheme = ['green', 'brown', 'blue', 'gray', 'dark'].includes(data.boardTheme)
        ? data.boardTheme : DEFAULT_SETTINGS.boardTheme;
      state.settings.pieceStyle = ['classic', 'flat', 'neo'].includes(data.pieceStyle)
        ? data.pieceStyle : DEFAULT_SETTINGS.pieceStyle;
      state.settings.coordinates = data.coordinates !== false;
      state.settings.showLegal = data.showLegal !== false;
      state.settings.showLast = data.showLast !== false;
      state.settings.animations = data.animations !== false;
      state.settings.animationMs = clampNumber(data.animationMs, 0, 500, DEFAULT_SETTINGS.animationMs);
      state.settings.pieceScale = clampNumber(data.pieceScale, 70, 100, DEFAULT_SETTINGS.pieceScale);
      state.settings.autoPromote = data.autoPromote === true;
      state.settings.confirmResign = data.confirmResign !== false;
      state.settings.showEvalBar = data.showEvalBar !== false;
      state.settings.showBestMove = data.showBestMove !== false;
      state.settings.analysisDepth = clampNumber(data.analysisDepth, 6, 20, DEFAULT_SETTINGS.analysisDepth);
      state.settings.analysisTime = clampNumber(data.analysisTime, 120, 2000, DEFAULT_SETTINGS.analysisTime);
      state.settings.botEloMin = clampNumber(data.botEloMin, 600, 2800, DEFAULT_SETTINGS.botEloMin);
      state.settings.botEloMax = clampNumber(data.botEloMax, 600, 2800, DEFAULT_SETTINGS.botEloMax);
      if (state.settings.botEloMin > state.settings.botEloMax) {
        const temp = state.settings.botEloMin;
        state.settings.botEloMin = state.settings.botEloMax;
        state.settings.botEloMax = temp;
      }
    } catch (err) { /* настройки не критичны */ }
  }

  function clampNumber(value, min, max, fallback) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.max(min, Math.min(max, Math.round(number)));
  }

  function saveSettings() {
    state.settings.mode = state.form.mode;
    state.settings.level = state.form.level;
    state.settings.time = state.form.time;
    state.settings.color = state.form.color;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.settings));
    } catch (err) { /* приватный режим */ }
  }

  function applySettings(initial) {
    const s = state.settings;
    document.body.dataset.board = s.boardTheme;
    document.body.dataset.pieces = s.pieceStyle;
    document.body.classList.toggle('no-coords', !s.coordinates);
    document.documentElement.style.setProperty('--anim-ms', s.animationMs + 'ms');
    document.documentElement.style.setProperty('--piece-scale', (s.pieceScale / 100).toFixed(3));
    updateSoundUI();
    syncSettingsForm();
    if (!initial) {
      renderBoard();
      renderPlayers();
    }
    updateEvalBar();
    renderArrows();
  }

  function syncSettingsForm() {
    if (!els.settingsOverlay) return;
    const s = state.settings;
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = String(value);
    };
    set('set-board-theme', s.boardTheme);
    set('set-piece-style', s.pieceStyle);
    set('set-volume', s.volume);
    set('set-animation', s.animationMs);
    set('set-piece-scale', s.pieceScale);
    set('set-analysis-depth', s.analysisDepth);
    set('set-analysis-time', s.analysisTime);
    set('set-bot-min', s.botEloMin);
    set('set-bot-max', s.botEloMax);
    const checks = {
      'set-coordinates': s.coordinates,
      'set-show-legal': s.showLegal,
      'set-show-last': s.showLast,
      'set-animations': s.animations,
      'set-auto-promote': s.autoPromote,
      'set-confirm-resign': s.confirmResign,
      'set-eval-bar': s.showEvalBar,
      'set-best-move': s.showBestMove,
      'set-sound': s.sound
    };
    Object.keys(checks).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.checked = !!checks[id];
    });
    updateSettingOutputs();
  }

  function updateSettingOutputs() {
    const bind = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    const s = state.settings;
    bind('out-volume', s.volume + '%');
    bind('out-animation', s.animationMs ? s.animationMs + ' мс' : 'выкл.');
    bind('out-piece-scale', s.pieceScale + '%');
    bind('out-analysis-depth', 'до ' + s.analysisDepth);
    bind('out-analysis-time', s.analysisTime + ' мс');
    bind('out-bot-range', s.botEloMin + '–' + s.botEloMax);
  }

  function loadSolvedPuzzles() {
    try {
      const raw = localStorage.getItem('chess-arena-puzzles-v1');
      const data = raw ? JSON.parse(raw) : [];
      state.solvedPuzzles = Array.isArray(data) ? data.filter((id) => typeof id === 'string') : [];
    } catch (err) {
      state.solvedPuzzles = [];
    }
  }

  function saveSolvedPuzzles() {
    try {
      localStorage.setItem('chess-arena-puzzles-v1', JSON.stringify(state.solvedPuzzles));
    } catch (err) { /* приватный режим */ }
  }

  function loadPuzzleStats() {
    try {
      const raw = localStorage.getItem('chess-arena-endless-v1');
      const data = raw ? JSON.parse(raw) : null;
      if (!data || typeof data !== 'object') return;
      PUZZLE_LEVELS.forEach((level) => {
        const row = data[level];
        if (!row || typeof row !== 'object') return;
        state.puzzleStats[level] = {
          solved: Math.max(0, Number(row.solved) || 0),
          streak: Math.max(0, Number(row.streak) || 0),
          best: Math.max(0, Number(row.best) || 0)
        };
      });
    } catch (err) { /* статистика не критична */ }
  }

  function savePuzzleStats() {
    try {
      localStorage.setItem('chess-arena-endless-v1', JSON.stringify(state.puzzleStats));
    } catch (err) { /* приватный режим */ }
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    if (location.protocol !== 'http:' && location.protocol !== 'https:') return;
    navigator.serviceWorker.register('../sw.js', { scope: '../' }).catch(() => {});
  }

  /* ---------------------------------------------------------------- движок */
  function setupStockfish() {
    if (!window.StockfishClient) {
      state.stockfishState = 'disabled';
      state.engineName = 'встроенный движок';
      updateEnginePill();
      return;
    }
    const configured = Object.prototype.hasOwnProperty.call(window, 'CHESS_STOCKFISH_URL')
      ? window.CHESS_STOCKFISH_URL : undefined;
    if (configured === null) {
      state.stockfishState = 'disabled';
      state.engineName = 'встроенный движок';
      updateEnginePill();
      return;
    }
    state.stockfish = new window.StockfishClient(configured);
    state.stockfishState = 'loading';
    state.engineName = 'Stockfish 16';
    updateEnginePill();

    // Загружаем заранее, чтобы первый ход бота не ждал компиляции WASM.
    setTimeout(() => {
      const sf = state.stockfish;
      if (!sf) return;
      sf.init().then(() => {
        state.stockfishState = 'ready';
        state.engineName = 'Stockfish 16';
        updateEnginePill();
        if (state.started) renderTags();
      }).catch(() => {
        state.stockfishState = 'failed';
        state.engineName = 'встроенный движок';
        updateEnginePill();
        if (state.started) renderTags();
      });
    }, 120);
  }

  function updateEnginePill() {
    if (!els.enginePill) return;
    const ready = state.stockfishState === 'ready' || state.stockfishState === 'loading';
    els.enginePill.textContent = ready ? 'SF 16' : (state.stockfishState === 'disabled' ? 'ОФЛАЙН' : 'РЕЗЕРВ');
    els.enginePill.title = ready
      ? 'Stockfish 16 · single-threaded WASM'
      : 'Встроенный шахматный движок';
    els.enginePill.dataset.state = state.stockfishState;
  }

  function stockfishUsable() {
    return !!(state.stockfish && state.stockfishState !== 'failed' && state.stockfishState !== 'disabled');
  }

  function stockfishSearch(options) {
    if (!stockfishUsable()) return Promise.reject(new Error('Stockfish недоступен'));
    return state.stockfish.search(options).then((result) => {
      state.stockfishState = 'ready';
      state.engineName = 'Stockfish 16';
      updateEnginePill();
      return result;
    }).catch((error) => {
      if (state.stockfishState !== 'loading') {
        state.stockfishState = 'failed';
        state.engineName = 'встроенный движок';
        updateEnginePill();
      }
      throw error;
    });
  }

  function chooseBotElo(level) {
    if (!level.custom) return level.rating;
    const min = Math.min(state.settings.botEloMin, state.settings.botEloMax);
    const max = Math.max(state.settings.botEloMin, state.settings.botEloMax);
    const step = 50;
    return Math.round((min + Math.random() * (max - min)) / step) * step;
  }

  function resolvedLevel(level) {
    if (!level || !level.custom) return level;
    const elo = state.botElo || chooseBotElo(level);
    const time = Math.round(250 + (elo - 600) * 0.55);
    const depth = Math.max(8, Math.min(17, Math.round(6 + (elo - 600) / 160)));
    return Object.assign({}, level, { rating: elo, elo, time, depth });
  }

  /* ---------------------------------------------------------------- форма */
  function buildLevels() {
    els.levels.innerHTML = LEVELS.map((level, index) => {
      const meta = level.custom
        ? `Диапазон ${state.settings.botEloMin}–${state.settings.botEloMax}`
        : level.meta;
      return `
      <button type="button" class="level-card" data-level="${index}">
        <span class="level-icon">
          <svg viewBox="0 0 45 45"><use href="#pc-${level.piece}"></use></svg>
        </span>
        <span class="level-text">
          <span class="level-name">${level.name}</span>
          <span class="level-meta">${meta}</span>
        </span>
      </button>
    `;
    }).join('');
  }

  function bindEvents() {
    $('#new-game-top').addEventListener('click', openSetup);
    $('#new-game-side').addEventListener('click', openSetup);
    els.startBtn.addEventListener('click', startFromSetup);
    els.setupCancel.addEventListener('click', () => closeSetup(true));

    els.modeSegment.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-mode]');
      if (!btn) return;
      state.form.mode = btn.dataset.mode;
      updateFormUI();
      if (!state.started) refreshPreview();
    });

    els.levels.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-level]');
      if (!btn) return;
      state.form.level = Number(btn.dataset.level);
      if (LEVELS[state.form.level] && LEVELS[state.form.level].custom) state.botElo = 0;
      updateFormUI();
      if (!state.started) refreshPreview();
    });

    els.timeChips.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-time]');
      if (!btn) return;
      state.form.time = btn.dataset.time;
      updateFormUI();
      if (!state.started) {
        const preset = TIME_PRESETS[state.form.time] || TIME_PRESETS['10+0'];
        state.timeKey = state.form.time;
        state.clocks.enabled = preset.initial > 0;
        state.clocks.initial = preset.initial;
        state.clocks.inc = preset.inc;
        state.clocks.white = preset.initial;
        state.clocks.black = preset.initial;
        state.clocks.running = false;
        stopClock();
        updateClocks();
        renderTags();
      }
    });

    els.colorChips.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-color]');
      if (!btn) return;
      state.form.color = btn.dataset.color;
      updateFormUI();
      if (!state.started) refreshPreview();
    });

    els.soundBtn.addEventListener('click', toggleSound);
    if (els.settingsBtn) els.settingsBtn.addEventListener('click', openSettings);
    $$('[data-open-settings]').forEach((btn) => btn.addEventListener('click', openSettings));
    if (els.settingsNav) els.settingsNav.addEventListener('click', openSettings);
    if (els.settingsClose) els.settingsClose.addEventListener('click', closeSettings);
    if (els.settingsDone) els.settingsDone.addEventListener('click', closeSettings);
    if (els.settingsReset) els.settingsReset.addEventListener('click', resetSettings);
    if (els.settingsOverlay) {
      els.settingsOverlay.addEventListener('pointerdown', (event) => {
        if (event.target === els.settingsOverlay) closeSettings();
      });
      els.settingsOverlay.addEventListener('input', onSettingInput);
      els.settingsOverlay.addEventListener('change', onSettingInput);
    }
    if (els.archiveNav) els.archiveNav.addEventListener('click', openArchive);
    if (els.archiveBtn) els.archiveBtn.addEventListener('click', openArchive);
    if (els.archiveClose) els.archiveClose.addEventListener('click', closeArchive);
    if (els.archiveOverlay) {
      els.archiveOverlay.addEventListener('pointerdown', (event) => {
        if (event.target === els.archiveOverlay) closeArchive();
      });
      els.archiveList.addEventListener('click', onArchiveAction);
    }
    if (els.pgnBtn) els.pgnBtn.addEventListener('click', openPgnDialog);
    if (els.pgnClose) els.pgnClose.addEventListener('click', closePgnDialog);
    if (els.pgnOverlay) {
      els.pgnOverlay.addEventListener('pointerdown', (event) => {
        if (event.target === els.pgnOverlay) closePgnDialog();
      });
    }
    if (els.pgnCopy) els.pgnCopy.addEventListener('click', () => copyPgn(false));
    if (els.pgnDownload) els.pgnDownload.addEventListener('click', downloadPgn);
    if (els.pgnLoad) els.pgnLoad.addEventListener('click', loadPgnFromDialog);
    if (els.pgnFenCopy) els.pgnFenCopy.addEventListener('click', copyFen);
    if (els.pgnFenLoad) els.pgnFenLoad.addEventListener('click', loadFenFromDialog);

    els.undoBtn.addEventListener('click', takeback);
    els.flipBtn.addEventListener('click', flipBoard);
    els.resignBtn.addEventListener('click', handleResign);

    els.moves.addEventListener('click', (event) => {
      const btn = event.target.closest('.san[data-ply]');
      if (!btn) return;
      const ply = Number(btn.dataset.ply);
      if (ply === state.snaps.length - 1) exitReview();
      else enterReview(ply);
    });

    els.reviewBar.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-nav]');
      if (!btn) return;
      const action = btn.dataset.nav;
      if (action === 'first') enterReview(0);
      else if (action === 'last') exitReview();
      else if (action === 'prev') stepReview(-1);
      else if (action === 'next') stepReview(1);
    });
    $('#back-to-live').addEventListener('click', exitReview);

    els.promoPieces.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-promo]');
      if (!btn || !state.promotion) return;
      const promo = Number(btn.dataset.promo);
      const move = state.promotion.moves.find((m) => E.movePromo(m) === promo);
      hidePromotion();
      if (move) commitMove(move);
    });
    els.promo.addEventListener('pointerdown', (event) => {
      if (event.target === els.promo) hidePromotion();
    });

    $('#rematch-btn').addEventListener('click', () => {
      hideResult();
      newGame();
    });
    $('#result-new-btn').addEventListener('click', () => {
      hideResult();
      openSetup();
    });
    $('#result-close').addEventListener('click', hideResult);

    els.analyzeBtn.addEventListener('click', startAnalysis);
    els.analyzeResultBtn.addEventListener('click', startAnalysis);
    els.evalChart.addEventListener('click', onEvalChartClick);

    [els.puzzleNav, els.puzzleBtn].forEach((btn) => {
      if (btn) btn.addEventListener('click', () => openPuzzleList());
    });
    els.puzzleClose.addEventListener('click', closePuzzleList);
    els.puzzleOverlay.addEventListener('pointerdown', (event) => {
      if (event.target === els.puzzleOverlay) closePuzzleList();
    });
    els.endlessLevels.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-endless]');
      if (!btn) return;
      startGeneratedPuzzle(Number(btn.dataset.endless));
    });
    els.randomPuzzle.addEventListener('click', () => {
      startGeneratedPuzzle(1 + Math.floor(Math.random() * 4));
    });
    els.puzzleFilters.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-filter]');
      if (!btn) return;
      state.puzzleFilter = btn.dataset.filter;
      renderPuzzleList();
    });
    els.puzzleGrid.addEventListener('click', (event) => {
      const item = event.target.closest('[data-puzzle]');
      if (!item) return;
      const found = window.ChessPuzzles.list.find((p) => p.id === item.dataset.puzzle);
      if (found) startPuzzle(found);
    });
    els.puzzleHint.addEventListener('click', showPuzzleHint);
    els.puzzleRetry.addEventListener('click', retryPuzzle);
    els.puzzleSolution.addEventListener('click', showPuzzleSolution);
    els.puzzleListBtn.addEventListener('click', () => leavePuzzle(true));
    els.puzzleNext.addEventListener('click', nextPuzzle);
    els.puzzleAll.addEventListener('click', () => {
      hidePuzzleSuccess();
      leavePuzzle(true);
    });
    els.puzzleSuccessClose.addEventListener('click', hidePuzzleSuccess);

    els.board.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);

    els.setupOverlay.addEventListener('pointerdown', (event) => {
      if (event.target === els.setupOverlay && state.started) closeSetup(true);
    });

    document.addEventListener('keydown', onKeyDown);
  }

  function updateFormUI() {
    $$('#mode-segment [data-mode]').forEach((btn) => {
      const active = btn.dataset.mode === state.form.mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    $$('#levels [data-level]').forEach((btn) => {
      const active = Number(btn.dataset.level) === state.form.level;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    $$('#time-chips [data-time]').forEach((btn) => {
      const active = btn.dataset.time === state.form.time;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    $$('#color-chips [data-color]').forEach((btn) => {
      const active = btn.dataset.color === state.form.color;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });

    const local = state.form.mode === 'local';
    els.botSection.classList.toggle('hidden', local);
    els.colorSection.classList.toggle('hidden', local);
    els.startBtn.textContent = local ? 'Начать партию' : 'Начать игру';
  }

  function refreshPreview(redrawBoard = true) {
    if (state.started) return;
    state.mode = state.form.mode;
    state.level = state.form.level;
    state.timeKey = state.form.time;
    state.colorChoice = state.form.color;
    const previewLevel = resolvedLevel(LEVELS[state.level]);
    state.botElo = previewLevel.rating;
    if (state.mode === 'bot') {
      state.humanColor = state.form.color === 'b' ? -1 : 1;
      state.botColor = -state.humanColor;
      state.orientation = state.humanColor;
    } else {
      state.humanColor = 1;
      state.botColor = -1;
      state.orientation = 1;
    }
    renderPlayers();
    renderTags();
    updateStatus();
    updateClocks();
    if (redrawBoard) renderBoard();
  }

  function showSetup(initial) {
    if (state.started && !state.over) {
      state.pausedForSetup = state.clocks.running;
      if (state.pausedForSetup) stopClock();
      state.botWasThinking = state.mode === 'bot' && state.game.side === state.botColor;
      cancelBot();
    } else {
      state.pausedForSetup = false;
      state.botWasThinking = false;
    }
    hideResult();
    syncFormFromCurrent();
    updateFormUI();
    els.setupOverlay.classList.remove('hidden');
    els.setupCancel.classList.toggle('hidden', !state.started);
    els.startBtn.focus({ preventScroll: true });
  }

  function syncFormFromCurrent() {
    if (state.started) {
      state.form = {
        mode: state.mode,
        level: state.level,
        time: state.timeKey,
        color: state.colorChoice
      };
    } else {
      state.form = {
        mode: state.mode,
        level: state.level,
        time: state.timeKey,
        color: state.colorChoice
      };
    }
  }

  function closeSetup(resume) {
    els.setupOverlay.classList.add('hidden');
    if (resume && state.started && !state.over) {
      if (state.pausedForSetup) {
        state.pausedForSetup = false;
        state.clocks.running = true;
        state.clocks.last = performance.now();
        startClockTimer();
        updateClocks();
      }
      if (state.botWasThinking && state.mode === 'bot' && state.game.side === state.botColor) {
        state.botWasThinking = false;
        scheduleBot(250);
      }
    }
    state.pausedForSetup = false;
    state.botWasThinking = false;
  }

  function startFromSetup() {
    const preset = TIME_PRESETS[state.form.time] || TIME_PRESETS['10+0'];
    state.mode = state.form.mode;
    state.level = state.form.level;
    state.timeKey = state.form.time;
    state.colorChoice = state.form.color;
    if (state.mode === 'bot') {
      const chosen = LEVELS[state.level] || LEVELS[0];
      state.botElo = chosen.custom ? chooseBotElo(chosen) : chosen.rating;
    }

    let color = state.form.color === 'b' ? -1 : 1;
    if (state.form.color === 'random') color = Math.random() < 0.5 ? 1 : -1;

    if (state.mode === 'bot') {
      state.humanColor = color;
      state.botColor = -color;
      state.orientation = color;
    } else {
      state.humanColor = 1;
      state.botColor = -1;
      state.orientation = 1;
    }

    state.clocks.enabled = preset.initial > 0;
    state.clocks.initial = preset.initial;
    state.clocks.inc = preset.inc;

    saveSettings();
    ensureAudio();
    newGame();
    playSound('start');
  }

  function newGame() {
    cancelBot();
    stopClock();
    clearResultTimer();
    hideResult();
    hidePromotion();
    resetResign();
    resetAnalysis();
    deselect();

    state.game = new E.Game();
    state.started = true;
    state.over = false;
    state.result = null;
    state.snaps = [{ fen: state.game.fen(), move: null, san: null, color: 0 }];
    state.lastMove = null;
    state.viewPly = null;
    state.reviewGame = null;
    state.selected = null;
    state.legalForSelected = [];
    state.pausedForSetup = false;
    state.botWasThinking = false;

    state.clocks.white = state.clocks.initial;
    state.clocks.black = state.clocks.initial;
    state.clocks.running = false;
    state.clocks.last = 0;
    stopClock();

    els.setupOverlay.classList.add('hidden');
    els.promo.classList.add('hidden');

    renderAll();
    if (state.mode === 'bot' && state.game.side === state.botColor) {
      scheduleBot(420);
    } else {
      updateStatus();
    }
  }
  /* __APP_PART2__ */

  /* ---------------------------------------------------------------- отрисовка */
  function renderAll() {
    renderBoard();
    renderPlayers();
    renderMoves();
    renderTags();
    updateStatus();
    updateClocks();
    updateReviewBar();
    renderControls();
    renderAnalysisPanel();
    updatePuzzlePanel();
  }

  function displayGame() {
    return state.viewPly === null ? state.game : state.reviewGame;
  }

  function pieceSvg(piece) {
    const type = E.typeOf(piece);
    return `<svg viewBox="0 0 45 45"><use href="#pc-${PIECE_KEY[type]}"></use></svg>`;
  }

  function visualOf(sq) {
    const file = sq & 7;
    const row = sq >> 4;
    if (state.orientation === 1) return { col: file, row };
    return { col: 7 - file, row: 7 - row };
  }

  function renderBoard() {
    const game = displayGame();
    if (!game) return;
    const checkColor = game.inCheck(game.side) ? game.side : 0;
    const checkSq = checkColor === 1 ? game.kingW : game.kingB;
    const last = state.viewPly === null
      ? state.lastMove
      : (state.snaps[state.viewPly] && state.snaps[state.viewPly].move);
    const selected = state.viewPly === null ? state.selected : null;

    let squaresHtml = '';
    for (let vr = 0; vr < 8; vr++) {
      for (let vc = 0; vc < 8; vc++) {
        const sq = state.orientation === 1 ? vr * 16 + vc : 119 - vr * 16 - vc;
        const file = sq & 7;
        const rank = 7 - (sq >> 4);
        const classes = ['square', ((file + rank) & 1) === 0 ? 'dark' : 'light'];
        if (state.settings.showLast && last && (sq === last.from || sq === last.to)) classes.push('last');
        if (selected === sq) classes.push('selected');
        if (checkColor && sq === checkSq) classes.push('check');

        const coordFile = state.settings.coordinates && vr === 7 ? `<span class="coord file">${FILES[file]}</span>` : '';
        const coordRank = state.settings.coordinates && vc === 0 ? `<span class="coord rank">${rank + 1}</span>` : '';
        squaresHtml += `<div class="${classes.join(' ')}" data-sq="${sq}">${coordFile}${coordRank}</div>`;
      }
    }
    els.squares.innerHTML = squaresHtml;

    let piecesHtml = '';
    for (let row = 0; row < 8; row++) {
      for (let file = 0; file < 8; file++) {
        const sq = row * 16 + file;
        const piece = game.board[sq];
        if (!piece) continue;
        const pos = visualOf(sq);
        piecesHtml += `<div class="piece ${piece > 0 ? 'w' : 'b'}" data-sq="${sq}" style="left:${pos.col * 12.5}%;top:${pos.row * 12.5}%">${pieceSvg(piece)}</div>`;
      }
    }
    els.pieces.innerHTML = piecesHtml;

    renderMarkers();
    renderArrows();
    updateEvalBar();
  }

  function renderMarkers() {
    if (!state.settings.showLegal || state.viewPly !== null || state.selected === null || state.over) {
      els.markers.innerHTML = '';
      return;
    }
    const game = state.game;
    const piece = game.board[state.selected];
    const targets = new Map();
    for (const move of state.legalForSelected) {
      const to = E.moveTo(move);
      if (targets.has(to)) continue;
      const captured = game.board[to] !== 0 ||
        (piece && E.typeOf(piece) === E.PAWN && to === game.ep);
      targets.set(to, captured);
    }
    let html = '';
    targets.forEach((captured, sq) => {
      const pos = visualOf(sq);
      html += `<div class="marker${captured ? ' capture' : ''}" style="left:${pos.col * 12.5}%;top:${pos.row * 12.5}%"></div>`;
    });
    els.markers.innerHTML = html;
  }

  function analysisEvalAt(ply) {
    const analysis = state.analysis;
    if (!analysis || !analysis.evals.length) return null;
    const index = Math.max(0, Math.min(analysis.evals.length - 1, ply));
    return analysis.evals[index] || null;
  }

  function updateEvalBar() {
    if (!els.evalBar) return;
    const analysis = state.analysis;
    const visible = !!analysis && !!analysis.evals.length && state.settings.showEvalBar;
    els.evalBar.classList.toggle('hidden', !visible);
    if (!visible) return;
    const ply = state.viewPly === null ? state.snaps.length - 1 : state.viewPly;
    const entry = analysisEvalAt(ply);
    if (!entry) return;
    const cp = Math.max(-1200, Math.min(1200, entry.cp));
    const whiteShare = 50 + 50 * (2 / (1 + Math.exp(-cp / 260)) - 1);
    els.evalFill.style.height = whiteShare.toFixed(1) + '%';
    els.evalFill.classList.toggle('black-advantage', cp < 0);
    els.evalLabel.textContent = evalText(entry.cp);
    els.evalLabel.classList.toggle('negative', cp < 0);
    els.evalBar.title = evalPhrase(entry.cp);
  }

  function renderArrows() {
    if (!els.arrows) return;
    const analysis = state.analysis;
    if (!state.settings.showBestMove || !analysis || !analysis.done) {
      els.arrows.innerHTML = '';
      return;
    }
    const ply = state.viewPly === null ? state.snaps.length - 1 : state.viewPly;
    const entry = analysisEvalAt(ply);
    if (!entry || !entry.bestUci || entry.bestUci.length < 4) {
      els.arrows.innerHTML = '';
      return;
    }
    const fromName = entry.bestUci.slice(0, 2);
    const toName = entry.bestUci.slice(2, 4);
    if (!/^[a-h][1-8]$/.test(fromName) || !/^[a-h][1-8]$/.test(toName)) {
      els.arrows.innerHTML = '';
      return;
    }
    const from = E.fromAlgebraic(fromName);
    const to = E.fromAlgebraic(toName);
    const a = visualOf(from);
    const b = visualOf(to);
    if (!a || !b) return;
    const x1 = a.col * 12.5 + 6.25;
    const y1 = a.row * 12.5 + 6.25;
    const x2 = b.col * 12.5 + 6.25;
    const y2 = b.row * 12.5 + 6.25;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const length = Math.sqrt(dx * dx + dy * dy) || 1;
    const shorten = 3.6;
    const sx = x1 + (dx / length) * 2.8;
    const sy = y1 + (dy / length) * 2.8;
    const ex = x2 - (dx / length) * shorten;
    const ey = y2 - (dy / length) * shorten;
    els.arrows.innerHTML = `
      <defs>
        <marker id="best-arrow-head" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="#81b64c"></path>
        </marker>
      </defs>
      <line x1="${sx.toFixed(2)}" y1="${sy.toFixed(2)}" x2="${ex.toFixed(2)}" y2="${ey.toFixed(2)}"
        stroke="rgba(129,182,76,0.82)" stroke-width="2.4" stroke-linecap="round"
        marker-end="url(#best-arrow-head)"></line>
    `;
  }

  function updateSquareSelection() {
    $$('#squares .square').forEach((square) => {
      square.classList.toggle('selected', Number(square.dataset.sq) === state.selected);
    });
  }

  function selectSquare(sq) {
    if (!canHumanMove()) return;
    const piece = state.game.board[sq];
    if (!piece || E.colorOf(piece) !== state.game.side) {
      deselect();
      return;
    }
    state.selected = sq;
    state.legalForSelected = state.game.legalMoves().filter((m) => E.moveFrom(m) === sq);
    updateSquareSelection();
    renderMarkers();
  }

  function deselect() {
    state.selected = null;
    state.legalForSelected = [];
    updateSquareSelection();
    renderMarkers();
  }

  /* ---------------------------------------------------------------- игроки */
  function playerInfo(color) {
    if (state.puzzle && state.puzzle.active) {
      if (color === state.humanColor) {
        return { name: 'Вы', sub: 'Решаете задачу', human: true };
      }
      return { name: 'Соперник', sub: 'Автоматический ответ', human: false, piece: 'king' };
    }
    const mode = state.started ? state.mode : state.form.mode;
    const level = resolvedLevel(LEVELS[state.started ? state.level : state.form.level] || LEVELS[0]);
    if (mode === 'bot') {
      if (color === state.humanColor) {
        return { name: 'Вы', sub: 'Игрок', human: true };
      }
      return { name: level.name, sub: `Бот · ${level.rating}`, human: false, piece: level.piece };
    }
    return {
      name: color === 1 ? 'Белые' : 'Чёрные',
      sub: 'Игрок',
      human: true
    };
  }

  function missingOf(color) {
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    for (let sq = 0; sq < 128; sq++) {
      if (sq & 0x88) { sq += 7; continue; }
      const piece = state.game.board[sq];
      if (piece && E.colorOf(piece) === color) {
        const type = E.typeOf(piece);
        if (type !== E.KING) counts[type]++;
      }
    }
    const missing = [];
    for (const type of CAPTURE_ORDER) {
      const lost = START_COUNTS[type] - counts[type];
      for (let i = 0; i < lost; i++) missing.push(type);
    }
    return missing;
  }

  function capturedBy(color) {
    return missingOf(-color);
  }

  function materialFor(color) {
    const mine = missingOf(color).reduce((sum, type) => sum + PAWN_POINTS[type], 0);
    const theirs = missingOf(-color).reduce((sum, type) => sum + PAWN_POINTS[type], 0);
    return theirs - mine;
  }

  function humanAvatar() {
    return '<span class="avatar human"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"></circle><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"></path></svg></span>';
  }

  function botAvatar(pieceName) {
    return `<span class="avatar bot"><svg class="avatar-piece w" viewBox="0 0 45 45" aria-hidden="true"><use href="#pc-${pieceName}"></use></svg></span>`;
  }

  function playerBarHtml(color) {
    const info = playerInfo(color);
    const captured = capturedBy(color);
    const material = materialFor(color);
    const capsHtml = captured.map((type) => (
      `<span class="mini-piece ${-color > 0 ? 'w' : 'b'}">${pieceSvg(-color * type)}</span>`
    )).join('');
    const materialHtml = material > 0 ? `<span class="material">+${material}</span>` : '';
    const avatar = info.human ? humanAvatar() : botAvatar(info.piece || 'pawn');
    const clockText = state.clocks.enabled ? formatClock(clockFor(color)) : '∞';
    return `
      ${avatar}
      <span class="player-meta">
        <span class="player-name">${info.name}</span>
        <span class="player-sub">${info.sub}</span>
      </span>
      <span class="captured">${capsHtml}${materialHtml}</span>
      <span class="clock${state.clocks.enabled ? '' : ' unlimited'}">${clockText}</span>
    `;
  }

  function renderPlayers() {
    const bottom = state.orientation;
    const top = -bottom;
    els.barTop.dataset.color = top === 1 ? 'w' : 'b';
    els.barBottom.dataset.color = bottom === 1 ? 'w' : 'b';
    els.barTop.innerHTML = playerBarHtml(top);
    els.barBottom.innerHTML = playerBarHtml(bottom);
    updateClocks();
  }

  function renderTags() {
    if (state.puzzle && state.puzzle.active) {
      const item = state.puzzle.item;
      const levels = (window.ChessPuzzles && window.ChessPuzzles.levels) || {};
      const diff = levels[item.level] || {};
      els.gameTags.innerHTML =
        `<span class="tag"><strong>Задача</strong></span>` +
        `<span class="tag">${item.theme}</span>` +
        `<span class="tag">${diff.name || 'Тактика'} · ${item.rating}</span>`;
      return;
    }
    const mode = state.started ? state.mode : state.form.mode;
    const level = resolvedLevel(LEVELS[state.started ? state.level : state.form.level] || LEVELS[0]);
    const timeKey = state.started ? state.timeKey : state.form.time;
    const preset = TIME_PRESETS[timeKey] || TIME_PRESETS['10+0'];
    const tags = [];
    tags.push(`<span class="tag"><strong>${mode === 'bot' ? 'Компьютер' : 'Два игрока'}</strong>${mode === 'bot' ? ` · ${level.name} · ${level.rating}` : ''}</span>`);
    tags.push(`<span class="tag">${preset.label}</span>`);
    if (mode === 'bot') {
      let colorText;
      if (state.started) colorText = state.humanColor === 1 ? 'белые' : 'чёрные';
      else if (state.form.color === 'random') colorText = 'случайно';
      else colorText = state.form.color === 'b' ? 'чёрные' : 'белые';
      tags.push(`<span class="tag">Вы · ${colorText}</span>`);
      if (state.engineName === 'Stockfish 16') tags.push('<span class="tag engine-mini">SF 16</span>');
    }
    els.gameTags.innerHTML = tags.join('');
  }

  /* ---------------------------------------------------------------- часы */
  function clockFor(color) {
    return color === 1 ? state.clocks.white : state.clocks.black;
  }

  function formatClock(ms) {
    if (ms <= 0) return '0:00';
    if (ms < 20000) {
      const sec = Math.floor(ms / 100) / 10;
      return '0:' + (sec < 10 ? '0' : '') + sec.toFixed(1);
    }
    const total = Math.ceil(ms / 1000);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function updateClocks() {
    [els.barTop, els.barBottom].forEach((bar) => {
      const color = bar.dataset.color === 'w' ? 1 : -1;
      const clockEl = bar.querySelector('.clock');
      if (!clockEl) return;
      if (!state.clocks.enabled) {
        clockEl.textContent = '∞';
        clockEl.classList.add('unlimited');
        clockEl.classList.remove('low');
      } else {
        const ms = clockFor(color);
        clockEl.textContent = formatClock(ms);
        clockEl.classList.remove('unlimited');
        clockEl.classList.toggle('low', ms > 0 && ms < 20000);
      }
      bar.classList.toggle('active', state.started && !state.over && state.game.side === color);
    });
  }

  function settleClock() {
    if (!state.clocks.running || state.over) return;
    const now = performance.now();
    const dt = Math.max(0, now - state.clocks.last);
    state.clocks.last = now;
    if (state.game.side === 1) state.clocks.white = Math.max(0, state.clocks.white - dt);
    else state.clocks.black = Math.max(0, state.clocks.black - dt);
  }

  function startClockTimer() {
    clearInterval(state.clocks.timer);
    state.clocks.timer = setInterval(tickClock, 100);
  }

  function stopClock() {
    state.clocks.running = false;
    clearInterval(state.clocks.timer);
    state.clocks.timer = null;
  }

  function tickClock() {
    if (!state.clocks.running || state.over || !state.started) return;
    settleClock();
    updateClocks();
    const ms = clockFor(state.game.side);
    if (ms <= 0) {
      const loser = state.game.side;
      if (loser === 1) state.clocks.white = 0;
      else state.clocks.black = 0;
      updateClocks();
      stopClock();
      endGame(-loser, 'timeout');
    }
  }

  /* ---------------------------------------------------------------- история */
  function sanButton(index, snap, current) {
    let mark = '';
    if (state.analysis && state.analysis.done && state.analysis.moves[index - 1]) {
      const info = CLASS_INFO[state.analysis.moves[index - 1].cls];
      if (info && info.symbol) {
        mark = `<span class="san-mark ${info.cls}" title="${info.label}">${info.symbol}</span>`;
      }
    }
    return `<button type="button" class="san${index === current ? ' current' : ''}" data-ply="${index}">${snap.san}${mark}</button>`;
  }

  function renderMoves() {
    const current = state.viewPly === null ? state.snaps.length - 1 : state.viewPly;
    let html = '';
    for (let i = 1; i < state.snaps.length; i++) {
      const snap = state.snaps[i];
      if (i % 2 === 1) {
        html += '<div class="move-row" role="listitem">';
        html += `<span class="move-no">${Math.ceil(i / 2)}.</span>`;
        html += sanButton(i, snap, current);
        if (i === state.snaps.length - 1) {
          html += '<span class="san placeholder"></span></div>';
        }
      } else {
        html += sanButton(i, snap, current) + '</div>';
      }
    }
    els.moves.innerHTML = html;
    els.movesEmpty.classList.toggle('hidden', state.snaps.length > 1);
    if (state.viewPly === null) {
      els.moves.scrollTop = els.moves.scrollHeight;
    }
  }

  function updateReviewBar() {
    const reviewing = state.viewPly !== null;
    els.reviewBar.classList.toggle('hidden', !reviewing);
    if (!reviewing) return;
    const max = state.snaps.length - 1;
    const ply = state.viewPly;
    const first = els.reviewBar.querySelector('[data-nav="first"]');
    const prev = els.reviewBar.querySelector('[data-nav="prev"]');
    const next = els.reviewBar.querySelector('[data-nav="next"]');
    const last = els.reviewBar.querySelector('[data-nav="last"]');
    first.disabled = ply <= 0;
    prev.disabled = ply <= 0;
    next.disabled = ply >= max;
    last.disabled = ply >= max;
  }

  function enterReview(ply) {
    if (!state.snaps[ply]) return;
    state.viewPly = ply;
    state.reviewGame = new E.Game(state.snaps[ply].fen);
    deselect();
    hidePromotion();
    renderBoard();
    renderMoves();
    updateReviewBar();
    updateStatus();
    renderControls();
    renderAnalysisPanel();
    updatePuzzlePanel();
  }

  function exitReview() {
    if (state.viewPly === null) return;
    state.viewPly = null;
    state.reviewGame = null;
    deselect();
    renderBoard();
    renderMoves();
    updateReviewBar();
    updateStatus();
    renderControls();
    renderAnalysisPanel();
    updatePuzzlePanel();
  }

  function stepReview(delta) {
    const max = state.snaps.length - 1;
    let ply = state.viewPly === null ? max : state.viewPly;
    ply = Math.max(0, Math.min(max, ply + delta));
    if (ply === max) exitReview();
    else enterReview(ply);
  }

  /* ---------------------------------------------------------------- статус */
  function resultShort() {
    if (!state.result) return 'Партия завершена';
    const reason = state.result.reason;
    if (reason === 'checkmate') return 'Мат!';
    if (reason === 'timeout') return 'Время вышло';
    if (reason === 'resign') return 'Сдача';
    if (reason === 'stalemate') return 'Пат — ничья';
    if (reason === 'repetition') return 'Ничья: повторение';
    if (reason === 'fifty') return 'Ничья: 50 ходов';
    if (reason === 'material') return 'Ничья: мало фигур';
    return 'Партия завершена';
  }

  function updateStatus() {
    const puzzle = state.puzzle && state.puzzle.active ? state.puzzle : null;
    els.statusLine.classList.toggle('thinking', state.botThinking || !!(puzzle && puzzle.waiting));
    els.statusLine.classList.toggle('over', state.over || !!(puzzle && puzzle.solved));

    if (state.viewPly !== null) {
      els.statusText.textContent = `Просмотр · ход ${Math.ceil(state.viewPly / 2)}`;
      return;
    }
    if (puzzle) {
      if (puzzle.solved) els.statusText.textContent = 'Задача решена!';
      else if (puzzle.waiting) els.statusText.textContent = 'Соперник отвечает…';
      else if (state.game.side === state.humanColor) els.statusText.textContent = 'Задача · ваш ход';
      else els.statusText.textContent = 'Задача · ход соперника';
      return;
    }
    if (!state.started) {
      els.statusText.textContent = 'Начните игру';
      return;
    }
    if (state.over) {
      els.statusText.textContent = resultShort();
      return;
    }
    if (state.botThinking) {
      els.statusText.textContent = `${LEVELS[state.level].name} думает…`;
      return;
    }
    const check = state.game.inCheck(state.game.side) ? ' · Шах!' : '';
    if (state.mode === 'bot') {
      els.statusText.textContent = state.game.side === state.humanColor
        ? `Ваш ход${check}`
        : `Ход компьютера${check}`;
    } else {
      els.statusText.textContent = (state.game.side === 1 ? 'Ход белых' : 'Ход чёрных') + check;
    }
  }

  function renderControls() {
    const puzzle = state.puzzle && state.puzzle.active;
    els.controls.classList.toggle('hidden', !!puzzle);
    els.panelActions.classList.toggle('hidden', !!puzzle);
    els.analyzeBtn.disabled = !!puzzle || !state.started || !state.over || state.snaps.length < 2;
    if (puzzle) return;
    const noHistory = !state.game || state.game.history.length === 0;
    els.undoBtn.disabled = !state.started || state.over || noHistory || state.viewPly !== null;
    els.resignBtn.disabled = !state.started || state.over;
  }

  function canHumanMove() {
    if (state.puzzle && state.puzzle.active) {
      return !state.puzzle.solved && !state.puzzle.waiting &&
        state.game.side === state.humanColor && state.viewPly === null && !state.promotion;
    }
    if (!state.started || state.over || state.viewPly !== null || state.promotion) return false;
    if (state.mode === 'bot' && state.game.side === state.botColor) return false;
    return true;
  }
  /* __APP_PART3__ */

  /* ---------------------------------------------------------------- мышь и касания */
  function squareFromPoint(clientX, clientY) {
    const rect = els.board.getBoundingClientRect();
    const size = rect.width / 8;
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    if (x < 0 || y < 0 || x >= rect.width || y >= rect.height) return null;
    const vc = Math.min(7, Math.floor(x / size));
    const vr = Math.min(7, Math.floor(y / size));
    return state.orientation === 1 ? vr * 16 + vc : 119 - vr * 16 - vc;
  }

  function squareRect(sq) {
    const rect = els.board.getBoundingClientRect();
    const size = rect.width / 8;
    const pos = visualOf(sq);
    return {
      left: rect.left + pos.col * size,
      top: rect.top + pos.row * size,
      size
    };
  }

  function onPointerDown(event) {
    if (!canHumanMove()) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target.closest('#promo')) return;
    const sq = squareFromPoint(event.clientX, event.clientY);
    if (sq === null) return;

    const piece = state.game.board[sq];
    const own = !!piece && E.colorOf(piece) === state.game.side;
    const pd = {
      sq,
      startX: event.clientX,
      startY: event.clientY,
      dragging: false,
      own,
      wasSelected: state.selected === sq,
      pointerId: event.pointerId
    };
    state.pointer = pd;

    if (own) {
      ensureAudio();
      if (!pd.wasSelected) selectSquare(sq);
      try { els.board.setPointerCapture(event.pointerId); } catch (err) { /* не критично */ }
    }
    event.preventDefault();
  }

  function onPointerMove(event) {
    const pd = state.pointer;
    if (!pd) return;
    if (!pd.dragging && pd.own) {
      const dx = event.clientX - pd.startX;
      const dy = event.clientY - pd.startY;
      if (dx * dx + dy * dy > 30) {
        pd.dragging = true;
        startDrag(pd.sq, event.clientX, event.clientY);
      }
    }
    if (pd.dragging) positionGhost(event.clientX, event.clientY);
  }

  function onPointerUp(event) {
    const pd = state.pointer;
    if (!pd) return;
    state.pointer = null;
    const wasDragging = pd.dragging;
    const sq = squareFromPoint(event.clientX, event.clientY);

    if (wasDragging) {
      endDrag();
      if (sq !== null && sq !== pd.sq) attemptMove(pd.sq, sq);
      return;
    }

    if (pd.own) {
      if (sq !== null && sq !== pd.sq) {
        attemptMove(pd.sq, sq);
        return;
      }
      if (pd.wasSelected) deselect();
      return;
    }

    if (state.selected !== null && sq !== null) {
      const from = state.selected;
      const moved = attemptMove(from, sq);
      if (!moved) {
        const piece = state.game.board[sq];
        if (piece && E.colorOf(piece) === state.game.side && !state.over) selectSquare(sq);
        else deselect();
      }
    }
  }

  function startDrag(sq, x, y) {
    const piece = state.game.board[sq];
    if (!piece) return;
    const size = els.board.getBoundingClientRect().width / 8;
    const ghost = document.createElement('div');
    ghost.className = 'drag-ghost ' + (piece > 0 ? 'w' : 'b');
    ghost.style.width = size + 'px';
    ghost.style.height = size + 'px';
    ghost.innerHTML = pieceSvg(piece);
    document.body.appendChild(ghost);
    state.dragGhost = ghost;
    positionGhost(x, y);
    const src = els.pieces.querySelector(`.piece[data-sq="${sq}"]`);
    if (src) src.classList.add('drag-src');
  }

  function positionGhost(x, y) {
    if (!state.dragGhost) return;
    state.dragGhost.style.left = x + 'px';
    state.dragGhost.style.top = y + 'px';
  }

  function endDrag() {
    if (state.dragGhost) {
      state.dragGhost.remove();
      state.dragGhost = null;
    }
    $$('.piece.drag-src').forEach((el) => el.classList.remove('drag-src'));
  }

  /* ---------------------------------------------------------------- ход */
  function attemptMove(from, to) {
    if (state.puzzle && state.puzzle.active) return attemptPuzzleMove(from, to);
    if (!canHumanMove()) return false;
    const moves = state.game.legalMoves().filter((m) => E.moveFrom(m) === from && E.moveTo(m) === to);
    if (!moves.length) return false;
    if (E.movePromo(moves[0])) {
      if (state.settings.autoPromote) {
        const queen = moves.find((m) => E.movePromo(m) === E.QUEEN) || moves[0];
        commitMove(queen);
        return true;
      }
      openPromotion(from, to, moves);
      return true;
    }
    commitMove(moves[0]);
    return true;
  }

  function openPromotion(from, to, moves) {
    state.promotion = { from, to, moves };
    const color = state.game.side;
    const order = [E.QUEEN, E.KNIGHT, E.ROOK, E.BISHOP];
    els.promoPieces.innerHTML = order.map((type) => {
      const exists = moves.some((m) => E.movePromo(m) === type);
      if (!exists) return '';
      return `<button type="button" class="promo-btn ${color === 1 ? 'w' : 'b'}" data-promo="${type}" aria-label="${PIECE_KEY[type]}">${pieceSvg(color * type)}</button>`;
    }).join('');
    deselect();
    els.promo.classList.remove('hidden');
    els.promo.querySelector('.promo-btn')?.focus({ preventScroll: true });
  }

  function hidePromotion() {
    state.promotion = null;
    els.promo.classList.add('hidden');
  }

  function collectMoverRects(from, to, piece) {
    const movers = [{ from, to, rect: squareRect(from) }];
    if (E.typeOf(piece) === E.KING && Math.abs(to - from) === 2) {
      const kingSide = to > from;
      const rookFrom = kingSide ? to + 1 : to - 2;
      const rookTo = kingSide ? to - 1 : to + 1;
      movers.push({ from: rookFrom, to: rookTo, rect: squareRect(rookFrom) });
    }
    return movers;
  }

  function animateMovers(movers) {
    if (!state.settings.animations || state.settings.animationMs <= 0) return;
    for (const mover of movers) {
      const el = els.pieces.querySelector(`.piece[data-sq="${mover.to}"]`);
      if (!el) continue;
      const target = squareRect(mover.to);
      const dx = mover.rect.left - target.left;
      const dy = mover.rect.top - target.top;
      if (!dx && !dy) continue;
      el.classList.add('animating');
      const animation = el.animate(
        [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: 'translate(0, 0)' }],
        { duration: state.settings.animationMs, easing: 'cubic-bezier(.2,.75,.3,1)' }
      );
      animation.onfinish = () => el.classList.remove('animating');
    }
  }

  function commitMove(move) {
    if (!state.started || state.over) return false;
    const game = state.game;
    const from = E.moveFrom(move);
    const to = E.moveTo(move);
    const piece = game.board[from];
    if (!piece) return false;
    const mover = game.side;
    const type = E.typeOf(piece);
    const promo = E.movePromo(move);
    const isEp = type === E.PAWN && to === game.ep && game.board[to] === 0;
    const isCapture = game.board[to] !== 0 || isEp;
    const isCastle = type === E.KING && Math.abs(to - from) === 2;

    if (state.clocks.enabled && state.clocks.running) {
      settleClock();
      if (clockFor(mover) <= 0) {
        if (mover === 1) state.clocks.white = 0;
        else state.clocks.black = 0;
        updateClocks();
        stopClock();
        endGame(-mover, 'timeout');
        return false;
      }
    }

    let san;
    try {
      san = game.san(move);
    } catch (err) {
      return false;
    }

    const movers = collectMoverRects(from, to, piece);
    game.makeMove(move);

    state.lastMove = { from, to };
    state.selected = null;
    state.legalForSelected = [];
    state.viewPly = null;
    state.reviewGame = null;
    state.promotion = null;
    state.snaps.push({ fen: game.fen(), move: { from, to }, san, color: mover });

    if (state.clocks.enabled) {
      if (!state.clocks.running) {
        state.clocks.running = true;
        startClockTimer();
      }
      if (mover === 1) state.clocks.white += state.clocks.inc;
      else state.clocks.black += state.clocks.inc;
      state.clocks.last = performance.now();
    }

    const check = game.inCheck(game.side);

    renderBoard();
    animateMovers(movers);
    renderPlayers();
    renderMoves();
    renderTags();
    updateClocks();
    updateStatus();
    updateReviewBar();
    renderControls();

    if (state.puzzle && state.puzzle.active) {
      if (check) playSound('check');
      else if (isCastle) playSound('castle');
      else if (isCapture) playSound('capture');
      else if (promo) playSound('promote');
      else playSound('move');
      afterPuzzleMove();
      return true;
    }

    const status = game.status();
    if (status) {
      endGame(status.winner, status.reason);
      return true;
    }

    if (check) playSound('check');
    else if (isCastle) playSound('castle');
    else if (isCapture) playSound('capture');
    else if (promo) playSound('promote');
    else playSound('move');

    if (state.mode === 'bot' && game.side === state.botColor) {
      scheduleBot(280);
    } else {
      updateStatus();
    }
    return true;
  }

  /* ---------------------------------------------------------------- отмена и сдача */
  function takeback() {
    if (state.puzzle && state.puzzle.active) return;
    if (!state.started || state.over || !state.game.history.length) return;
    cancelBot();
    resetAnalysis();
    hidePromotion();
    resetResign();

    let popped = 0;
    do {
      state.game.undoMove();
      state.snaps.pop();
      popped++;
    } while (
      state.game.history.length &&
      state.mode === 'bot' &&
      state.game.side !== state.humanColor
    );

    state.over = false;
    state.result = null;
    clearResultTimer();
    hideResult();
    state.viewPly = null;
    state.reviewGame = null;
    state.selected = null;
    state.legalForSelected = [];
    state.lastMove = state.snaps[state.snaps.length - 1].move;
    state.clocks.last = performance.now();

    renderAll();
    if (state.mode === 'bot' && state.game.side === state.botColor) {
      scheduleBot(300);
    } else {
      updateStatus();
    }
    showToast(popped > 1 ? 'Отменены два хода' : 'Ход отменён');
  }

  function flipBoard() {
    state.orientation *= -1;
    renderBoard();
    renderPlayers();
    renderTags();
  }

  function updateResignButton() {
    els.resignBtn.classList.remove('armed');
    els.resignBtn.innerHTML = '<span class="ico">⚑</span> Сдаться';
    els.resignBtn.disabled = !state.started || state.over;
  }

  function resetResign() {
    state.resignArmed = false;
    clearTimeout(state.resignTimer);
    state.resignTimer = null;
    updateResignButton();
  }

  function handleResign() {
    if (!state.started || state.over) return;
    if (!state.settings.confirmResign) {
      const loser = state.mode === 'bot' ? state.humanColor : state.game.side;
      endGame(-loser, 'resign');
      return;
    }
    if (!state.resignArmed) {
      state.resignArmed = true;
      els.resignBtn.classList.add('armed');
      els.resignBtn.textContent = 'Точно сдаться?';
      clearTimeout(state.resignTimer);
      state.resignTimer = setTimeout(resetResign, 3200);
      return;
    }
    resetResign();
    const loser = state.mode === 'bot' ? state.humanColor : state.game.side;
    endGame(-loser, 'resign');
  }

  function onKeyDown(event) {
    if (event.key === 'Escape') {
      if (!els.pgnOverlay.classList.contains('hidden')) { closePgnDialog(); return; }
      if (!els.settingsOverlay.classList.contains('hidden')) { closeSettings(); return; }
      if (!els.archiveOverlay.classList.contains('hidden')) { closeArchive(); return; }
      if (!els.puzzleSuccess.classList.contains('hidden')) { hidePuzzleSuccess(); return; }
      if (!els.puzzleOverlay.classList.contains('hidden')) { closePuzzleList(); return; }
      if (!els.promo.classList.contains('hidden')) { hidePromotion(); return; }
      if (!els.resultOverlay.classList.contains('hidden')) { hideResult(); return; }
      if (!els.setupOverlay.classList.contains('hidden')) {
        if (state.started) closeSetup(true);
        return;
      }
      if (state.viewPly !== null) { exitReview(); return; }
      if (state.selected !== null) { deselect(); return; }
    }

    const tag = event.target && event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (event.target && event.target.isContentEditable)) {
      return;
    }

    if ((event.ctrlKey || event.metaKey) && (event.key === 'z' || event.key === 'Z' || event.key === 'я' || event.key === 'Я')) {
      event.preventDefault();
      takeback();
      return;
    }

    if (state.viewPly !== null) {
      if (event.key === 'ArrowLeft') { event.preventDefault(); stepReview(-1); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); stepReview(1); }
      else if (event.key === 'Home') { event.preventDefault(); enterReview(0); }
      else if (event.key === 'End') { event.preventDefault(); exitReview(); }
      return;
    }

    if (event.key === 'f' || event.key === 'F' || event.key === 'а' || event.key === 'А') {
      flipBoard();
    }
  }
  /* ---------------------------------------------------------------- компьютер */
  function ensureWorker() {
    if (state.worker) return state.worker;
    if (typeof Worker === 'undefined') return null;
    try {
      const workerUrl = window.CHESS_WORKER_URL || 'js/ai-worker.js';
      const worker = new Worker(workerUrl);
      worker.onmessage = onBotMessage;
      worker.onerror = onBotError;
      state.worker = worker;
      return worker;
    } catch (err) {
      return null;
    }
  }

  function cancelBot() {
    state.botId++;
    state.botThinking = false;
    state.pendingBot = null;
    if (state.stockfish) state.stockfish.stop();
    if (state.botTimer) {
      clearTimeout(state.botTimer);
      state.botTimer = null;
    }
    if (state.worker) {
      state.worker.onmessage = null;
      state.worker.onerror = null;
      state.worker.terminate();
      state.worker = null;
    }
  }

  function scheduleBot(delay) {
    if (state.over || state.mode !== 'bot' || state.game.side !== state.botColor) return;
    const id = ++state.botId;
    state.botThinking = true;
    state.pendingBot = null;
    updateStatus();
    renderControls();

    if (state.botTimer) clearTimeout(state.botTimer);
    state.botTimer = setTimeout(() => {
      state.botTimer = null;
      if (id !== state.botId || state.over) return;
      const level = resolvedLevel(LEVELS[state.level] || LEVELS[0]);
      const options = {
        depth: level.depth,
        time: level.time,
        randomChance: level.randomChance,
        randomness: level.randomness
      };
      const fen = state.game.fen();
      state.pendingBot = { id, fen, options };

      if (level.engine === 'stockfish' && stockfishUsable()) {
        stockfishSearch({
          fen,
          depth: level.depth,
          movetime: level.time,
          elo: level.elo,
          skill: level.skill
        }).then((result) => {
          if (id !== state.botId || state.over || !state.botThinking) return;
          state.pendingBot = null;
          finishBotMove(result.move);
        }).catch(() => {
          if (id !== state.botId || state.over || !state.botThinking) return;
          fallbackSearch(id, fen, options);
        });
        return;
      }

      const worker = ensureWorker();
      if (worker) {
        try {
          worker.postMessage({ type: 'search', id, fen, options });
        } catch (err) {
          onBotError();
        }
      } else {
        fallbackSearch(id, fen, options);
      }
    }, Math.max(0, delay || 200));
  }

  function moveFromUci(game, uci) {
    if (!uci || typeof uci !== 'string') return null;
    const legal = game.legalMoves();
    for (const move of legal) {
      if (game.uci(move) === uci) return move;
    }
    return null;
  }

  function finishBotMove(move) {
    state.botThinking = false;
    state.pendingBot = null;
    const legal = state.game.legalMoves();
    let chosen = move;
    if (typeof chosen === 'string') chosen = moveFromUci(state.game, chosen);
    if (!legal.includes(chosen)) {
      chosen = legal.length ? legal[Math.floor(Math.random() * legal.length)] : null;
    }
    if (chosen === null) {
      const status = state.game.status();
      if (status) endGame(status.winner, status.reason);
      else updateStatus();
      return;
    }
    commitMove(chosen);
  }

  function onBotMessage(event) {
    const data = event.data || {};
    if (!data.id || data.id !== state.botId) return;
    if (data.type === 'error') {
      onBotError();
      return;
    }
    if (data.type !== 'result' || !state.botThinking) return;
    finishBotMove(data.move);
  }

  function onBotError() {
    if (state.worker) {
      state.worker.onmessage = null;
      state.worker.onerror = null;
      state.worker.terminate();
      state.worker = null;
    }
    if (!state.botThinking || !state.pendingBot) return;
    const pending = state.pendingBot;
    state.pendingBot = null;
    fallbackSearch(pending.id, pending.fen, pending.options);
  }

  function fallbackSearch(id, fen, options) {
    setTimeout(() => {
      if (id !== state.botId || state.over || !state.botThinking) return;
      let move = null;
      try {
        const probe = new E.Game(fen, { track: false });
        const result = E.search(probe, {
          depth: Math.min(2, options.depth || 2),
          time: Math.min(450, options.time || 450),
          randomChance: options.randomChance || 0,
          randomness: options.randomness || 0
        });
        move = result.move;
      } catch (err) { /* выберем случайный */ }
      if (id !== state.botId || state.over || !state.botThinking) return;
      finishBotMove(move);
    }, 20);
  }

  /* ---------------------------------------------------------------- итог */
  function clearResultTimer() {
    if (state.resultTimer) {
      clearTimeout(state.resultTimer);
      state.resultTimer = null;
    }
  }

  function endGame(winner, reason) {
    if (state.over) return;
    state.over = true;
    state.result = { winner, reason };
    stopClock();
    cancelBot();
    hidePromotion();
    resetResign();
    state.selected = null;
    state.legalForSelected = [];
    state.viewPly = null;
    state.reviewGame = null;

    renderBoard();
    renderPlayers();
    renderMoves();
    updateClocks();
    updateStatus();
    updateReviewBar();
    renderControls();
    playSound('end');
    saveToArchive();

    clearResultTimer();
    state.resultTimer = setTimeout(showResult, 480);
  }

  function showResult() {
    if (!state.result) return;
    state.resultTimer = null;
    const { winner, reason } = state.result;
    let cls = 'draw';
    let eyebrow = 'Партия завершена';
    let title = 'Ничья';
    let sub = '';
    let score = '½ – ½';
    let emblem = 'bishop';

    if (winner === 0) {
      if (reason === 'stalemate') sub = 'Патовое положение — ходов нет, но шаха тоже.';
      else if (reason === 'repetition') sub = 'Одна и та же позиция повторилась три раза.';
      else if (reason === 'fifty') sub = 'Пятьдесят ходов без взятий и движения пешек.';
      else if (reason === 'material') sub = 'На доске недостаточно фигур для мата.';
      else sub = 'Партия завершилась вничью.';
      eyebrow = 'Ничья';
    } else {
      score = winner === 1 ? '1 – 0' : '0 – 1';
      if (reason === 'checkmate') title = 'Мат!';
      else if (reason === 'timeout') title = 'Время вышло';
      else if (reason === 'resign') title = 'Сдача';

      if (state.mode === 'bot') {
        if (winner === state.humanColor) {
          cls = 'win';
          eyebrow = 'Вы победили';
          emblem = 'queen';
        } else {
          cls = 'lose';
          eyebrow = 'Компьютер победил';
          emblem = 'king';
        }
      } else {
        cls = 'win';
        eyebrow = winner === 1 ? 'Победа белых' : 'Победа чёрных';
        emblem = winner === 1 ? 'queen' : 'king';
      }
      if (reason === 'timeout') sub = 'У соперника закончилось время.';
      else if (reason === 'resign') {
        if (state.mode === 'bot') {
          sub = winner === state.humanColor ? 'Соперник признал поражение.' : 'Вы признали поражение.';
        } else {
          sub = winner === 1 ? 'Чёрные признали поражение.' : 'Белые признали поражение.';
        }
      } else sub = '';
    }

    els.resultCard.classList.remove('win', 'lose', 'draw');
    els.resultCard.classList.add(cls);
    els.resultEyebrow.textContent = eyebrow;
    els.resultTitle.textContent = title;
    els.resultSub.textContent = sub;
    els.resultScore.textContent = score;
    $('#result-emblem').innerHTML = `<svg viewBox="0 0 45 45"><use href="#pc-${emblem}"></use></svg>`;
    els.resultOverlay.classList.remove('hidden');
    $('#rematch-btn').focus({ preventScroll: true });
  }

  function hideResult() {
    els.resultOverlay.classList.add('hidden');
    clearResultTimer();
  }

  function openSetup() {
    if (state.puzzle && state.puzzle.active) leavePuzzle(false);
    showSetup(false);
  }

  /* ---------------------------------------------------------------- звук */
  function updateSoundUI() {
    const on = !!state.settings.sound;
    els.soundBtn.setAttribute('aria-pressed', String(on));
    els.soundBtn.setAttribute('aria-label', on ? 'Выключить звук' : 'Включить звук');
    $('.sound-on', els.soundBtn).classList.toggle('hidden', !on);
    $('.sound-off', els.soundBtn).classList.toggle('hidden', on);
  }

  function ensureAudio() {
    if (!state.settings.sound) return null;
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      if (!state.audio) state.audio = new Ctx();
      if (state.audio.state === 'suspended') state.audio.resume();
      return state.audio;
    } catch (err) {
      return null;
    }
  }

  function tone(freq, dur, type, volume, delay, slideTo) {
    const ctx = ensureAudio();
    if (!ctx) return;
    const level = Math.max(0, Math.min(1, volume * (state.settings.volume / 70)));
    const t = ctx.currentTime + (delay || 0);
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type || 'sine';
    osc.frequency.setValueAtTime(freq, t);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(Math.max(20, slideTo), t + dur);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.001, level), t + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t);
    osc.stop(t + dur + 0.03);
  }

  function noiseBurst(dur, volume, cutoff, delay) {
    const ctx = ensureAudio();
    if (!ctx) return;
    const level = Math.max(0, Math.min(1, volume * (state.settings.volume / 70)));
    if (level <= 0) return;
    const length = Math.max(1, Math.floor(ctx.sampleRate * dur));
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i++) {
      data[i] = (Math.random() * 2 - 1) * (1 - i / length);
    }
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = cutoff;
    const gain = ctx.createGain();
    gain.gain.value = level;
    source.connect(filter).connect(gain).connect(ctx.destination);
    source.start(ctx.currentTime + (delay || 0));
  }

  function playSound(kind) {
    if (!state.settings.sound) return;
    try {
      if (kind === 'move') {
        noiseBurst(0.035, 0.08, 1800);
        tone(190, 0.045, 'triangle', 0.045);
      } else if (kind === 'capture') {
        noiseBurst(0.06, 0.12, 900);
        tone(120, 0.08, 'sine', 0.065, 0, 85);
      } else if (kind === 'check') {
        tone(780, 0.09, 'sine', 0.04);
        tone(990, 0.11, 'sine', 0.035, 0.1);
      } else if (kind === 'castle') {
        tone(230, 0.05, 'triangle', 0.045);
        tone(310, 0.05, 'triangle', 0.04, 0.08);
      } else if (kind === 'promote') {
        tone(520, 0.07, 'sine', 0.035);
        tone(660, 0.07, 'sine', 0.035, 0.08);
        tone(880, 0.1, 'sine', 0.035, 0.16);
      } else if (kind === 'start') {
        tone(440, 0.08, 'sine', 0.035);
        tone(660, 0.1, 'sine', 0.035, 0.09);
      } else if (kind === 'end') {
        tone(392, 0.12, 'triangle', 0.04);
        tone(494, 0.12, 'triangle', 0.035, 0.12);
        tone(659, 0.2, 'triangle', 0.035, 0.24);
      } else if (kind === 'wrong') {
        noiseBurst(0.05, 0.05, 700);
        tone(190, 0.12, 'sawtooth', 0.035, 0, 120);
      } else if (kind === 'toggle') {
        tone(700, 0.06, 'sine', 0.025);
      }
    } catch (err) { /* звук не критичен */ }
  }

  function toggleSound() {
    state.settings.sound = !state.settings.sound;
    updateSoundUI();
    saveSettings();
    if (state.settings.sound) {
      ensureAudio();
      playSound('toggle');
    }
    showToast(state.settings.sound ? 'Звук включён' : 'Звук выключен');
  }

  /* ---------------------------------------------------------------- разбор партии */
  const CLASS_INFO = {
    best: { label: 'Лучший ход', symbol: '★', cls: 'best' },
    excellent: { label: 'Отличный ход', symbol: '', cls: 'excellent' },
    good: { label: 'Хороший ход', symbol: '', cls: 'good' },
    inaccuracy: { label: 'Неточность', symbol: '?!', cls: 'inaccuracy' },
    mistake: { label: 'Ошибка', symbol: '?', cls: 'mistake' },
    blunder: { label: 'Зевок', symbol: '??', cls: 'blunder' }
  };

  function resetAnalysis() {
    state.analysisToken++;
    state.analysis = null;
    renderAnalysisPanel();
  }

  function startAnalysis() {
    if (state.puzzle && state.puzzle.active) {
      showToast('Разбор доступен для обычных партий');
      return;
    }
    if (!state.started || state.snaps.length < 2) {
      showToast('Сначала сделайте хотя бы один ход');
      return;
    }
    if (!state.over) {
      showToast('Разбор будет доступен после окончания партии');
      return;
    }
    if (state.analysis && state.analysis.running) {
      renderAnalysisPanel();
      return;
    }
    if (state.analysis && state.analysis.done) {
      renderAnalysisPanel();
      showToast('Разбор уже готов');
      return;
    }
    hideResult();
    const token = ++state.analysisToken;
    state.analysis = {
      token,
      running: true,
      done: false,
      evals: [],
      moves: [],
      summary: null,
      total: state.snaps.length,
      useSf: stockfishUsable(),
      engine: stockfishUsable() ? 'Stockfish 16' : 'встроенный движок'
    };
    renderAnalysisPanel();
    showToast('Анализирую партию…');
    setTimeout(() => analyzePosition(0, token), 40);
  }

  function analyzePosition(index, token) {
    const analysis = state.analysis;
    if (!analysis || token !== analysis.token) return;
    if (index >= analysis.total) {
      finishAnalysis(token);
      return;
    }

    let game;
    try {
      game = new E.Game(state.snaps[index].fen, { track: false });
    } catch (err) {
      analysis.evals.push({ cp: 0, bestUci: '', bestSan: '', depth: 0, error: true });
      renderAnalysisPanel();
      setTimeout(() => analyzePosition(index + 1, token), 0);
      return;
    }

    const legal = game.legalMoves();
    if (!legal.length) {
      const mate = game.inCheck(game.side);
      const cp = mate ? (game.side === 1 ? -100000 : 100000) : 0;
      analysis.evals.push({ cp, bestUci: '', bestSan: '', depth: 0, terminal: true });
      renderAnalysisPanel();
      setTimeout(() => analyzePosition(index + 1, token), 0);
      return;
    }

    if (analysis.useSf) {
      stockfishSearch({
        fen: state.snaps[index].fen,
        depth: state.settings.analysisDepth,
        movetime: state.settings.analysisTime
      }).then((result) => {
        if (!state.analysis || token !== state.analysis.token) return;
        const cp = game.side === 1 ? result.cp : -result.cp;
        const move = result.move ? moveFromUci(game, result.move) : null;
        let bestSan = '';
        if (move !== null) {
          try { bestSan = game.san(move); } catch (err) { bestSan = ''; }
        }
        analysis.evals.push({
          cp,
          bestUci: move !== null ? game.uci(move) : '',
          bestSan,
          depth: result.depth || 0
        });
        renderAnalysisPanel();
        setTimeout(() => analyzePosition(index + 1, token), 0);
      }).catch(() => {
        if (!state.analysis || token !== state.analysis.token) return;
        analysis.useSf = false;
        analysis.engine = 'встроенный движок';
        analyzePositionCustom(index, token, game);
      });
      return;
    }

    analyzePositionCustom(index, token, game);
  }

  function analyzePositionCustom(index, token, game) {
    const analysis = state.analysis;
    if (!analysis || token !== analysis.token) return;
    let entry;
    try {
      const legal = game.legalMoves();
      if (!legal.length) {
        const mate = game.inCheck(game.side);
        const cp = mate ? (game.side === 1 ? -100000 : 100000) : 0;
        entry = { cp, bestUci: '', bestSan: '', depth: 0, terminal: true };
      } else {
        const result = E.search(game, { depth: 3, time: 200 });
        const cp = game.side === 1 ? result.score : -result.score;
        let bestSan = '';
        if (result.move !== null) {
          try { bestSan = game.san(result.move); } catch (err) { bestSan = ''; }
        }
        entry = {
          cp,
          bestUci: result.move !== null ? game.uci(result.move) : '',
          bestSan,
          depth: result.depth
        };
      }
    } catch (err) {
      entry = { cp: 0, bestUci: '', bestSan: '', depth: 0, error: true };
    }

    analysis.evals.push(entry);
    renderAnalysisPanel();
    setTimeout(() => analyzePosition(index + 1, token), 0);
  }

  function finishAnalysis(token) {
    const analysis = state.analysis;
    if (!analysis || token !== analysis.token) return;

    const moves = [];
    let accuracySum = 0;
    let counted = 0;
    let bestCount = 0;
    let inaccuracies = 0;
    let mistakes = 0;
    let blunders = 0;

    for (let ply = 1; ply < state.snaps.length; ply++) {
      const before = analysis.evals[ply - 1];
      const after = analysis.evals[ply];
      if (!before || !after) continue;
      const snap = state.snaps[ply];
      const mover = snap.color;
      const beforeCp = mateSafeCp(before.cp);
      const afterCp = mateSafeCp(after.cp);
      let loss = mover === 1 ? beforeCp - afterCp : afterCp - beforeCp;
      loss = Math.max(0, Math.min(2000, loss));
      const isBest = !!before.bestSan && before.bestSan === snap.san;
      const cls = classifyMove(loss, isBest);
      if (cls === 'best') bestCount++;
      else if (cls === 'inaccuracy') inaccuracies++;
      else if (cls === 'mistake') mistakes++;
      else if (cls === 'blunder') blunders++;
      accuracySum += 100 * Math.exp(-loss / 200);
      counted++;
      moves.push({
        ply,
        snap,
        cls,
        loss,
        isBest,
        bestSan: before.bestSan,
        evalBefore: before.cp,
        evalAfter: after.cp
      });
    }

    analysis.running = false;
    analysis.done = true;
    analysis.moves = moves;
    analysis.summary = {
      accuracy: counted ? Math.round(accuracySum / counted) : 0,
      best: bestCount,
      inaccuracy: inaccuracies,
      mistake: mistakes,
      blunder: blunders,
      avgLoss: counted ? Math.round(moves.reduce((sum, m) => sum + m.loss, 0) / counted) : 0,
      engine: analysis.engine || 'встроенный движок'
    };

    renderMoves();
    renderAnalysisPanel();
    renderBoard();
    updateStatus();
    const summary = analysis.summary;
    showToast(`Разбор готов · точность ${summary.accuracy}%`);
  }

  function classifyMove(loss, isBest) {
    if (isBest) return 'best';
    if (loss <= 20) return 'excellent';
    if (loss <= 50) return 'good';
    if (loss <= 110) return 'inaccuracy';
    if (loss <= 250) return 'mistake';
    return 'blunder';
  }

  function mateSafeCp(cp) {
    if (cp > 90000) return 1000;
    if (cp < -90000) return -1000;
    return Math.max(-1000, Math.min(1000, cp));
  }

  function evalText(cp) {
    if (cp > 90000 || cp < -90000) return '#';
    const pawns = Math.abs(cp) / 100;
    return (cp >= 0 ? '+' : '−') + pawns.toFixed(2);
  }

  function evalPhrase(cp) {
    if (cp > 90000) return 'мат в пользу белых';
    if (cp < -90000) return 'мат в пользу чёрных';
    if (Math.abs(cp) < 30) return 'примерно равно';
    return cp > 0 ? 'перевес белых' : 'перевес чёрных';
  }

  function renderAnalysisPanel() {
    const analysis = state.analysis;
    const visible = !!analysis && !(state.puzzle && state.puzzle.active);
    els.analysisPanel.classList.toggle('hidden', !visible);
    if (!visible) return;

    if (analysis.running) {
      els.analysisProgress.textContent = `${analysis.evals.length} / ${analysis.total}`;
    } else if (analysis.done) {
      els.analysisProgress.textContent = `Готово · ${analysis.moves.length} ход.`;
    } else {
      els.analysisProgress.textContent = '';
    }

    renderEvalChart();

    if (analysis.running) {
      els.analysisSummary.innerHTML = '<span class="analysis-badge">Движок считает варианты…</span>';
      els.analysisCurrent.innerHTML = '<span class="muted">Оценка появится по мере готовности графика.</span>';
      return;
    }

    if (analysis.done && analysis.summary) {
      const s = analysis.summary;
      let badges = `<span class="analysis-badge accuracy">Точность ${s.accuracy}%</span>`;
      if (s.engine) badges += `<span class="analysis-badge" title="Движок разбора">${s.engine === 'Stockfish 16' ? 'SF 16' : 'движок'}</span>`;
      if (s.best) badges += `<span class="analysis-badge" title="Лучшие ходы">★ ${s.best}</span>`;
      if (s.inaccuracy) badges += `<span class="analysis-badge" title="Неточности">?! ${s.inaccuracy}</span>`;
      if (s.mistake) badges += `<span class="analysis-badge bad" title="Ошибки">? ${s.mistake}</span>`;
      if (s.blunder) badges += `<span class="analysis-badge bad" title="Зевки">?? ${s.blunder}</span>`;
      if (!s.inaccuracy && !s.mistake && !s.blunder) {
        badges += '<span class="analysis-badge">Без грубых ошибок</span>';
      }
      els.analysisSummary.innerHTML = badges;
    }

    els.analysisCurrent.innerHTML = analysisCurrentHtml();
  }

  function analysisCurrentHtml() {
    const analysis = state.analysis;
    if (!analysis) return '';
    if (analysis.running) {
      return '<span class="muted">Движок оценивает позиции. Можно продолжать смотреть партию.</span>';
    }
    if (!analysis.done) return '';

    const ply = state.viewPly === null ? state.snaps.length - 1 : state.viewPly;
    const ev = analysis.evals[ply];
    const lastMove = ply > 0 ? analysis.moves[ply - 1] : null;
    let html = '';
    if (ev) {
      html += `Оценка: <b>${evalText(ev.cp)}</b> <span class="muted">(${evalPhrase(ev.cp)})</span>`;
    }
    if (lastMove) {
      const info = CLASS_INFO[lastMove.cls];
      html += `<br>${lastMove.snap.san} — <span class="cls-${info.cls}">${info.label}</span>`;
      if (lastMove.cls === 'best') {
        html += ' <span class="muted">— так и нужно</span>';
      } else if (lastMove.bestSan) {
        html += `.<br>Лучше: <b>${lastMove.bestSan}</b> <span class="muted">(${evalText(lastMove.evalBefore)})</span>`;
      }
    } else if (ply === 0) {
      html += '<br><span class="muted">Начальная позиция. График и ходы можно нажимать.</span>';
    }
    if (state.viewPly === null) {
      html += '<br><span class="muted">Нажмите на ход или график, чтобы открыть просмотр.</span>';
    }
    return html;
  }

  function renderEvalChart() {
    const analysis = state.analysis;
    if (!analysis || !analysis.evals.length) {
      els.evalChart.innerHTML = '';
      return;
    }
    const evals = analysis.evals;
    const n = evals.length;
    const points = evals.map((entry, index) => {
      const x = n === 1 ? 50 : (index / (n - 1)) * 100;
      const cp = Math.max(-800, Math.min(800, entry.cp));
      const y = 50 - (cp / 800) * 44;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    });
    const area = `0,100 ${points.join(' ')} 100,100`;
    const currentPly = state.viewPly === null ? state.snaps.length - 1 : state.viewPly;
    const cursorIndex = Math.max(0, Math.min(n - 1, currentPly));
    const cursorX = n === 1 ? 50 : (cursorIndex / (n - 1)) * 100;
    els.evalChart.title = 'Выше — перевес белых, ниже — чёрных. Нажмите, чтобы открыть позицию.';
    els.evalChart.innerHTML = `
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polygon class="eval-area" points="${area}"></polygon>
        <line class="eval-zero" x1="0" y1="50" x2="100" y2="50"></line>
        <polyline class="eval-line" points="${points.join(' ')}"></polyline>
        <line x1="${cursorX.toFixed(2)}" y1="2" x2="${cursorX.toFixed(2)}" y2="98" stroke="rgba(255,255,255,0.35)" stroke-width="0.7"></line>
        <circle class="eval-dot current" cx="${cursorX.toFixed(2)}" cy="${(50 - (Math.max(-800, Math.min(800, evals[cursorIndex].cp)) / 800) * 44).toFixed(2)}" r="2.2"></circle>
      </svg>
    `;
  }

  function onEvalChartClick(event) {
    const analysis = state.analysis;
    if (!analysis || !analysis.evals.length) return;
    const rect = els.evalChart.getBoundingClientRect();
    if (!rect.width) return;
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const ply = Math.round(ratio * (analysis.evals.length - 1));
    if (!state.snaps[ply]) return;
    if (ply === state.snaps.length - 1) exitReview();
    else enterReview(ply);
  }

  /* ---------------------------------------------------------------- настройки */
  function openSettings() {
    state.settingsPaused = state.started && !state.over && state.clocks.running;
    if (state.settingsPaused) stopClock();
    syncSettingsForm();
    els.settingsOverlay.classList.remove('hidden');
    els.settingsClose.focus({ preventScroll: true });
  }

  function closeSettings() {
    els.settingsOverlay.classList.add('hidden');
    saveSettings();
    if (state.settingsPaused && state.started && !state.over) {
      state.clocks.running = true;
      state.clocks.last = performance.now();
      startClockTimer();
      updateClocks();
    }
    state.settingsPaused = false;
  }

  function resetSettings() {
    const form = Object.assign({}, state.form);
    state.settings = Object.assign({}, DEFAULT_SETTINGS);
    state.settings.mode = form.mode;
    state.settings.level = form.level;
    state.settings.time = form.time;
    state.settings.color = form.color;
    buildLevels();
    applySettings(false);
    saveSettings();
    showToast('Настройки сброшены');
  }

  function onSettingInput(event) {
    const target = event.target;
    if (!target || !target.id) return;
    const s = state.settings;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    let rerenderLevels = false;

    switch (target.id) {
      case 'set-board-theme': s.boardTheme = value; break;
      case 'set-piece-style': s.pieceStyle = value; break;
      case 'set-coordinates': s.coordinates = !!value; break;
      case 'set-show-legal': s.showLegal = !!value; break;
      case 'set-show-last': s.showLast = !!value; break;
      case 'set-animations': s.animations = !!value; break;
      case 'set-auto-promote': s.autoPromote = !!value; break;
      case 'set-confirm-resign': s.confirmResign = !!value; break;
      case 'set-eval-bar': s.showEvalBar = !!value; break;
      case 'set-best-move': s.showBestMove = !!value; break;
      case 'set-sound': s.sound = !!value; break;
      case 'set-volume': s.volume = clampNumber(value, 0, 100, s.volume); break;
      case 'set-animation': s.animationMs = clampNumber(value, 0, 500, s.animationMs); break;
      case 'set-piece-scale': s.pieceScale = clampNumber(value, 70, 100, s.pieceScale); break;
      case 'set-analysis-depth': s.analysisDepth = clampNumber(value, 6, 20, s.analysisDepth); break;
      case 'set-analysis-time': s.analysisTime = clampNumber(value, 120, 2000, s.analysisTime); break;
      case 'set-bot-min':
        s.botEloMin = clampNumber(value, 600, 2800, s.botEloMin);
        if (s.botEloMin > s.botEloMax) s.botEloMax = s.botEloMin;
        rerenderLevels = true;
        break;
      case 'set-bot-max':
        s.botEloMax = clampNumber(value, 600, 2800, s.botEloMax);
        if (s.botEloMax < s.botEloMin) s.botEloMin = s.botEloMax;
        rerenderLevels = true;
        break;
      default: return;
    }

    updateSettingOutputs();
    applySettings(false);
    if (rerenderLevels) {
      buildLevels();
      updateFormUI();
    }
    if (target.id === 'set-sound' && s.sound) {
      ensureAudio();
      playSound('toggle');
    }
    saveSettings();
  }

  /* ---------------------------------------------------------------- PGN, FEN и архив */
  function resultPgn() {
    if (!state.result) return '*';
    if (state.result.winner === 1) return '1-0';
    if (state.result.winner === -1) return '0-1';
    if (state.result.winner === 0) return '1/2-1/2';
    return '*';
  }

  function buildPgn() {
    if (!state.snaps || state.snaps.length === 0) return '';
    const result = resultPgn();
    const date = new Date();
    const dateText = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
    const level = resolvedLevel(LEVELS[state.level] || LEVELS[0]);
    const white = state.mode === 'bot' && state.humanColor === -1 ? level.name : (state.mode === 'bot' ? 'Вы' : 'Белые');
    const black = state.mode === 'bot' && state.humanColor === 1 ? level.name : (state.mode === 'bot' ? 'Вы' : 'Чёрные');
    const tags = [
      '[Event "CHESS ARENA"]',
      '[Site "local"]',
      `[Date "${dateText}"]`,
      '[Round "-"]',
      `[White "${white}"]`,
      `[Black "${black}"]`,
      `[Result "${result}"]`
    ];
    if (state.mode === 'bot') tags.push(`[BlackElo "${state.humanColor === -1 ? '' : level.rating}"]`.replace('""', '"?"'));
    if (state.mode === 'bot') tags.push(`[WhiteElo "${state.humanColor === 1 ? '' : level.rating}"]`.replace('""', '"?"'));
    const startFen = state.snaps[0].fen;
    if (startFen !== E.START_FEN) {
      tags.push('[SetUp "1"]');
      tags.push(`[FEN "${startFen}"]`);
    }

    const parts = [];
    for (let i = 1; i < state.snaps.length; i++) {
      const snap = state.snaps[i];
      if (i % 2 === 1) parts.push(`${Math.ceil(i / 2)}. ${snap.san}`);
      else parts.push(snap.san);
    }
    if (result !== '*') parts.push(result);
    return tags.join('\n') + '\n\n' + parts.join(' ') + '\n';
  }

  function loadArchive() {
    try {
      const raw = localStorage.getItem(ARCHIVE_KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data.filter((item) => item && typeof item.pgn === 'string') : [];
    } catch (err) {
      return [];
    }
  }

  function saveToArchive() {
    if (!state.started || state.snaps.length < 2) return;
    const list = loadArchive();
    const level = resolvedLevel(LEVELS[state.level] || LEVELS[0]);
    list.unshift({
      id: 'g' + Date.now(),
      date: new Date().toISOString(),
      mode: state.mode,
      level: state.mode === 'bot' ? level.name + ' · ' + level.rating : 'Два игрока',
      result: resultPgn(),
      moves: state.snaps.length - 1,
      pgn: buildPgn()
    });
    try {
      localStorage.setItem(ARCHIVE_KEY, JSON.stringify(list.slice(0, 40)));
    } catch (err) { /* приватный режим */ }
  }

  function openArchive() {
    renderArchive();
    els.archiveOverlay.classList.remove('hidden');
    els.archiveClose.focus({ preventScroll: true });
  }

  function closeArchive() {
    els.archiveOverlay.classList.add('hidden');
  }

  function archiveResultText(result) {
    if (result === '1-0') return '1 – 0';
    if (result === '0-1') return '0 – 1';
    if (result === '1/2-1/2') return '½ – ½';
    return '*';
  }

  function renderArchive() {
    const list = loadArchive();
    if (!list.length) {
      els.archiveList.innerHTML = '<div class="archive-empty">Пока нет сохранённых партий.<br>Сыграйте партию — она появится здесь автоматически.</div>';
      return;
    }
    els.archiveList.innerHTML = list.map((item) => {
      const date = item.date ? new Date(item.date) : null;
      const dateText = date && !Number.isNaN(date.getTime())
        ? date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }) + ' · ' +
          date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
        : 'Партия';
      const modeText = item.mode === 'bot' ? 'с компьютером' : 'два игрока';
      return `
        <article class="archive-item">
          <div class="archive-main">
            <span class="archive-date">${dateText} · ${modeText}</span>
            <strong>${item.level || 'Партия'}</strong>
            <span class="archive-meta">${item.moves || 0} ход. · ${archiveResultText(item.result)}</span>
          </div>
          <div class="archive-actions">
            <button class="btn btn-soft btn-sm" type="button" data-archive-load="${item.id}">Открыть</button>
            <button class="archive-del" type="button" data-archive-delete="${item.id}" aria-label="Удалить партию">×</button>
          </div>
        </article>
      `;
    }).join('');
  }

  function onArchiveAction(event) {
    const load = event.target.closest('[data-archive-load]');
    if (load) {
      const item = loadArchive().find((entry) => entry.id === load.dataset.archiveLoad);
      if (item) {
        closeArchive();
        loadGameText(item.pgn, { source: 'archive' });
      }
      return;
    }
    const del = event.target.closest('[data-archive-delete]');
    if (del) {
      const list = loadArchive().filter((entry) => entry.id !== del.dataset.archiveDelete);
      try { localStorage.setItem(ARCHIVE_KEY, JSON.stringify(list)); } catch (err) { /* приватный режим */ }
      renderArchive();
      showToast('Партия удалена из архива');
    }
  }

  function openPgnDialog() {
    els.pgnText.value = buildPgn();
    els.pgnFen.value = state.game ? state.game.fen() : E.START_FEN;
    els.pgnOverlay.classList.remove('hidden');
    els.pgnText.focus({ preventScroll: true });
  }

  function closePgnDialog() {
    els.pgnOverlay.classList.add('hidden');
  }

  function copyText(text) {
    if (!text) return Promise.reject(new Error('Нет текста'));
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
      try {
        const area = document.createElement('textarea');
        area.value = text;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        const ok = document.execCommand('copy');
        area.remove();
        if (ok) resolve();
        else reject(new Error('Копирование недоступно'));
      } catch (err) {
        reject(err);
      }
    });
  }

  function copyPgn(download) {
    const text = els.pgnText.value || buildPgn();
    if (download) {
      downloadPgn();
      return;
    }
    copyText(text).then(() => showToast('PGN скопирован')).catch(() => showToast('Не удалось скопировать PGN'));
  }

  function downloadPgn() {
    const text = els.pgnText.value || buildPgn();
    if (!text) return;
    try {
      const blob = new Blob([text], { type: 'application/x-chess-pgn;charset=utf-8' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'chess-arena-' + new Date().toISOString().slice(0, 10) + '.pgn';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 2000);
      showToast('PGN сохранён');
    } catch (err) {
      showToast('Не удалось сохранить PGN');
    }
  }

  function copyFen() {
    const fen = els.pgnFen.value || (state.game ? state.game.fen() : '');
    copyText(fen).then(() => showToast('FEN скопирован')).catch(() => showToast('Не удалось скопировать FEN'));
  }

  function normalizeSanToken(token) {
    return String(token)
      .replace(/^[.]+/, '')
      .replace(/[!?]+$/, '')
      .replace(/[+#]+$/, '')
      .replace(/e\.p\.?$/i, '')
      .replace(/0-0-0/g, 'O-O-O')
      .replace(/0-0/g, 'O-O');
  }

  function findSanMove(game, token) {
    const clean = normalizeSanToken(token);
    if (!clean) return null;
    const legal = game.legalMoves();
    for (const move of legal) {
      let san = '';
      try { san = game.san(move); } catch (err) { continue; }
      if (normalizeSanToken(san) === clean) return move;
    }
    if (/^[a-h][1-8][a-h][1-8][qrbn]?$/i.test(clean)) {
      return moveFromUci(game, clean.toLowerCase());
    }
    return null;
  }

  function loadGameText(rawText, options) {
    const text = String(rawText || '').trim();
    if (!text) {
      showToast('Вставьте PGN или FEN');
      return false;
    }

    let startFen = E.START_FEN;
    let fenOnly = null;
    const fenHeader = /\[FEN\s+"([^"]+)"\]/i.exec(text);
    if (fenHeader) startFen = fenHeader[1].trim();
    const fenCandidate = text.split(/\r?\n/).map((line) => line.trim()).find((line) => (
      /^[rnbqkpRNBQKP1-8/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/.test(line)
    ));
    if (fenCandidate) fenOnly = fenCandidate;
    if (!fenHeader && fenOnly) startFen = fenOnly;

    const resultHeader = /\[Result\s+"([^"]+)"\]/i.exec(text);
    let body = text
      .replace(/\[[^\]]*\]/g, ' ')
      .replace(/\{[^}]*\}/g, ' ')
      .replace(/;[^\n]*/g, ' ')
      .replace(/\$\d+/g, ' ')
      .replace(/\d+\.(?:\.\.)?/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    let game;
    try {
      game = new E.Game(startFen);
    } catch (err) {
      showToast('Некорректная начальная позиция');
      return false;
    }

    const tokens = body.split(/\s+/).filter((token) => (
      token && !['1-0', '0-1', '1/2-1/2', '*'].includes(token)
    ));

    const snaps = [{ fen: game.fen(), move: null, san: null, color: 0 }];
    let lastMove = null;
    let parsed = 0;
    for (const token of tokens) {
      const move = findSanMove(game, token);
      if (move === null) {
        if (parsed === 0 && !fenOnly) {
          showToast('Не удалось разобрать PGN: ' + token);
          return false;
        }
        break;
      }
      const from = E.moveFrom(move);
      const to = E.moveTo(move);
      const mover = game.side;
      let san = '';
      try { san = game.san(move); } catch (err) { san = token; }
      game.makeMove(move);
      snaps.push({ fen: game.fen(), move: { from, to }, san, color: mover });
      lastMove = { from, to };
      parsed++;
      if (game.status()) break;
    }

    if (parsed === 0 && !fenOnly && !fenHeader) {
      showToast('В тексте не найдено ходов PGN');
      return false;
    }

    cancelBot();
    stopClock();
    hideResult();
    resetAnalysis();
    hidePromotion();
    resetResign();
    state.game = game;
    state.started = true;
    state.over = false;
    state.result = null;
    state.mode = 'local';
    state.humanColor = 1;
    state.botColor = -1;
    state.orientation = 1;
    state.colorChoice = 'w';
    state.timeKey = 'none';
    state.snaps = snaps;
    state.lastMove = lastMove;
    state.viewPly = null;
    state.reviewGame = null;
    state.selected = null;
    state.legalForSelected = [];
    state.promotion = null;
    state.pointer = null;
    state.botThinking = false;
    state.pendingBot = null;
    state.clocks.enabled = false;
    state.clocks.running = false;
    stopClock();

    const status = game.status();
    if (status) {
      state.over = true;
      state.result = { winner: status.winner, reason: status.reason };
    } else if (resultHeader) {
      const result = resultHeader[1];
      if (result === '1-0') state.result = { winner: 1, reason: 'import' };
      else if (result === '0-1') state.result = { winner: -1, reason: 'import' };
      else if (result === '1/2-1/2') state.result = { winner: 0, reason: 'import' };
    }

    closePgnDialog();
    closeArchive();
    els.setupOverlay.classList.add('hidden');
    renderAll();
    updateStatus();
    showToast((options && options.source === 'archive' ? 'Партия открыта' : 'Позиция загружена') +
      ' · ' + (snaps.length - 1) + ' ход.');
    return true;
  }

  function loadPgnFromDialog() {
    loadGameText(els.pgnText.value);
  }

  function loadFenFromDialog() {
    const fen = els.pgnFen.value.trim();
    if (!loadGameText(fen)) return;
  }

  /* ---------------------------------------------------------------- задачи */
  function puzzleLevel(puzzle) {
    const levels = (window.ChessPuzzles && window.ChessPuzzles.levels) || {};
    return levels[puzzle.level] || { name: 'Тактика' };
  }

  function openPuzzleList() {
    if (!window.ChessPuzzles) {
      showToast('Задачи не загрузились');
      return;
    }
    renderPuzzleList();
    els.puzzleOverlay.classList.remove('hidden');
    els.puzzleClose.focus({ preventScroll: true });
  }

  function closePuzzleList() {
    els.puzzleOverlay.classList.add('hidden');
  }

  function startGeneratedPuzzle(level) {
    if (!window.ChessPuzzleGen) {
      showToast('Генератор задач не загрузился');
      return;
    }
    const item = window.ChessPuzzleGen.generate(level);
    if (!item) {
      showToast('Не удалось создать задачу. Попробуйте ещё раз.');
      return;
    }
    startPuzzle(item);
  }

  function renderPuzzleList() {
    if (!window.ChessPuzzles) return;
    const list = window.ChessPuzzles.list;
    const filtered = state.puzzleFilter === 'all'
      ? list
      : list.filter((puzzle) => String(puzzle.level) === state.puzzleFilter);

    $$('#puzzle-filters [data-filter]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.filter === state.puzzleFilter);
    });

    els.puzzleGrid.innerHTML = filtered.map((puzzle) => {
      const solved = state.solvedPuzzles.includes(puzzle.id);
      const stars = '★'.repeat(puzzle.level) + '☆'.repeat(Math.max(0, 4 - puzzle.level));
      return `
        <button class="puzzle-item${solved ? ' solved' : ''}" type="button" data-puzzle="${puzzle.id}">
          ${solved ? '<span class="puzzle-solved-mark" aria-label="Решено">✓</span>' : ''}
          <span class="puzzle-item-theme">${puzzle.theme}</span>
          <span class="puzzle-item-title">${puzzle.title}</span>
          <span class="puzzle-item-meta">${puzzleLevel(puzzle).name} · ${puzzle.rating} · <span class="puzzle-item-stars">${stars}</span></span>
        </button>
      `;
    }).join('');

    PUZZLE_LEVELS.forEach((level) => {
      const stats = state.puzzleStats[level];
      const streak = stats.streak > 1 ? ` · серия ${stats.streak}` : '';
      if (els.endlessCounts[level]) {
        els.endlessCounts[level].textContent = `Решено: ${stats.solved}${streak}`;
      }
    });

    const solvedCount = list.filter((puzzle) => state.solvedPuzzles.includes(puzzle.id)).length;
    els.puzzleCount.textContent = `Классика: ${solvedCount} из ${list.length}. Ошибки не отнимают попытки — пробуйте снова.`;
  }

  function startPuzzle(puzzle) {
    if (!window.ChessPuzzles) return;
    let saved;
    if (state.puzzle && state.puzzle.active) {
      saved = state.puzzle.saved;
    } else {
      if (state.analysis && state.analysis.running) resetAnalysis();
      saved = captureSession();
    }

    clearTimeout(state.puzzleTimer);
    state.puzzleTimer = null;
    cancelBot();
    stopClock();
    hideResult();
    hidePuzzleSuccess();
    hidePromotion();
    resetResign();
    closePuzzleList();
    els.setupOverlay.classList.add('hidden');

    state.puzzle = {
      active: true,
      item: puzzle,
      saved,
      index: 0,
      mistakes: 0,
      hintUsed: false,
      solved: false,
      waiting: false,
      feedback: '',
      feedbackKind: '',
      solutionShown: false
    };
    setupPuzzleBoard();
    showToast('Найдите лучший ход');
  }

  function setupPuzzleBoard() {
    const puzzle = state.puzzle;
    if (!puzzle) return;
    const game = new E.Game(puzzle.item.fen);
    state.game = game;
    state.started = true;
    state.over = false;
    state.result = null;
    state.mode = 'puzzle';
    state.humanColor = game.side;
    state.botColor = -game.side;
    state.orientation = game.side;
    state.colorChoice = game.side === 1 ? 'w' : 'b';
    state.snaps = [{ fen: game.fen(), move: null, san: null, color: 0 }];
    state.lastMove = null;
    state.viewPly = null;
    state.reviewGame = null;
    state.selected = null;
    state.legalForSelected = [];
    state.promotion = null;
    state.pointer = null;
    state.botThinking = false;
    state.pendingBot = null;
    state.analysis = null;
    state.clocks.enabled = false;
    state.clocks.running = false;
    stopClock();

    puzzle.lines = puzzle.item.lines && puzzle.item.lines.length
      ? puzzle.item.lines.map((line) => line.slice())
      : [puzzle.item.moves.slice()];
    puzzle.line = puzzle.lines[0];
    puzzle.index = 0;
    puzzle.waiting = false;
    puzzle.solved = false;
    puzzle.feedback = '';
    puzzle.feedbackKind = '';

    els.promo.classList.add('hidden');
    renderAll();
    updateStatus();
  }

  function updatePuzzlePanel() {
    const puzzle = state.puzzle;
    const active = !!(puzzle && puzzle.active);
    els.puzzlePanel.classList.toggle('hidden', !active);
    if (!active) return;

    const item = puzzle.item;
    const playerMoves = Math.ceil(puzzle.line.length / 2);
    const doneMoves = Math.min(playerMoves, Math.ceil(puzzle.index / 2));
    els.puzzleTheme.textContent = item.theme;
    els.puzzleDifficulty.textContent = `${puzzleLevel(item).name} · ${item.rating}`;
    els.puzzleProgress.textContent = puzzle.solved ? 'Решено' : `${doneMoves} / ${playerMoves}`;

    if (puzzle.solved) {
      els.puzzleInstruction.textContent = 'Задача решена. Можно перейти к следующей.';
    } else if (puzzle.waiting) {
      els.puzzleInstruction.textContent = 'Соперник отвечает…';
    } else {
      const color = item.fen.split(/\s+/)[1] === 'b' ? 'чёрных' : 'белых';
      els.puzzleInstruction.textContent = `Найдите лучший ход за ${color}.`;
    }

    const feedback = puzzle.feedback || (puzzle.hintUsed && !puzzle.solved ? `Подсказка: ${item.hint}` : '');
    els.puzzleFeedback.textContent = feedback;
    els.puzzleFeedback.className = 'puzzle-feedback' + (puzzle.feedbackKind ? ` ${puzzle.feedbackKind}` : '');
    els.puzzleHint.disabled = puzzle.solved;
    els.puzzleSolution.disabled = puzzle.solved;
  }

  function attemptPuzzleMove(from, to) {
    if (!canHumanMove()) return false;
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active || puzzle.solved || puzzle.waiting) return false;
    const legal = state.game.legalMoves().filter(
      (move) => E.moveFrom(move) === from && E.moveTo(move) === to
    );
    if (!legal.length) return false;

    const nextUci = legal.map((move) => state.game.uci(move));
    const chosenIndex = nextUci.findIndex((uci) => (
      puzzle.lines.some((line) => line[puzzle.index] === uci)
    ));
    if (chosenIndex < 0) {
      rejectPuzzleMove();
      deselect();
      return true;
    }
    const chosen = legal[chosenIndex];
    const chosenUci = nextUci[chosenIndex];
    puzzle.lines = puzzle.lines.filter((line) => line[puzzle.index] === chosenUci);
    puzzle.line = puzzle.lines[0];
    puzzle.index++;
    commitMove(chosen);
    return true;
  }

  function rejectPuzzleMove() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active) return;
    puzzle.mistakes++;
    puzzle.feedbackKind = 'bad';
    if (puzzle.mistakes >= 2) {
      puzzle.hintUsed = true;
      puzzle.feedback = `Пока не то. Подсказка: ${puzzle.item.hint}`;
    } else {
      puzzle.feedback = 'Не совсем. Попробуйте другой ход.';
    }
    playSound('wrong');
    els.board.classList.remove('shake');
    void els.board.offsetWidth;
    els.board.classList.add('shake');
    setTimeout(() => els.board.classList.remove('shake'), 340);
    updatePuzzlePanel();
  }

  function afterPuzzleMove() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active) return;

    if (puzzle.index >= puzzle.line.length) {
      puzzle.solved = true;
      puzzle.waiting = false;
      puzzle.feedback = 'Тактический приём сработал.';
      puzzle.feedbackKind = 'ok';
      recordPuzzleSolved(puzzle.item);
      renderPuzzleList();
      updateStatus();
      updatePuzzlePanel();
      playSound('end');
      clearTimeout(state.puzzleTimer);
      state.puzzleTimer = setTimeout(() => {
        if (state.puzzle && state.puzzle.active && state.puzzle.solved) showPuzzleSuccess();
      }, 560);
      return;
    }

    if (puzzle.index % 2 === 1) {
      puzzle.waiting = true;
      puzzle.feedback = 'Верно! Соперник отвечает…';
      puzzle.feedbackKind = 'ok';
      updateStatus();
      updatePuzzlePanel();
      renderControls();
      clearTimeout(state.puzzleTimer);
      state.puzzleTimer = setTimeout(playPuzzleReply, 620);
    } else {
      puzzle.waiting = false;
      puzzle.feedback = 'Хорошо! Продолжайте.';
      puzzle.feedbackKind = 'ok';
      updateStatus();
      updatePuzzlePanel();
      renderControls();
    }
  }

  function recordPuzzleSolved(item) {
    if (item.generated) {
      const stats = state.puzzleStats[item.level] || state.puzzleStats[1];
      stats.solved++;
      stats.streak++;
      stats.best = Math.max(stats.best, stats.streak);
      savePuzzleStats();
      return;
    }
    if (!state.solvedPuzzles.includes(item.id)) {
      state.solvedPuzzles.push(item.id);
      saveSolvedPuzzles();
    }
  }

  function playPuzzleReply() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active || puzzle.solved || !puzzle.waiting) return;
    const expected = puzzle.line[puzzle.index];
    const move = state.game.legalMoves().find((m) => state.game.uci(m) === expected);
    puzzle.waiting = false;
    if (!move) {
      puzzle.feedback = 'Не удалось воспроизвести ответ соперника.';
      puzzle.feedbackKind = 'bad';
      updateStatus();
      updatePuzzlePanel();
      return;
    }
    puzzle.index++;
    commitMove(move);
  }

  function showPuzzleHint() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active || puzzle.solved) return;
    puzzle.hintUsed = true;
    puzzle.feedback = `Подсказка: ${puzzle.item.hint}`;
    puzzle.feedbackKind = '';
    updatePuzzlePanel();
  }

  function puzzleSolutionText(item, line) {
    const game = new E.Game(item.fen);
    const parts = [];
    (line || item.moves).forEach((uci, index) => {
      const move = game.legalMoves().find((m) => game.uci(m) === uci);
      if (!move) return;
      const san = game.san(move);
      if (index % 2 === 0) parts.push(`${index / 2 + 1}. ${san}`);
      else parts.push(san);
      game.makeMove(move);
    });
    return parts.join(' ');
  }

  function showPuzzleSolution() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active || puzzle.solved) return;
    puzzle.solutionShown = true;
    puzzle.feedback = `Решение: ${puzzleSolutionText(puzzle.item, puzzle.line)}`;
    puzzle.feedbackKind = '';
    updatePuzzlePanel();
  }

  function retryPuzzle() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active) return;
    clearTimeout(state.puzzleTimer);
    setupPuzzleBoard();
    puzzle.mistakes = 0;
    puzzle.hintUsed = false;
    updatePuzzlePanel();
    updateStatus();
    showToast('Задача начата заново');
  }

  function showPuzzleSuccess() {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active) return;
    els.puzzleSuccessSub.textContent = `${puzzle.item.title}. ${puzzle.item.idea}`;
    const mistakes = puzzle.mistakes;
    const mistakeText = mistakes
      ? `${mistakes} ${plural(mistakes, ['ошибка', 'ошибки', 'ошибок'])}`
      : 'Без ошибок';
    els.puzzleSuccessScore.textContent = `${puzzleLevel(puzzle.item).name} · ${mistakeText}`;
    els.puzzleSuccess.classList.remove('hidden');
    els.puzzleNext.focus({ preventScroll: true });
  }

  function hidePuzzleSuccess() {
    els.puzzleSuccess.classList.add('hidden');
  }

  function nextPuzzle() {
    const puzzle = state.puzzle;
    if (!puzzle) return;
    const level = puzzle.item.level;
    hidePuzzleSuccess();
    startGeneratedPuzzle(level);
  }

  function leavePuzzle(openList) {
    const puzzle = state.puzzle;
    if (!puzzle || !puzzle.active) {
      if (openList) openPuzzleList();
      return;
    }
    clearTimeout(state.puzzleTimer);
    state.puzzleTimer = null;
    const saved = puzzle.saved;
    state.puzzle = null;
    hidePuzzleSuccess();
    els.puzzleOverlay.classList.add('hidden');
    els.puzzlePanel.classList.add('hidden');
    restoreSession(saved);
    if (openList) openPuzzleList();
  }

  /* ---------------------------------------------------------------- сохранение партии */
  function captureSession() {
    return {
      game: state.game,
      snaps: state.snaps,
      started: state.started,
      over: state.over,
      result: state.result,
      mode: state.mode,
      level: state.level,
      humanColor: state.humanColor,
      botColor: state.botColor,
      orientation: state.orientation,
      colorChoice: state.colorChoice,
      timeKey: state.timeKey,
      lastMove: state.lastMove,
      viewPly: state.viewPly,
      reviewGame: state.reviewGame,
      analysis: state.analysis,
      analysisToken: state.analysisToken,
      clocks: {
        enabled: state.clocks.enabled,
        initial: state.clocks.initial,
        inc: state.clocks.inc,
        white: state.clocks.white,
        black: state.clocks.black,
        running: state.clocks.running
      },
      setupOpen: !els.setupOverlay.classList.contains('hidden'),
      resultOpen: !els.resultOverlay.classList.contains('hidden')
    };
  }

  function restoreSession(saved) {
    if (!saved) return;
    stopClock();
    cancelBot();
    state.game = saved.game;
    state.snaps = saved.snaps;
    state.started = saved.started;
    state.over = saved.over;
    state.result = saved.result;
    state.mode = saved.mode;
    state.level = saved.level;
    state.humanColor = saved.humanColor;
    state.botColor = saved.botColor;
    state.orientation = saved.orientation;
    state.colorChoice = saved.colorChoice;
    state.timeKey = saved.timeKey;
    state.lastMove = saved.lastMove;
    state.viewPly = saved.viewPly;
    state.reviewGame = saved.reviewGame;
    state.analysis = saved.analysis;
    state.analysisToken = saved.analysisToken;
    state.clocks.enabled = saved.clocks.enabled;
    state.clocks.initial = saved.clocks.initial;
    state.clocks.inc = saved.clocks.inc;
    state.clocks.white = saved.clocks.white;
    state.clocks.black = saved.clocks.black;
    state.clocks.running = false;
    state.clocks.last = 0;
    state.selected = null;
    state.legalForSelected = [];
    state.promotion = null;
    state.pointer = null;
    state.botThinking = false;
    state.pendingBot = null;
    els.promo.classList.add('hidden');

    renderAll();
    els.setupOverlay.classList.toggle('hidden', !saved.setupOpen);
    els.resultOverlay.classList.toggle('hidden', !saved.resultOpen);

    if (saved.clocks.running && state.started && !state.over) {
      state.clocks.running = true;
      state.clocks.last = performance.now();
      startClockTimer();
      updateClocks();
    }
    if (state.mode === 'bot' && state.started && !state.over && state.game.side === state.botColor) {
      scheduleBot(300);
    }
  }

  function plural(n, forms) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return forms[0];
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1];
    return forms[2];
  }

  /* ---------------------------------------------------------------- мелочи */
  function showToast(text) {
    els.toast.textContent = text;
    els.toast.classList.add('show');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => {
      els.toast.classList.remove('show');
    }, 2200);
  }

  init();



})();
