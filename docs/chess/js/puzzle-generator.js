/* CHESS ARENA — бесконечный генератор тактических задач.
   Каждая позиция проверяется движком и правилами перед выдачей. */
(function (global) {
  'use strict';

  const E = global.ChessEngine;
  const FILES = 'abcdefgh';
  const KNIGHT_OFFSETS = [33, 31, 18, 14, -14, -18, -31, -33];
  const PAWN = 1;
  const KNIGHT = 2;
  const ROOK = 4;
  const QUEEN = 5;

  function rnd(n) { return Math.floor(Math.random() * n); }
  function choose(list) { return list[rnd(list.length)]; }
  function onBoard(sq) { return (sq & 0x88) === 0; }
  function randomSq() { return (rnd(8) << 4) | rnd(8); }
  function kingAdjacent(a, b) {
    return Math.abs((a & 7) - (b & 7)) <= 1 && Math.abs((a >> 4) - (b >> 4)) <= 1;
  }
  function knightAttacks(from, to) {
    if (!onBoard(from) || !onBoard(to)) return false;
    return KNIGHT_OFFSETS.some((off) => from + off === to);
  }
  function square(file, rank) { return E.fromAlgebraic(FILES[file] + rank); }
  function charFor(type, color) {
    return color === 1 ? 'PNBRQK'[type - 1] : 'pnbrqk'[type - 1];
  }

  function buildFen(pieces, side) {
    const grid = Array.from({ length: 8 }, () => Array(8).fill(''));
    for (const piece of pieces) {
      grid[piece.sq >> 4][piece.sq & 7] = charFor(piece.type, piece.color);
    }
    const rows = grid.map((row) => {
      let out = '';
      let empty = 0;
      for (const value of row) {
        if (!value) {
          empty++;
        } else {
          if (empty) { out += empty; empty = 0; }
          out += value;
        }
      }
      if (empty) out += empty;
      return out;
    });
    return `${rows.join('/')} ${side === 1 ? 'w' : 'b'} - - 0 1`;
  }

  function validPosition(game) {
    if (game.kingW < 0 || game.kingB < 0) return false;
    if (kingAdjacent(game.kingW, game.kingB)) return false;
    if (game.inCheck(game.side) || game.inCheck(-game.side)) return false;
    return true;
  }

  function makeItem(level, fen, lines, extra) {
    return Object.assign({
      id: `gen-${level}-${Date.now()}-${rnd(1000000)}`,
      title: 'Тактическая задача',
      theme: 'Тактика',
      level,
      rating: 1000,
      fen,
      lines,
      moves: lines[0].slice(),
      hint: 'Ищите форсированный ход: шах, взятие или удар по двум фигурам.',
      idea: 'Найдите лучший ход и доведите комбинацию до конца.',
      generated: true
    }, extra || {});
  }

  function fenSide(fen) {
    const parts = String(fen || '').trim().split(/\s+/);
    return parts[1] === 'b' ? -1 : 1;
  }

  function appendPawns(pieces, color, count, forbidden) {
    for (let i = 0; i < count; i++) {
      for (let guard = 0; guard < 24; guard++) {
        const file = rnd(8);
        const rank = color === 1 ? 2 + rnd(3) : 4 + rnd(3);
        const sq = square(file, rank);
        if (forbidden.includes(sq) || pieces.some((p) => p.sq === sq)) continue;
        pieces.push({ sq, type: PAWN, color });
        break;
      }
    }
  }

  function fallback(level) {
    const classics = (global.ChessPuzzles && global.ChessPuzzles.list) || [];
    const pool = classics.filter((item) => item.level === level);
    if (!pool.length) return null;
    const source = choose(pool);
    return makeItem(level, source.fen, [source.moves.slice()], {
      title: source.title,
      theme: source.theme,
      rating: source.rating,
      hint: source.hint,
      idea: source.idea
    });
  }

  /* ---------- уровень 1: мат в один ход ---------- */
  function generateMateInOne() {
    const edge = [];
    for (let row = 0; row < 8; row++) {
      for (let file = 0; file < 8; file++) {
        if (row === 0 || row === 7 || file === 0 || file === 7) {
          edge.push(row * 16 + file);
        }
      }
    }

    for (let attempt = 0; attempt < 260; attempt++) {
      const blackKing = choose(edge);
      const whiteKing = randomSq();
      if (whiteKing === blackKing || kingAdjacent(whiteKing, blackKing)) continue;

      const whiteQueen = randomSq();
      const whiteRook = randomSq();
      if ([blackKing, whiteKing].includes(whiteQueen) || [blackKing, whiteKing, whiteQueen].includes(whiteRook)) continue;
      if (kingAdjacent(whiteQueen, blackKing) || kingAdjacent(whiteRook, blackKing)) continue;

      const pieces = [
        { sq: blackKing, type: 6, color: -1 },
        { sq: whiteKing, type: 6, color: 1 },
        { sq: whiteQueen, type: QUEEN, color: 1 },
        { sq: whiteRook, type: ROOK, color: 1 }
      ];

      // Чёрные пешки и иногда ладья делают позицию ближе к реальной партии.
      appendPawns(pieces, -1, 1 + rnd(3), [blackKing, whiteKing, whiteQueen, whiteRook]);
      if (Math.random() < 0.4) {
        for (let guard = 0; guard < 16; guard++) {
          const sq = randomSq();
          if (pieces.some((p) => p.sq === sq) || kingAdjacent(sq, blackKing)) continue;
          pieces.push({ sq, type: ROOK, color: -1 });
          break;
        }
      }
      appendPawns(pieces, 1, rnd(3), [blackKing, whiteKing, whiteQueen, whiteRook]);

      const fen = buildFen(pieces, 1);
      let game;
      try { game = new E.Game(fen, { track: false }); } catch (err) { continue; }
      if (!validPosition(game)) continue;

      const mates = [];
      for (const move of game.legalMoves()) {
        game.makeMove(move);
        const mate = game.legalMoves().length === 0 && game.inCheck(game.side);
        game.undoMove();
        if (mate) {
          const uci = game.uci(move);
          if (!mates.includes(uci)) mates.push(uci);
        }
      }
      if (!mates.length) continue;

      const lines = mates.slice(0, 6).map((uci) => [uci]);
      return makeItem(1, fen, lines, {
        title: 'Мат в один ход',
        theme: 'Мат в 1',
        rating: 950 + rnd(160),
        hint: 'Проверьте все шахи. Один из них не оставляет королю ни одного поля — даже с защитниками рядом.',
        idea: 'Король на краю доски. Шах отсекает последние поля, а лишние фигуры соперника только мешают ему защититься.'
      });
    }
    return null;
  }

  /* ---------- уровень 2: вилка конём ---------- */
  function generateKnightFork() {
    for (let attempt = 0; attempt < 500; attempt++) {
      const forkSq = randomSq();
      const targets = KNIGHT_OFFSETS
        .map((off) => forkSq + off)
        .filter((sq) => onBoard(sq));
      if (targets.length < 4) continue;

      const blackKing = choose(targets);
      if (kingAdjacent(forkSq, blackKing)) continue;
      const queenTargets = targets.filter((sq) => sq !== blackKing && !kingAdjacent(sq, blackKing));
      if (!queenTargets.length) continue;
      const blackQueen = choose(queenTargets);

      const starts = KNIGHT_OFFSETS
        .map((off) => forkSq + off)
        .filter((sq) => onBoard(sq) && sq !== blackKing && sq !== blackQueen);
      if (!starts.length) continue;
      const whiteKnight = choose(starts);

      const whiteKing = randomSq();
      if (whiteKing === blackKing || whiteKing === blackQueen || whiteKing === whiteKnight) continue;
      if (kingAdjacent(whiteKing, blackKing) || kingAdjacent(whiteKing, blackQueen)) continue;
      if (knightAttacks(whiteKnight, blackKing) || knightAttacks(whiteKnight, blackQueen)) continue;

      const pieces = [
        { sq: blackKing, type: 6, color: -1 },
        { sq: blackQueen, type: QUEEN, color: -1 },
        { sq: whiteKing, type: 6, color: 1 },
        { sq: whiteKnight, type: KNIGHT, color: 1 }
      ];
      const forbidden = [blackKing, blackQueen, whiteKing, whiteKnight, forkSq];
      appendPawns(pieces, -1, rnd(3), forbidden);
      appendPawns(pieces, 1, rnd(2), forbidden);
      const fen = buildFen(pieces, 1);

      let game;
      try { game = new E.Game(fen, { track: false }); } catch (err) { continue; }
      if (!validPosition(game)) continue;

      const forkMove = game.legalMoves().find(
        (move) => E.moveFrom(move) === whiteKnight && E.moveTo(move) === forkSq && !E.movePromo(move)
      );
      if (!forkMove) continue;
      const forkUci = game.uci(forkMove);

      game.makeMove(forkMove);
      if (!game.inCheck(game.side)) { game.undoMove(); continue; }
      const replies = game.legalMoves();
      if (!replies.length) { game.undoMove(); continue; }
      if (replies.some((move) => E.moveTo(move) === forkSq)) { game.undoMove(); continue; }

      const options = [];
      for (const reply of replies) {
        game.makeMove(reply);
        const capture = game.legalMoves().find(
          (move) => E.moveFrom(move) === forkSq && E.moveTo(move) === blackQueen
        );
        if (capture) options.push({ reply, capture });
        game.undoMove();
      }
      game.undoMove();
      if (!options.length) continue;

      const option = choose(options);
      const lines = [[forkUci, game.uci(option.reply), game.uci(option.capture)]];
      return makeItem(2, fen, lines, {
        title: 'Вилка конём',
        theme: 'Вилка',
        rating: 1260 + rnd(260),
        hint: 'Конь одним ходом может напасть на короля и на ферзя. Найдите это поле.',
        idea: 'Конь даёт шах королю и одновременно нападает на ферзя. Король обязан отойти, и ферзь теряется.'
      });
    }
    return null;
  }

  /* ---------- уровень 3: жертва ферзя на последней горизонтали ---------- */
  function generateBackRankSacrifice() {
    for (let attempt = 0; attempt < 200; attempt++) {
      const mirror = Math.random() < 0.5;
      const targetFile = mirror ? 3 : 4;
      const kingFile = mirror ? 1 : 6;
      const blackRookFile = mirror ? 2 : 5;
      const target = square(targetFile, 8);
      const blackKing = square(kingFile, 8);
      const blackRook = square(blackRookFile, 8);
      const whiteRook = square(targetFile, 1);
      const queenRank = 2 + rnd(3);
      const whiteQueen = square(targetFile, queenRank);
      if (whiteQueen === whiteRook) continue;

      const whiteKing = randomSq();
      if ([blackKing, blackRook, whiteRook, whiteQueen].includes(whiteKing)) continue;
      if (kingAdjacent(whiteKing, blackKing)) continue;

      const pieces = [
        { sq: blackKing, type: 6, color: -1 },
        { sq: blackRook, type: ROOK, color: -1 },
        { sq: whiteKing, type: 6, color: 1 },
        { sq: whiteRook, type: ROOK, color: 1 },
        { sq: whiteQueen, type: QUEEN, color: 1 }
      ];

      // Пешечное прикрытие чёрного короля.
      for (let f = kingFile - 1; f <= kingFile + 1; f++) {
        if (f < 0 || f > 7) continue;
        pieces.push({ sq: square(f, 7), type: PAWN, color: -1 });
      }

      // Пара белых пешек для разнообразия.
      for (let i = 0; i < rnd(4); i++) {
        const file = rnd(8);
        if (file === targetFile) continue;
        const rank = 2 + rnd(3);
        const sq = square(file, rank);
        if (pieces.some((p) => p.sq === sq) || kingAdjacent(sq, blackKing)) continue;
        pieces.push({ sq, type: PAWN, color: 1 });
      }

      const fen = buildFen(pieces, 1);
      let game;
      try { game = new E.Game(fen, { track: false }); } catch (err) { continue; }
      if (!validPosition(game)) continue;

      const queenMove = game.legalMoves().find(
        (move) => E.moveFrom(move) === whiteQueen && E.moveTo(move) === target
      );
      if (!queenMove) continue;
      const queenUci = game.uci(queenMove);

      game.makeMove(queenMove);
      const rookReply = game.legalMoves().find(
        (move) => E.moveFrom(move) === blackRook && E.moveTo(move) === target
      );
      if (!rookReply) { game.undoMove(); continue; }
      const replyUci = game.uci(rookReply);

      game.makeMove(rookReply);
      const mateMoves = [];
      for (const move of game.legalMoves()) {
        game.makeMove(move);
        if (game.legalMoves().length === 0 && game.inCheck(game.side)) {
          mateMoves.push(game.uci(move));
        }
        game.undoMove();
      }
      game.undoMove();
      game.undoMove();

      const recaptureUci = game.uci(E.mkMove(whiteRook, target));
      if (!mateMoves.includes(recaptureUci)) continue;

      return makeItem(3, fen, [[queenUci, replyUci, recaptureUci]], {
        title: 'Жертва ферзя на последней горизонтали',
        theme: 'Жертва',
        rating: 1720 + rnd(280),
        hint: 'Ферзь может пожертвовать собой на последней горизонтали. Ладья с первой линии поддержит удар.',
        idea: 'Ферзь вынуждает ладью соперника взять себя, освобождая последнюю горизонталь для мата второй ладьёй.'
      });
    }
    return null;
  }

  function findMateInOne(game) {
    for (const move of game.legalMoves()) {
      game.makeMove(move);
      const mate = game.legalMoves().length === 0 && game.inCheck(game.side);
      game.undoMove();
      if (mate) return move;
    }
    return null;
  }

  /* ---------- уровень 4: форсированный мат в два хода ---------- */
  function generateMateInTwo() {
    const edge = [];
    for (let row = 0; row < 8; row++) {
      for (let file = 0; file < 8; file++) {
        if (row === 0 || row === 7 || file === 0 || file === 7) {
          edge.push(row * 16 + file);
        }
      }
    }

    for (let attempt = 0; attempt < 90; attempt++) {
      const blackKing = choose(edge);
      const whiteKing = randomSq();
      if (whiteKing === blackKing || kingAdjacent(whiteKing, blackKing)) continue;

      const whiteQueen = randomSq();
      const whiteRook = randomSq();
      if ([blackKing, whiteKing].includes(whiteQueen) || [blackKing, whiteKing, whiteQueen].includes(whiteRook)) continue;
      if (kingAdjacent(whiteQueen, blackKing) || kingAdjacent(whiteRook, blackKing)) continue;

      const pieces = [
        { sq: blackKing, type: 6, color: -1 },
        { sq: whiteKing, type: 6, color: 1 },
        { sq: whiteQueen, type: QUEEN, color: 1 },
        { sq: whiteRook, type: ROOK, color: 1 }
      ];
      const banned = [blackKing, whiteKing, whiteQueen, whiteRook];
      appendPawns(pieces, -1, rnd(3), banned);
      appendPawns(pieces, 1, rnd(2), banned);

      const fen = buildFen(pieces, 1);
      let game;
      try { game = new E.Game(fen, { track: false }); } catch (err) { continue; }
      if (!validPosition(game)) continue;

      const legal = game.legalMoves();
      if (legal.length < 8) continue;

      const candidates = [];
      for (const first of legal) {
        game.makeMove(first);
        const replies = game.legalMoves();
        if (!replies.length) { game.undoMove(); continue; }
        const givesCheck = game.inCheck(game.side);
        let good = true;
        let example = null;

        for (const reply of replies) {
          game.makeMove(reply);
          const mate = findMateInOne(game);
          game.undoMove();
          if (!mate) { good = false; break; }
          if (!example) example = { reply, mate };
        }
        game.undoMove();
        if (good && example) {
          candidates.push({ first, example, givesCheck });
          if (candidates.length >= 6) break;
        }
      }

      if (!candidates.length) continue;
      const chosen = candidates.find((item) => item.givesCheck) || choose(candidates);
      const firstUci = game.uci(chosen.first);
      const replyUci = game.uci(chosen.example.reply);
      const mateUci = game.uci(chosen.example.mate);

      return makeItem(4, fen, [[firstUci, replyUci, mateUci]], {
        title: 'Форсированный мат в два хода',
        theme: 'Мат в 2',
        rating: 2060 + rnd(320),
        hint: 'Найдите первый ход, после которого у чёрных нет защиты от мата на следующем ходу.',
        idea: 'Первый ход отнимает у короля ключевые поля или жертвует фигуру. Любой ответ чёрных заканчивается матом.'
      });
    }
    return null;
  }

  function generate(level) {
    const safeLevel = level === 2 || level === 3 || level === 4 ? level : 1;
    let item = null;
    if (safeLevel === 1) item = generateMateInOne();
    else if (safeLevel === 2) item = generateKnightFork();
    else if (safeLevel === 3) item = generateBackRankSacrifice();
    else item = generateMateInTwo();
    return item || fallback(safeLevel);
  }

  global.ChessPuzzleGen = { generate };
})(window);
