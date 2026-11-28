/* CHESS ARENA — клиент Stockfish 16 (single-threaded WASM, UCI).
   Загружает движок в отдельном Worker и общается с ним по протоколу UCI.
   Если файлы Stockfish недоступны, приложение использует встроенный движок. */
(function (global) {
  'use strict';

  const DEFAULT_URL = 'js/stockfish/stockfish-nnue-16-single.js#stockfish-nnue-16-single.wasm';
  const INIT_TIMEOUT = 15000;
  const MATE_SCORE = 100000;

  function parseInfo(line, previous) {
    const info = Object.assign({
      depth: 0,
      cp: 0,
      mate: null,
      pv: [],
      nodes: 0,
      nps: 0,
      multipv: 1
    }, previous || {});

    let m = /(?:^|\s)depth\s+(\d+)/.exec(line);
    if (m) info.depth = Number(m[1]);
    m = /(?:^|\s)nodes\s+(\d+)/.exec(line);
    if (m) info.nodes = Number(m[1]);
    m = /(?:^|\s)nps\s+(\d+)/.exec(line);
    if (m) info.nps = Number(m[1]);
    m = /(?:^|\s)multipv\s+(\d+)/.exec(line);
    if (m) info.multipv = Number(m[1]);

    m = /(?:^|\s)score\s+(cp|mate)\s+(-?\d+)/.exec(line);
    if (m) {
      const value = Number(m[2]);
      if (m[1] === 'mate') {
        info.mate = value;
        info.cp = value >= 0
          ? MATE_SCORE - Math.abs(value) * 100
          : -MATE_SCORE - value * 100;
      } else {
        info.mate = null;
        info.cp = value;
      }
    }

    m = /(?:^|\s)pv\s+(.+)$/.exec(line);
    if (m) info.pv = m[1].trim().split(/\s+/);

    return info;
  }

  class StockfishClient {
    constructor(url) {
      this.url = url || DEFAULT_URL;
      this.worker = null;
      this.ready = false;
      this.failed = false;
      this.initPromise = null;
      this.queue = [];
      this.current = null;
      this.lastError = null;
      this.everReady = false;
    }

    init() {
      if (this.ready) return Promise.resolve(true);
      if (this.initPromise) return this.initPromise;

      this.initPromise = new Promise((resolve, reject) => {
        let worker;
        try {
          worker = new Worker(this.url);
        } catch (error) {
          this.failed = true;
          this.lastError = error;
          reject(error);
          return;
        }

        this.worker = worker;
        let settled = false;
        const timer = setTimeout(() => fail(new Error('Stockfish: превышено время запуска')), INIT_TIMEOUT);

        const fail = (error) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          this.failed = true;
          this.lastError = error;
          this.ready = false;
          try { worker.terminate(); } catch (err) { /* уже остановлен */ }
          this.worker = null;
          reject(error);
        };

        worker.onerror = (event) => {
          fail(new Error('Stockfish: ' + ((event && event.message) || 'ошибка Worker')));
        };

        worker.onmessage = (event) => {
          const line = String(event.data == null ? '' : event.data).trim();
          if (!line) return;

          if (line === 'uciok') {
            if (!settled) {
              settled = true;
              clearTimeout(timer);
              this.ready = true;
              this.everReady = true;
              this.post('setoption name Threads value 1');
              this.post('setoption name Hash value 16');
              this.post('setoption name Move Overhead value 30');
              this.post('setoption name UCI_Chess960 value false');
              this.post('setoption name Ponder value false');
              resolve(true);
            }
            return;
          }

          if (line.startsWith('info ') && this.current) {
            this.current.info = parseInfo(line, this.current.info);
            if (this.current.opts && typeof this.current.opts.onInfo === 'function') {
              try { this.current.opts.onInfo(this.current.info); } catch (err) { /* не критично */ }
            }
            return;
          }

          if (line.startsWith('bestmove')) {
            this.handleBestMove(line);
          }
        };

        try {
          worker.postMessage('uci');
        } catch (error) {
          fail(error);
        }
      });

      return this.initPromise;
    }

    post(command) {
      if (!this.worker) return false;
      try {
        this.worker.postMessage(command);
        return true;
      } catch (error) {
        this.lastError = error;
        return false;
      }
    }

    handleBestMove(line) {
      const match = /^bestmove\s+(\S+)/.exec(line);
      const task = this.current;
      this.current = null;
      if (task) {
        const info = task.info || {};
        const move = match && match[1] !== '(none)' ? match[1] : null;
        task.resolve({
          move,
          uci: move,
          score: info.cp || 0,
          cp: info.cp || 0,
          mate: info.mate,
          depth: info.depth || 0,
          nodes: info.nodes || 0,
          pv: info.pv || []
        });
      }
      this.pump();
    }

    /* Ставит поиск в очередь. Возвращает Promise с результатом. */
    search(options) {
      const opts = Object.assign({}, options || {});
      return new Promise((resolve, reject) => {
        this.queue.push({ opts, resolve, reject, info: null });
        this.pump();
      });
    }

    pump() {
      if (this.current || !this.queue.length) return;
      const task = this.queue.shift();
      if (!this.worker || this.failed) {
        this.init().then(() => this.startTask(task)).catch((error) => {
          task.reject(error);
          this.pump();
        });
        return;
      }
      this.startTask(task);
    }

    startTask(task) {
      if (this.failed || !this.worker) {
        task.reject(this.lastError || new Error('Stockfish недоступен'));
        this.pump();
        return;
      }
      const opts = task.opts;
      this.current = task;
      task.info = { depth: 0, cp: 0, mate: null, pv: [], nodes: 0, nps: 0, multipv: 1 };

      if (opts.elo) {
        this.post('setoption name Skill Level value 20');
        this.post('setoption name UCI_LimitStrength value true');
        this.post('setoption name UCI_Elo value ' + Math.max(1320, Math.min(3190, Math.round(opts.elo))));
      } else if (Number.isFinite(opts.skill)) {
        this.post('setoption name UCI_LimitStrength value false');
        this.post('setoption name Skill Level value ' + Math.max(0, Math.min(20, Math.round(opts.skill))));
      } else {
        this.post('setoption name UCI_LimitStrength value false');
        this.post('setoption name Skill Level value 20');
      }
      this.post('setoption name MultiPV value ' + Math.max(1, Math.min(5, opts.multiPV || 1)));
      this.post('position fen ' + opts.fen);

      let go = 'go';
      if (opts.depth) go += ' depth ' + Math.max(1, Math.min(30, Math.round(opts.depth)));
      if (opts.movetime) go += ' movetime ' + Math.max(30, Math.min(30000, Math.round(opts.movetime)));
      if (go === 'go') go += ' movetime 500';
      this.post(go);

      const limit = Math.max(3000, (opts.movetime || 1000) + 20000);
      task.guard = setTimeout(() => {
        if (this.current === task) this.post('stop');
      }, limit);
    }

    /* Останавливает текущий поиск. Результат всё равно придёт и будет проигнорирован вызывающим. */
    stop() {
      if (!this.current) return;
      this.post('stop');
    }

    /* Сбрасывает очередь и текущую задачу при старте новой партии. */
    clearQueue(reason) {
      const error = reason || new Error('Поиск отменён');
      while (this.queue.length) {
        const task = this.queue.shift();
        try { task.reject(error); } catch (err) { /* не критично */ }
      }
    }

    newGame() {
      if (!this.ready || this.current) return;
      this.post('ucinewgame');
      this.post('isready');
    }

    destroy() {
      this.clearQueue();
      if (this.current) {
        const task = this.current;
        this.current = null;
        try { task.reject(new Error('Stockfish остановлен')); } catch (err) { /* не критично */ }
      }
      if (this.worker) {
        try { this.post('quit'); } catch (err) { /* не критично */ }
        try { this.worker.terminate(); } catch (err) { /* не критично */ }
        this.worker = null;
      }
      this.ready = false;
    }
  }

  StockfishClient.DEFAULT_URL = DEFAULT_URL;
  StockfishClient.MATE_SCORE = MATE_SCORE;
  global.StockfishClient = StockfishClient;
})(typeof self !== 'undefined' ? self : globalThis);
