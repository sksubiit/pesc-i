import test from "node:test";
import assert from "node:assert/strict";
import {UciEngine,EngineStopped,parseScore} from "../../web/uci.mjs";

class Worker {
  constructor(){this.commands=[];this.terminated=false;this.reply=true;}
  postMessage(command) {
    this.commands.push(command);
    const emit=line=>this.onmessage({data:line});
    if(command==="uci" && this.reply) {
      emit("id name Test engine");
      emit("option name Hash type spin default 16 min 1 max 1024");
      emit("option name UCI_LimitStrength type check default false");
      emit("option name UCI_Elo type spin default 1320 min 1320 max 3190");
      emit("uciok");
    }
    if(command==="isready") emit("readyok");
    if(command.startsWith("go") && this.reply) {
      emit("info depth 8 score cp 35 nodes 100");
      emit("bestmove e2e4 ponder e7e5");
    }
  }
  terminate(){this.terminated=true;}
}
test("UCI listeners are registered before even synchronous responses",async()=>{
  const worker=new Worker(),engine=new UciEngine("test",{workerFactory:()=>worker});
  assert.equal(await engine.init("1500"),"Test engine");
  assert.ok(worker.commands.includes("setoption name UCI_Elo value 1500"));
  const result=await engine.bestMove(["d2d4","d7d5"],20);
  assert.equal(result.uci,"e2e4");
  assert.deepEqual(result.score,{type:"cp",value:35});
  assert.ok(worker.commands.includes("position startpos moves d2d4 d7d5"));
  engine.stop();assert.equal(worker.terminated,true);
});
test("unsupported strength settings fail instead of pretending they worked",async()=>{
  const engine=new UciEngine("test",{workerFactory:()=>new Worker()});
  await assert.rejects(engine.init("100"),/not supported/);engine.stop();
});
test("stopping terminates workers and rejects pending searches",async()=>{
  const worker=new Worker(),engine=new UciEngine("test",{workerFactory:()=>worker});
  await engine.init();worker.reply=false;
  const search=engine.bestMove([],20);
  engine.stop();
  await assert.rejects(search,EngineStopped);
  assert.equal(engine.waiters.size,0);
});
test("startup timeout is visible and cleans up the worker",async()=>{
  const worker=new Worker();worker.reply=false;
  const engine=new UciEngine("test",{workerFactory:()=>worker,startupTimeout:10});
  await assert.rejects(engine.init(),/did not respond/);
  assert.equal(worker.terminated,true);
});
test("search bounds and alternate PV scores do not overwrite the main score",()=>{
  assert.deepEqual(parseScore("info score mate -3"),{type:"mate",value:-3});
  assert.equal(parseScore("info multipv 2 score cp 99"),null);
  assert.equal(parseScore("info multipv 10 score cp 99"),null);
  assert.equal(parseScore("info score cp 99 lowerbound"),null);
});
