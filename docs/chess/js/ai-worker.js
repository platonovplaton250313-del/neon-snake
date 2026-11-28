/* CHESS ARENA — фоновый расчёт хода компьютера. */
importScripts('engine.js');

self.onmessage = function (event) {
  const data = event.data || {};
  if (data.type !== 'search') return;

  try {
    const game = new self.ChessEngine.Game(data.fen, { track: false });
    const result = self.ChessEngine.search(game, data.options || {});
    self.postMessage({
      type: 'result',
      id: data.id,
      move: result.move,
      score: result.score,
      depth: result.depth,
      nodes: result.nodes
    });
  } catch (error) {
    self.postMessage({
      type: 'error',
      id: data.id,
      message: String((error && error.message) || error)
    });
  }
};
