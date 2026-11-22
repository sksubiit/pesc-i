import test from "node:test";
import assert from "node:assert/strict";
import {boardCells,formatEvaluation} from "../../web/view.mjs";
const start="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
test("board orientation, pieces, and square colors",()=>{
  const normal=boardCells(start),flipped=boardCells(start,true);
  assert.equal(normal[0].name,"a8");assert.equal(normal[0].light,true);
  assert.equal(normal[56].name,"a1");assert.equal(normal[56].light,false);
  assert.deepEqual(flipped.map(c=>c.name),normal.map(c=>c.name).reverse());
  assert.equal(normal.filter(c=>c.piece).length,32);
});
test("evaluation colors are from White's perspective",()=>{
  assert.equal(formatEvaluation({cp:36,mate:null}).text,"+0.36");
  assert.ok(formatEvaluation({cp:-100,mate:null}).percent<50);
  assert.equal(formatEvaluation({cp:null,mate:-3}).text,"Black M3");
});
