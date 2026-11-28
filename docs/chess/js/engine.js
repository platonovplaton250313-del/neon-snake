/* CHESS ARENA — шахматные правила и поиск ходов.
   Работает и в окне, и в Web Worker. Без внешних зависимостей. */
(function (global) {
  'use strict';

  const WHITE = 1;
  const BLACK = -1;

  const PAWN = 1;
  const KNIGHT = 2;
  const BISHOP = 3;
  const ROOK = 4;
  const QUEEN = 5;
  const KING = 6;

  const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const FILES = 'abcdefgh';
  const PROMO_PIECES = [QUEEN, ROOK, BISHOP, KNIGHT];

  const CASTLE_WK = 1;
  const CASTLE_WQ = 2;
  const CASTLE_BK = 4;
  const CASTLE_BQ = 8;

  const KNIGHT_OFFSETS = [33, 31, 18, 14, -14, -18, -31, -33];
  const KING_OFFSETS = [16, -16, 1, -1, 17, 15, -15, -17];
  const BISHOP_DIRS = [17, 15, -15, -17];
  const ROOK_DIRS = [16, -16, 1, -1];
  const QUEEN_DIRS = BISHOP_DIRS.concat(ROOK_DIRS);

  const VALUES = { 1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 0 };
  const MATE = 100000;
  const INF = 1000000;
  const TIMEOUT = { timeout: true };

  /* Таблицы позиционной оценки: взгляд белых, первая строка — 8-я горизонталь. */
  const PST = {
    1: [
       0,  0,  0,  0,  0,  0,  0,  0,
      50, 50, 50, 50, 50, 50, 50, 50,
      10, 10, 20, 30, 30, 20, 10, 10,
       5,  5, 10, 25, 25, 10,  5,  5,
       0,  0,  0, 20, 20,  0,  0,  0,
       5, -5,-10,  0,  0,-10, -5,  5,
       5, 10, 10,-20,-20, 10, 10,  5,
       0,  0,  0,  0,  0,  0,  0,  0
    ],
    2: [
     -50,-40,-30,-30,-30,-30,-40,-50,
     -40,-20,  0,  0,  0,  0,-20,-40,
     -30,  0, 10, 15, 15, 10,  0,-30,
     -30,  5, 15, 20, 20, 15,  5,-30,
     -30,  0, 15, 20, 20, 15,  0,-30,
     -30,  5, 10, 15, 15, 10,  5,-30,
     -40,-20,  0,  5,  5,  0,-20,-40,
     -50,-40,-30,-30,-30,-30,-40,-50
    ],
    3: [
     -20,-10,-10,-10,-10,-10,-10,-20,
     -10,  0,  0,  0,  0,  0,  0,-10,
     -10,  0,  5, 10, 10,  5,  0,-10,
     -10,  5,  5, 10, 10,  5,  5,-10,
     -10,  0, 10, 10, 10, 10,  0,-10,
     -10, 10, 10, 10, 10, 10, 10,-10,
     -10,  5,  0,  0,  0,  0,  5,-10,
     -20,-10,-10,-10,-10,-10,-10,-20
    ],
    4: [
       0,  0,  0,  0,  0,  0,  0,  0,
       5, 10, 10, 10, 10, 10, 10,  5,
      -5,  0,  0,  0,  0,  0,  0, -5,
      -5,  0,  0,  0,  0,  0,  0, -5,
      -5,  0,  0,  0,  0,  0,  0, -5,
      -5,  0,  0,  0,  0,  0,  0, -5,
      -5,  0,  0,  0,  0,  0,  0, -5,
       0,  0,  0,  5,  5,  0,  0,  0
    ],
    5: [
     -20,-10,-10, -5, -5,-10,-10,-20,
     -10,  0,  0,  0,  0,  0,  0,-10,
     -10,  0,  5,  5,  5,  5,  0,-10,
      -5,  0,  5,  5,  5,  5,  0, -5,
       0,  0,  5,  5,  5,  5,  0, -5,
     -10,  5,  5,  5,  5,  5,  0,-10,
     -10,  0,  5,  0,  0,  0,  0,-10,
     -20,-10,-10, -5, -5,-10,-10,-20
    ],
    6: [
     -30,-40,-40,-50,-50,-40,-40,-30,
     -30,-40,-40,-50,-50,-40,-40,-30,
     -30,-40,-40,-50,-50,-40,-40,-30,
     -30,-40,-40,-50,-50,-40,-40,-30,
     -20,-30,-30,-40,-40,-30,-30,-20,
     -10,-20,-20,-20,-20,-20,-20,-10,
      20, 20,  0,  0,  0,  0, 20, 20,
      20, 30, 10,  0,  0, 10, 30, 20
    ]
  };

  const KING_ENDGAME = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
  ];

  function onBoard(sq) { return (sq & 0x88) === 0; }
  function fileOf(sq) { return sq & 7; }
  function rankOf(sq) { return 7 - (sq >> 4); }
  function sqFrom(file, rank) { return (7 - rank) * 16 + file; }
  function algebraic(sq) { return FILES[fileOf(sq)] + (rankOf(sq) + 1); }
  function fromAlgebraic(name) {
    return (7 - (name.charCodeAt(1) - 49)) * 16 + (name.charCodeAt(0) - 97);
  }

  function mkMove(from, to, promo) {
    return from | (to << 7) | ((promo || 0) << 14);
  }
  function moveFrom(m) { return m & 127; }
  function moveTo(m) { return (m >> 7) & 127; }
  function movePromo(m) { return (m >> 14) & 7; }

  function colorOf(piece) { return piece > 0 ? WHITE : BLACK; }
  function typeOf(piece) { return piece > 0 ? piece : -piece; }

  class Game {
    constructor(fen, opts) {
      this.track = !opts || opts.track !== false;
      this.load(fen || START_FEN);
    }

    load(fen) {
      const parts = String(fen).trim().split(/\s+/);
      const rows = parts[0].split('/');
      if (rows.length !== 8) throw new Error('Некорректный FEN');

      this.board = new Int8Array(128);
      this.kingW = -1;
      this.kingB = -1;

      for (let row = 0; row < 8; row++) {
        let file = 0;
        for (const ch of rows[row]) {
          if (ch >= '1' && ch <= '8') {
            file += ch.charCodeAt(0) - 48;
          } else {
            const type = 'pnbrqk'.indexOf(ch.toLowerCase()) + 1;
            if (!type) throw new Error('Некорректный FEN');
            const piece = ch === ch.toUpperCase() ? type : -type;
            const sq = row * 16 + file;
            this.board[sq] = piece;
            if (piece === KING) this.kingW = sq;
            if (piece === -KING) this.kingB = sq;
            file++;
          }
        }
      }

      this.side = parts[1] === 'b' ? BLACK : WHITE;
      this.castling = 0;
      const rights = parts[2] || '-';
      if (rights.includes('K')) this.castling |= CASTLE_WK;
      if (rights.includes('Q')) this.castling |= CASTLE_WQ;
      if (rights.includes('k')) this.castling |= CASTLE_BK;
      if (rights.includes('q')) this.castling |= CASTLE_BQ;
      this.ep = parts[3] && parts[3] !== '-' ? fromAlgebraic(parts[3]) : -1;
      this.halfmove = parseInt(parts[4], 10) || 0;
      this.fullmove = parseInt(parts[5], 10) || 1;

      this.history = [];
      this.keys = this.track ? [this.key()] : [];
      this.startFen = fen || START_FEN;
    }

    pieceAt(sq) { return this.board[sq]; }

    inCheck(color) {
      const king = color === WHITE ? this.kingW : this.kingB;
      return king >= 0 && this.isAttacked(king, -color);
    }

    isAttacked(sq, byColor) {
      const b = this.board;

      if (byColor === WHITE) {
        if (onBoard(sq + 15) && b[sq + 15] === PAWN) return true;
        if (onBoard(sq + 17) && b[sq + 17] === PAWN) return true;
      } else {
        if (onBoard(sq - 15) && b[sq - 15] === -PAWN) return true;
        if (onBoard(sq - 17) && b[sq - 17] === -PAWN) return true;
      }

      for (const off of KNIGHT_OFFSETS) {
        const t = sq + off;
        if (onBoard(t) && b[t] === byColor * KNIGHT) return true;
      }

      for (const off of KING_OFFSETS) {
        const t = sq + off;
        if (onBoard(t) && b[t] === byColor * KING) return true;
      }

      for (const dir of BISHOP_DIRS) {
        let t = sq + dir;
        while (onBoard(t)) {
          const p = b[t];
          if (p) {
            if (p === byColor * BISHOP || p === byColor * QUEEN) return true;
            break;
          }
          t += dir;
        }
      }

      for (const dir of ROOK_DIRS) {
        let t = sq + dir;
        while (onBoard(t)) {
          const p = b[t];
          if (p) {
            if (p === byColor * ROOK || p === byColor * QUEEN) return true;
            break;
          }
          t += dir;
        }
      }

      return false;
    }

    generateMoves(opts) {
      const capturesOnly = !!(opts && opts.capturesOnly);
      const moves = [];
      const b = this.board;
      const color = this.side;
      const dir = color === WHITE ? -16 : 16;
      const startRow = color === WHITE ? 6 : 1;
      const promoRow = color === WHITE ? 0 : 7;

      for (let row = 0; row < 8; row++) {
        for (let file = 0; file < 8; file++) {
          const from = row * 16 + file;
          const piece = b[from];
          if (!piece || colorOf(piece) !== color) continue;
          const type = typeOf(piece);

          if (type === PAWN) {
            const one = from + dir;
            if (onBoard(one) && b[one] === 0) {
              if ((one >> 4) === promoRow) {
                for (const p of PROMO_PIECES) moves.push(mkMove(from, one, p));
              } else if (!capturesOnly) {
                moves.push(mkMove(from, one));
                if ((from >> 4) === startRow) {
                  const two = from + dir * 2;
                  if (b[two] === 0) moves.push(mkMove(from, two));
                }
              }
            }

            for (const pd of [dir - 1, dir + 1]) {
              const to = from + pd;
              if (!onBoard(to)) continue;
              const target = b[to];
              if (target !== 0 && colorOf(target) !== color) {
                if ((to >> 4) === promoRow) {
                  for (const p of PROMO_PIECES) moves.push(mkMove(from, to, p));
                } else {
                  moves.push(mkMove(from, to));
                }
              } else if (target === 0 && to === this.ep) {
                moves.push(mkMove(from, to));
              }
            }
            continue;
          }

          if (type === KNIGHT || type === KING) {
            const offsets = type === KNIGHT ? KNIGHT_OFFSETS : KING_OFFSETS;
            for (const off of offsets) {
              const to = from + off;
              if (!onBoard(to)) continue;
              const target = b[to];
              if (target && colorOf(target) === color) continue;
              if (capturesOnly && target === 0) continue;
              moves.push(mkMove(from, to));
            }

            if (type === KING && !capturesOnly) {
              if (color === WHITE) {
                if ((this.castling & CASTLE_WK) && b[117] === 0 && b[118] === 0 &&
                    b[119] === ROOK && b[116] === KING &&
                    !this.isAttacked(116, BLACK) && !this.isAttacked(117, BLACK) &&
                    !this.isAttacked(118, BLACK)) {
                  moves.push(mkMove(116, 118));
                }
                if ((this.castling & CASTLE_WQ) && b[115] === 0 && b[114] === 0 &&
                    b[113] === 0 && b[112] === ROOK && b[116] === KING &&
                    !this.isAttacked(116, BLACK) && !this.isAttacked(115, BLACK) &&
                    !this.isAttacked(114, BLACK)) {
                  moves.push(mkMove(116, 114));
                }
              } else {
                if ((this.castling & CASTLE_BK) && b[5] === 0 && b[6] === 0 &&
                    b[7] === -ROOK && b[4] === -KING &&
                    !this.isAttacked(4, WHITE) && !this.isAttacked(5, WHITE) &&
                    !this.isAttacked(6, WHITE)) {
                  moves.push(mkMove(4, 6));
                }
                if ((this.castling & CASTLE_BQ) && b[3] === 0 && b[2] === 0 &&
                    b[1] === 0 && b[0] === -ROOK && b[4] === -KING &&
                    !this.isAttacked(4, WHITE) && !this.isAttacked(3, WHITE) &&
                    !this.isAttacked(2, WHITE)) {
                  moves.push(mkMove(4, 2));
                }
              }
            }
            continue;
          }

          const dirs = type === BISHOP ? BISHOP_DIRS :
                       type === ROOK ? ROOK_DIRS : QUEEN_DIRS;
          for (const d of dirs) {
            let to = from + d;
            while (onBoard(to)) {
              const target = b[to];
              if (target) {
                if (colorOf(target) !== color) moves.push(mkMove(from, to));
                break;
              }
              if (!capturesOnly) moves.push(mkMove(from, to));
              to += d;
            }
          }
        }
      }

      return moves;
    }

    legalMoves() {
      const pseudo = this.generateMoves();
      const legal = [];
      const track = this.track;
      this.track = false;
      for (const m of pseudo) {
        this.makeMove(m);
        if (!this.inCheck(-this.side)) legal.push(m);
        this.undoMove();
      }
      this.track = track;
      return legal;
    }
    makeMove(m) {
      const from = moveFrom(m);
      const to = moveTo(m);
      const promo = movePromo(m);
      const b = this.board;
      const piece = b[from];
      if (!piece) throw new Error('Пустой ход');
      const color = colorOf(piece);
      const type = typeOf(piece);

      let capturedSq = to;
      let captured = b[to];
      if (type === PAWN && to === this.ep && captured === 0) {
        capturedSq = to + (color === WHITE ? 16 : -16);
        captured = b[capturedSq];
      }

      const rec = {
        m, from, to, promo, piece, captured, capturedSq,
        castling: this.castling,
        ep: this.ep,
        halfmove: this.halfmove,
        fullmove: this.fullmove,
        kingW: this.kingW,
        kingB: this.kingB
      };
      this.history.push(rec);

      if (captured) b[capturedSq] = 0;
      b[from] = 0;
      b[to] = promo ? color * promo : piece;

      if (type === KING) {
        if (color === WHITE) this.kingW = to;
        else this.kingB = to;

        if (Math.abs(to - from) === 2) {
          const kingSide = to > from;
          const rookFrom = kingSide ? to + 1 : to - 2;
          const rookTo = kingSide ? to - 1 : to + 1;
          b[rookTo] = b[rookFrom];
          b[rookFrom] = 0;
        }
      }

      if (type === KING) {
        if (color === WHITE) this.castling &= ~(CASTLE_WK | CASTLE_WQ);
        else this.castling &= ~(CASTLE_BK | CASTLE_BQ);
      }
      if (from === 119 || to === 119) this.castling &= ~CASTLE_WK;
      if (from === 112 || to === 112) this.castling &= ~CASTLE_WQ;
      if (from === 7 || to === 7) this.castling &= ~CASTLE_BK;
      if (from === 0 || to === 0) this.castling &= ~CASTLE_BQ;

      if (type === PAWN && Math.abs(to - from) === 32) {
        this.ep = from + (color === WHITE ? -16 : 16);
      } else {
        this.ep = -1;
      }

      if (type === PAWN || captured) this.halfmove = 0;
      else this.halfmove++;
      if (color === BLACK) this.fullmove++;

      this.side = -this.side;
      if (this.track) this.keys.push(this.key());
      return rec;
    }

    undoMove() {
      const rec = this.history.pop();
      if (!rec) return null;
      const b = this.board;
      const { from, to, piece, captured, capturedSq } = rec;

      b[to] = 0;
      b[from] = piece;
      if (captured) b[capturedSq] = captured;

      if (typeOf(piece) === KING && Math.abs(to - from) === 2) {
        const kingSide = to > from;
        const rookFrom = kingSide ? to + 1 : to - 2;
        const rookTo = kingSide ? to - 1 : to + 1;
        b[rookFrom] = b[rookTo];
        b[rookTo] = 0;
      }

      this.castling = rec.castling;
      this.ep = rec.ep;
      this.halfmove = rec.halfmove;
      this.fullmove = rec.fullmove;
      this.kingW = rec.kingW;
      this.kingB = rec.kingB;
      this.side = -this.side;
      if (this.track) this.keys.pop();
      return rec;
    }

    key() {
      let out = '';
      for (let row = 0; row < 8; row++) {
        for (let file = 0; file < 8; file++) {
          const p = this.board[row * 16 + file];
          if (!p) out += '.';
          else if (p > 0) out += 'PNBRQK'[p - 1];
          else out += 'pnbrqk'[-p - 1];
        }
        out += '/';
      }
      let cast = '';
      if (this.castling & CASTLE_WK) cast += 'K';
      if (this.castling & CASTLE_WQ) cast += 'Q';
      if (this.castling & CASTLE_BK) cast += 'k';
      if (this.castling & CASTLE_BQ) cast += 'q';
      return out + (this.side === WHITE ? 'w' : 'b') + '|' +
        (cast || '-') + '|' + (this.ep >= 0 ? this.ep : '-');
    }

    fen() {
      let out = '';
      for (let row = 0; row < 8; row++) {
        let empty = 0;
        for (let file = 0; file < 8; file++) {
          const p = this.board[row * 16 + file];
          if (!p) {
            empty++;
          } else {
            if (empty) { out += empty; empty = 0; }
            const t = typeOf(p);
            out += p > 0 ? 'PNBRQK'[t - 1] : 'pnbrqk'[t - 1];
          }
        }
        if (empty) out += empty;
        if (row < 7) out += '/';
      }
      let cast = '';
      if (this.castling & CASTLE_WK) cast += 'K';
      if (this.castling & CASTLE_WQ) cast += 'Q';
      if (this.castling & CASTLE_BK) cast += 'k';
      if (this.castling & CASTLE_BQ) cast += 'q';
      return out + ' ' + (this.side === WHITE ? 'w' : 'b') + ' ' +
        (cast || '-') + ' ' + (this.ep >= 0 ? algebraic(this.ep) : '-') +
        ' ' + this.halfmove + ' ' + this.fullmove;
    }

    uci(m) {
      const promo = movePromo(m);
      return algebraic(moveFrom(m)) + algebraic(moveTo(m)) +
        (promo ? 'nbrq'[promo - 2] : '');
    }

    san(m) {
      const from = moveFrom(m);
      const to = moveTo(m);
      const promo = movePromo(m);
      const piece = this.board[from];
      const type = typeOf(piece);
      let text;

      if (type === KING && Math.abs(to - from) === 2) {
        text = to > from ? 'O-O' : 'O-O-O';
      } else if (type === PAWN) {
        const isCapture = this.board[to] !== 0 || to === this.ep;
        text = (isCapture ? FILES[fileOf(from)] + 'x' : '') + algebraic(to);
        if (promo) text += '=' + 'NBRQ'[promo - 2];
      } else {
        text = 'NBRQK'[type - 2];
        const legal = this.legalMoves();
        let sameFile = false;
        let sameRank = false;
        for (const other of legal) {
          const of = moveFrom(other);
          const ot = moveTo(other);
          if (ot !== to || of === from) continue;
          const op = this.board[of];
          if (typeOf(op) !== type || colorOf(op) !== colorOf(piece)) continue;
          if (fileOf(of) === fileOf(from)) sameFile = true;
          if (rankOf(of) === rankOf(from)) sameRank = true;
        }
        if (sameFile || sameRank) {
          if (!sameFile) text += FILES[fileOf(from)];
          else if (!sameRank) text += String(rankOf(from) + 1);
          else text += algebraic(from);
        }
        if (this.board[to] !== 0) text += 'x';
        text += algebraic(to);
      }

      const track = this.track;
      this.track = false;
      this.makeMove(m);
      const check = this.inCheck(this.side);
      const noMoves = this.legalMoves().length === 0;
      this.undoMove();
      this.track = track;

      if (check) text += noMoves ? '#' : '+';
      return text;
    }

    insufficientMaterial() {
      let minors = 0;
      let bishops = [];
      for (let row = 0; row < 8; row++) {
        for (let file = 0; file < 8; file++) {
          const p = this.board[row * 16 + file];
          if (!p) continue;
          const type = typeOf(p);
          if (type === PAWN || type === ROOK || type === QUEEN) return false;
          if (type === BISHOP) {
            minors++;
            bishops.push((fileOf(row * 16 + file) + rankOf(row * 16 + file)) & 1);
          } else if (type === KNIGHT) {
            minors++;
            bishops.push(-1);
          }
        }
      }
      if (minors <= 1) return true;
      if (minors === 2 && bishops.every((c) => c >= 0) && bishops[0] === bishops[1]) {
        return true;
      }
      return false;
    }

    status() {
      if (this.legalMoves().length === 0) {
        if (this.inCheck(this.side)) {
          return { over: true, winner: -this.side, reason: 'checkmate' };
        }
        return { over: true, winner: 0, reason: 'stalemate' };
      }
      if (this.halfmove >= 100) {
        return { over: true, winner: 0, reason: 'fifty' };
      }
      if (this.track && this.keys.length) {
        const last = this.keys[this.keys.length - 1];
        let count = 0;
        for (let i = this.keys.length - 1; i >= 0; i--) {
          if (this.keys[i] === last) count++;
          if (count >= 3) return { over: true, winner: 0, reason: 'repetition' };
        }
      }
      if (this.insufficientMaterial()) {
        return { over: true, winner: 0, reason: 'material' };
      }
      return null;
    }

  }

  function pstIndex(sq, color) {
    const row = sq >> 4;
    const file = sq & 7;
    return ((color === WHITE ? row : 7 - row) << 3) | file;
  }

  function evaluate(game) {
    const b = game.board;
    let score = 0;
    let material = 0;
    let bishopsW = 0;
    let bishopsB = 0;
    const pawnFilesW = [0, 0, 0, 0, 0, 0, 0, 0];
    const pawnFilesB = [0, 0, 0, 0, 0, 0, 0, 0];
    const pawnRowsW = [[], [], [], [], [], [], [], []];
    const pawnRowsB = [[], [], [], [], [], [], [], []];
    let rooksW = 0;
    let rooksB = 0;

    for (let row = 0; row < 8; row++) {
      for (let file = 0; file < 8; file++) {
        const sq = row * 16 + file;
        const p = b[sq];
        if (!p) continue;
        const type = typeOf(p);
        if (type !== KING) material += VALUES[type];
        if (type === BISHOP) {
          if (p > 0) bishopsW++; else bishopsB++;
        } else if (type === PAWN) {
          if (p > 0) {
            pawnFilesW[file]++;
            pawnRowsW[file].push(row);
          } else {
            pawnFilesB[file]++;
            pawnRowsB[file].push(row);
          }
        } else if (type === ROOK) {
          if (p > 0) rooksW++; else rooksB++;
        }
      }
    }

    const endgame = material <= 2600;

    for (let row = 0; row < 8; row++) {
      for (let file = 0; file < 8; file++) {
        const sq = row * 16 + file;
        const p = b[sq];
        if (!p) continue;
        const color = colorOf(p);
        const type = typeOf(p);
        const idx = pstIndex(sq, color);
        let bonus = 0;
        if (type === KING) {
          bonus = endgame ? KING_ENDGAME[idx] : PST[6][idx];
        } else {
          bonus = PST[type][idx];
        }
        score += color * (VALUES[type] + bonus);

        if (type === PAWN) {
          // Изолированные и сдвоенные пешки слабее, проходные — сильнее.
          const ownFiles = color === WHITE ? pawnFilesW : pawnFilesB;
          const enemyFiles = color === WHITE ? pawnFilesB : pawnFilesW;
          if (ownFiles[file] > 1) score -= color * 14;
          if ((file === 0 || !ownFiles[file - 1]) && (file === 7 || !ownFiles[file + 1])) {
            score -= color * 16;
          }
          const enemyRows = color === WHITE ? pawnRowsB : pawnRowsW;
          let blocked = false;
          for (let f = Math.max(0, file - 1); f <= Math.min(7, file + 1) && !blocked; f++) {
            for (const enemyRow of enemyRows[f]) {
              if (color === WHITE ? enemyRow < row : enemyRow > row) {
                blocked = true;
                break;
              }
            }
          }
          if (!blocked) {
            const advance = color === WHITE ? (6 - row) : (row - 1);
            score += color * (10 + Math.max(0, advance) * 10);
          }
        } else if (type === ROOK) {
          // Ладья любит открытые и полуоткрытые линии.
          const ownPawns = color === WHITE ? pawnFilesW : pawnFilesB;
          const enemyPawns = color === WHITE ? pawnFilesB : pawnFilesW;
          if (!ownPawns[file]) score += color * (enemyPawns[file] ? 12 : 24);
        }
      }
    }

    if (bishopsW >= 2) score += 32;
    if (bishopsB >= 2) score -= 32;
    // Небольшой бонус за активность ферзя в дебюте и центр в эндшпиле.
    if (!endgame) {
      if (b[52] || b[51] || b[36] || b[35]) {
        const centerW = (b[52] > 0) + (b[51] > 0) + (b[36] > 0) + (b[35] > 0);
        const centerB = (b[52] < 0) + (b[51] < 0) + (b[36] < 0) + (b[35] < 0);
        score += (centerW - centerB) * 10;
      }
    }

    const relative = game.side === WHITE ? score : -score;
    return relative + 8;
  }

  function capturedValue(game, m) {
    const to = moveTo(m);
    const from = moveFrom(m);
    const target = game.board[to];
    if (target) return VALUES[typeOf(target)];
    const piece = game.board[from];
    if (piece && typeOf(piece) === PAWN && to === game.ep) return VALUES[PAWN];
    return 0;
  }

  function historyIndex(game, m) {
    const piece = game.board[moveFrom(m)];
    const type = piece ? typeOf(piece) : PAWN;
    return type * 128 + moveTo(m);
  }

  function orderMoves(game, moves, ply, ttMove, killerA, killerB) {
    const b = game.board;
    const scored = moves.map((m) => {
      const from = moveFrom(m);
      const to = moveTo(m);
      const victim = b[to];
      const attacker = b[from];
      let s = 0;
      if (m === ttMove) {
        s = 1000000000;
      } else if (victim) {
        s = 1000000 + VALUES[typeOf(victim)] * 16 - (attacker ? VALUES[typeOf(attacker)] : 0);
      } else if (m === killerA) {
        s = 900000;
      } else if (m === killerB) {
        s = 800000;
      } else {
        s = history[historyIndex(game, m)] || 0;
      }
      const promo = movePromo(m);
      if (promo) s += VALUES[promo] * 8;
      if (m === killerA) s += 1000;
      return { m, s };
    });
    scored.sort((a, b) => b.s - a.s);
    return scored.map((x) => x.m);
  }

  let searchNodes = 0;
  let searchDeadline = 0;
  let transposition = new Map();
  let killers = [];
  const history = new Uint32Array(7 * 128);

  function checkTime() {
    if ((searchNodes & 1023) === 0 && performance.now() >= searchDeadline) {
      throw TIMEOUT;
    }
  }

  function quiesce(game, alpha, beta, ply, qdepth) {
    searchNodes++;
    checkTime();

    const inCheck = game.inCheck(game.side);
    let best;

    if (!inCheck) {
      best = evaluate(game);
      if (best >= beta) return beta;
      if (best > alpha) alpha = best;
    } else {
      best = -INF;
    }

    if (qdepth >= 5) return inCheck ? evaluate(game) : alpha;

    const moves = orderMoves(game, game.generateMoves({ capturesOnly: !inCheck }), ply);
    let any = false;

    for (const m of moves) {
      game.makeMove(m);
      if (game.inCheck(-game.side)) {
        game.undoMove();
        continue;
      }
      any = true;
      let score;
      try {
        score = -quiesce(game, -beta, -alpha, ply + 1, qdepth + 1);
      } catch (err) {
        game.undoMove();
        throw err;
      }
      game.undoMove();

      if (score > best) best = score;
      if (score > alpha) alpha = score;
      if (alpha >= beta) return beta;
    }

    if (inCheck && !any) return -MATE + ply;
    return inCheck ? best : alpha;
  }

  function negamax(game, depth, alpha, beta, ply) {
    searchNodes++;
    checkTime();

    // Проверка дает дополнительную глубину, но не раздувает поиск бесконечно.
    const inCheck = game.inCheck(game.side);
    if (inCheck && depth < 8) depth++;

    if (depth <= 0) return quiesce(game, alpha, beta, ply, 0);

    const key = game.key();
    const hit = transposition.get(key);
    if (hit && hit.depth >= depth) {
      let score = hit.score;
      if (score > MATE - 1000) score -= ply;
      else if (score < -MATE + 1000) score += ply;
      if (hit.flag === 0) return score;
      if (hit.flag === 1 && score >= beta) return score;
      if (hit.flag === 2 && score <= alpha) return score;
    }

    const killer = killers[ply] || (killers[ply] = [0, 0]);
    const moves = orderMoves(
      game,
      game.generateMoves(),
      ply,
      hit ? hit.move : 0,
      killer[0],
      killer[1]
    );
    let any = false;
    let bestScore = -INF;
    let bestMove = 0;
    let moveIndex = 0;

    for (const m of moves) {
      game.makeMove(m);
      if (game.inCheck(-game.side)) {
        game.undoMove();
        continue;
      }
      any = true;

      let score;
      try {
        if (moveIndex === 0) {
          score = -negamax(game, depth - 1, -beta, -alpha, ply + 1);
        } else {
          score = -negamax(game, depth - 1, -alpha - 1, -alpha, ply + 1);
          if (score > alpha && score < beta) {
            score = -negamax(game, depth - 1, -beta, -alpha, ply + 1);
          }
        }
      } catch (err) {
        game.undoMove();
        throw err;
      }
      game.undoMove();
      moveIndex++;

      if (score > bestScore) {
        bestScore = score;
        bestMove = m;
      }
      if (score > alpha) {
        alpha = score;
      }
      if (alpha >= beta) {
        if (!capturedValue(game, m)) {
          if (killer[0] !== m) {
            killer[1] = killer[0];
            killer[0] = m;
          }
          history[historyIndex(game, m)] += depth * depth;
        }
        setTt(key, depth, bestScore, 1, bestMove, ply);
        return bestScore;
      }
    }

    if (!any) return inCheck ? -MATE + ply : 0;
    setTt(key, depth, bestScore, 0, bestMove, ply);
    return bestScore;
  }

  function setTt(key, depth, score, flag, move, ply) {
    if (transposition.size > 90000) transposition.clear();
    let stored = score;
    if (score > MATE - 1000) stored = score + ply;
    else if (score < -MATE + 1000) stored = score - ply;
    transposition.set(key, { depth, score: stored, flag, move });
  }

  function search(game, options) {
    options = options || {};
    const legal = game.legalMoves();
    if (!legal.length) {
      return { move: null, score: 0, depth: 0, nodes: 0 };
    }

    if (options.randomChance && Math.random() < options.randomChance) {
      return {
        move: legal[Math.floor(Math.random() * legal.length)],
        score: 0,
        depth: 1,
        nodes: 0,
        random: true
      };
    }

    searchNodes = 0;
    searchDeadline = performance.now() + Math.max(30, options.time || 1000);
    transposition = new Map();
    killers = [];
    history.fill(0);

    const maxDepth = Math.max(1, options.depth || 3);
    const jitter = options.randomness || 0;
    let ordered = orderMoves(game, legal.slice());
    let best = ordered[0];
    let bestScore = 0;
    let completed = 0;

    for (let depth = 1; depth <= maxDepth; depth++) {
      let alpha = -INF;
      let localBest = null;
      let localScore = -INF;
      let localRaw = 0;
      let aborted = false;
      let firstMove = true;

      if (best) ordered = [best].concat(ordered.filter((m) => m !== best));

      for (const m of ordered) {
        game.makeMove(m);
        let score;
        try {
          if (firstMove) {
            score = -negamax(game, depth - 1, -INF, -alpha, 1);
          } else {
            score = -negamax(game, depth - 1, -alpha - 1, -alpha, 1);
            if (score > alpha) {
              score = -negamax(game, depth - 1, -INF, -alpha, 1);
            }
          }
        } catch (err) {
          game.undoMove();
          if (err === TIMEOUT) {
            aborted = true;
            break;
          }
          throw err;
        }
        game.undoMove();
        firstMove = false;

        const noisy = score + (jitter ? (Math.random() * 2 - 1) * jitter : 0);
        if (noisy > localScore) {
          localScore = noisy;
          localRaw = score;
          localBest = m;
        }
        if (score > alpha) alpha = score;
      }

      if (!aborted) {
        if (localBest !== null) best = localBest;
        bestScore = localRaw;
        completed = depth;
        if (Math.abs(bestScore) > MATE - 1000) break;
      }

      if (aborted || performance.now() >= searchDeadline) break;
    }

    return { move: best, score: bestScore, depth: completed, nodes: searchNodes };
  }

  global.ChessEngine = {
    Game,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    START_FEN,
    algebraic, fromAlgebraic,
    mkMove, moveFrom, moveTo, movePromo,
    colorOf, typeOf,
    evaluate, search
  };
})(typeof self !== 'undefined' ? self : globalThis);
