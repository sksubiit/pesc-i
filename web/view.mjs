export function boardCells(fen, flipped = false) {
  const cells = [];
  for (const row of fen.split(" ")[0].split("/")) {
    for (const char of row) {
      if (/^[1-8]$/.test(char)) cells.push(...Array(Number(char)).fill(null));
      else cells.push(char);
    }
  }
  if (cells.length !== 64) throw new Error("Invalid board position.");
  return Array.from({length:64}, (_, offset) => {
    const index = flipped ? 63-offset : offset;
    const file = index%8, rank = 8-Math.floor(index/8);
    return {name:"abcdefgh"[file]+rank, file, rank, piece:cells[index],
      light:(file+rank)%2 === 0, rankLabel:file === (flipped ? 7 : 0),
      fileLabel:rank === (flipped ? 8 : 1)};
  });
}
export function formatEvaluation(value) {
  if (!value) return {text:"—", percent:50};
  if (value.mate !== null) return {
    text:(value.mate > 0 ? "White" : "Black")+" M"+Math.abs(value.mate),
    percent:value.mate > 0 ? 96 : 4
  };
  const cp = value.cp ?? 0;
  return {text:(cp >= 0 ? "+" : "")+(cp/100).toFixed(2),
          percent:Math.max(4,Math.min(96,50+46*Math.tanh(cp/450)))};
}
