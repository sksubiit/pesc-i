import test from "node:test";
import assert from "node:assert/strict";
import {Chess} from "../../web/vendor/chess.mjs";
import {MatchController,resultOf} from "../../web/match.mjs";

const tick=()=>new Promise(resolve=>setTimeout(resolve,1));
async function until(predicate) {
  const end=Date.now()+2000;
  while(!predicate() && Date.now()<end) await tick();
  assert.ok(predicate(),"Expected state was not reached");
}
class Engine {
  constructor(){this.stopped=false;this.release=null;this.pending=null;}
  async init(){return "Fake engine";}
  async bestMove(moves){
    const board=new Chess();
    for(const uci of moves) board.move({from:uci.slice(0,2),to:uci.slice(2,4),promotion:uci[4]});
    const move=board.moves({verbose:true})[0];
    return new Promise(resolve=>{this.release=()=>resolve({
      uci:move.from+move.to+(move.promotion||""),score:{type:"cp",value:20}
    });});
  }
  stop(){this.stopped=true;}
}
test("a result arriving after pause cannot advance the game",async()=>{
  const engines=[],controller=new MatchController(()=>{const e=new Engine();engines.push(e);return e;});
  controller.newGame({paceMs:0});
  await until(()=>engines[0]?.release);
  const release=engines[0].release;
  controller.pause();release();await tick();
  assert.equal(controller.snapshot().moves.length,0);
  assert.ok(engines.every(e=>e.stopped));controller.close();
});
test("reset during search discards stale moves and releases old workers",async()=>{
  const engines=[],controller=new MatchController(()=>{const e=new Engine();engines.push(e);return e;});
  controller.newGame({paceMs:0});
  await until(()=>engines[0]?.release);
  const release=engines[0].release;
  controller.newGame({paceMs:0});release();
  await until(()=>engines[2]?.release);
  assert.equal(controller.snapshot().moves.length,0);
  assert.equal(controller.gameNumber,2);assert.equal(engines[0].stopped,true);
  controller.close();
});
test("resume preserves the position and uses fresh engines",async()=>{
  const engines=[],controller=new MatchController(()=>{const e=new Engine();engines.push(e);return e;});
  controller.newGame({paceMs:100});
  await until(()=>engines[0]?.release);engines[0].release();
  await until(()=>controller.snapshot().moves.length===1);
  controller.pause();
  const fen=controller.game.fen();
  controller.start();await until(()=>engines.length===4);
  assert.equal(controller.game.fen(),fen);controller.close();
});
test("game endings and cutoffs are distinguished correctly",()=>{
  const mate=new Chess();for(const move of ["f3","e5","g4","Qh4#"]) mate.move(move);
  assert.equal(resultOf(mate,300).result,"0-1");
  const cutoff=new Chess();cutoff.move("e4");
  assert.equal(resultOf(cutoff,1).result,"*");
  const draw=new Chess("8/8/8/8/8/8/3k4/K7 w - - 0 1");
  assert.equal(resultOf(draw,300).result,"1/2-1/2");
});
test("automatic rematches can be cancelled during intermission",async()=>{
  const engines=[],controller=new MatchController(()=>{const e=new Engine();engines.push(e);return e;});
  controller.newGame({paceMs:0,maxPlies:1,intermissionMs:20,autoNext:true});
  await until(()=>engines[0]?.release);engines[0].release();
  await until(()=>controller.snapshot().phase==="finished");
  controller.pause();await new Promise(r=>setTimeout(r,40));
  assert.equal(controller.gameNumber,1);assert.equal(controller.running,false);controller.close();
});

test("a failed second worker also shuts down the first worker",async()=>{
  const first=new Engine();let count=0;
  const controller=new MatchController(()=>{
    if (++count===2) throw new Error("Second worker failed");
    return first;
  });
  controller.newGame();
  await until(()=>controller.snapshot().phase==="error");
  assert.equal(first.stopped,true);assert.equal(controller.running,false);
  controller.close();
});
test("turning auto-next off during intermission prevents a new game",async()=>{
  const engines=[],controller=new MatchController(()=>{const e=new Engine();engines.push(e);return e;});
  controller.newGame({paceMs:0,maxPlies:1,intermissionMs:20,autoNext:true});
  await until(()=>engines[0]?.release);engines[0].release();
  await until(()=>controller.snapshot().phase==="finished");
  controller.settings.autoNext=false;
  await until(()=>controller.running===false);
  assert.equal(controller.gameNumber,1);controller.close();
});
