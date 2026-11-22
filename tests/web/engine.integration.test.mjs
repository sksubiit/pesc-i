// Runs the exact browser WASM engine in Node, using stdin/stdout as the transport.
import test from "node:test";
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {createRequire} from "node:module";
import {Chess} from "../../web/vendor/chess.mjs";
import {UciEngine} from "../../web/uci.mjs";
import {MatchController} from "../../web/match.mjs";
const require=createRequire(import.meta.url);
const path=require("stockfish").findEngine("lite-single");
class NodeWorker {
  constructor(){
    this.child=spawn(process.execPath,[path],{stdio:["pipe","pipe","pipe"]});
    this.lines=createInterface({input:this.child.stdout});
    this.lines.on("line",line=>this.onmessage?.({data:line}));
    this.child.on("error",error=>this.onerror?.(error));
    this.child.on("exit",code=>{if(!this.stopped && code!==0) this.onerror?.(new Error("Engine exited"));});
    this.child.stderr.resume();
  }
  postMessage(command){this.child.stdin.write(command+"\n");}
  terminate(){this.stopped=true;this.lines.close();this.child.kill();}
}
const engine=()=>new UciEngine(path,{workerFactory:()=>new NodeWorker()});
test("the browser WASM engine completes five legal games and rematches", {timeout:180000},async()=>{
  const results=[];
  await new Promise((resolve,reject)=>{
    const controller=new MatchController(engine,{onChange:state=>{
      if(state.phase==="error"){controller.close();reject(new Error(state.status));return;}
      if(state.phase!=="finished" || results.some(r=>r.number===state.gameNumber)) return;
      try {
        const check=new Chess();
        for(const move of state.moves) check.move(move.san);
        assert.equal(check.fen(),state.fen);
        assert.notEqual(state.outcome.result,"*","Expected a natural game ending");
        assert.equal(check.isGameOver(),true);
        results.push({number:state.gameNumber,result:state.outcome.result,plies:state.moves.length});
        console.log("WASM game",state.gameNumber,state.outcome.message,state.moves.length,"plies");
        if(results.length===5){controller.pause();controller.close();resolve();}
      } catch(error){controller.close();reject(error);}
    }});
    controller.newGame({thinkMs:10,paceMs:0,maxPlies:1000,intermissionMs:10,autoNext:true});
  });
  assert.equal(results.length,5);
});
