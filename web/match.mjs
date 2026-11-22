import {Chess} from "./vendor/chess.mjs";
import {EngineStopped} from "./uci.mjs";

export const DEFAULTS=Object.freeze({
  white:"full", black:"full", thinkMs:200, paceMs:900, autoNext:true,
  maxPlies:300, intermissionMs:4000
});
export function resultOf(game,maxPlies) {
  if (game.isCheckmate()) return {
    result:game.turn()==="w" ? "0-1" : "1-0",
    message:"Checkmate · "+(game.turn()==="w" ? "Black" : "White")+" wins."
  };
  if (game.isStalemate()) return {result:"1/2-1/2",message:"Draw · stalemate."};
  if (game.isThreefoldRepetition()) return {result:"1/2-1/2",message:"Draw · threefold repetition."};
  if (game.isInsufficientMaterial()) return {result:"1/2-1/2",message:"Draw · insufficient material."};
  if (game.isDraw()) return {result:"1/2-1/2",message:"Draw · fifty-move rule."};
  if (game.history().length>=maxPlies) return {result:"*",message:"Move limit reached · unfinished game."};
  return null;
}
export class MatchController {
  constructor(engineFactory,{onChange=()=>{}}={}) {
    this.engineFactory=engineFactory; this.onChange=onChange;
    this.game=new Chess(); this.settings={...DEFAULTS}; this.engines=[];
    this.running=false; this.generation=0; this.gameNumber=0;
    this.status="Ready. Start a game when you like."; this.phase="ready";
    this.score=null; this.players={white:"Stockfish",black:"Stockfish"};
    this.timer=null; this.releaseWait=null;
  }
  emit() {this.onChange(this.snapshot());}
  snapshot() {
    const moves=this.game.history({verbose:true}).map((m,i)=>({
      san:m.san,uci:m.from+m.to+(m.promotion||""),number:Math.floor(i/2)+1,
      side:m.color==="w" ? "white" : "black"
    }));
    return {fen:this.game.fen(),moves,lastMove:moves.at(-1)||null,
      turn:this.game.turn()==="w" ? "White" : "Black",check:this.game.isCheck(),
      running:this.running,phase:this.phase,status:this.status,score:this.score,
      players:{...this.players},gameNumber:this.gameNumber,
      outcome:resultOf(this.game,this.settings.maxPlies)};
  }
  cancel() {
    this.generation++;
    clearTimeout(this.timer); this.timer=null;
    if (this.releaseWait) {this.releaseWait(); this.releaseWait=null;}
    for (const engine of this.engines) engine.stop();
    this.engines=[];
  }
  pause(message="Paused. Both engine workers are off.") {
    if (!this.running) return;
    this.cancel(); this.running=false; this.phase="paused"; this.status=message; this.emit();
  }
  close() {this.cancel(); this.running=false; this.phase="stopped";}
  newGame(settings=this.settings) {
    this.cancel(); this.running=false;
    this.settings={...DEFAULTS,...settings};
    this.game=new Chess(); this.gameNumber++; this.score=null;
    this.players={white:"Stockfish",black:"Stockfish"};
    this.start();
  }
  start() {
    if (this.running) return;
    this.running=true; this.phase="starting";
    this.status="Loading two browser engines…";
    const generation=++this.generation;
    this.emit();
    void this.run(generation);
  }
  wait(milliseconds) {
    return new Promise(resolve=>{
      this.releaseWait=resolve;
      this.timer=setTimeout(()=>{this.releaseWait=null; this.timer=null; resolve();},milliseconds);
    });
  }
  async run(generation) {
    try {
      if (generation!==this.generation) return;
      const white=this.engineFactory(); this.engines.push(white);
      const black=this.engineFactory(); this.engines.push(black);
      const names=await Promise.all([white.init(this.settings.white),black.init(this.settings.black)]);
      if (generation!==this.generation) return;
      this.players={white:names[0],black:names[1]};
      while (this.running && generation===this.generation) {
        const outcome=resultOf(this.game,this.settings.maxPlies);
        if (outcome) {
          this.game.header("Result",outcome.result);
          this.phase="finished"; this.status=outcome.message;
          if (this.settings.autoNext) this.status+=" Next game shortly.";
          this.emit();
          if (generation!==this.generation) return;
          // Release engine memory during intermissions and after the final game.
          white.stop(); black.stop(); this.engines=[];
          if (!this.settings.autoNext) {this.running=false; this.emit(); return;}
          await this.wait(this.settings.intermissionMs);
          if (generation===this.generation && this.running) {
            if (this.settings.autoNext) this.newGame(this.settings);
            else {this.running=false; this.status=outcome.message; this.emit();}
          }
          return;
        }
        const turn=this.game.turn(), engine=turn==="w" ? white : black;
        this.phase="thinking"; this.status=(turn==="w" ? "White" : "Black")+" is thinking…"; this.emit();
        const moves=this.game.history({verbose:true}).map(m=>m.from+m.to+(m.promotion||""));
        const result=await engine.bestMove(moves,this.settings.thinkMs);
        if (generation!==this.generation || !this.running) return;
        if (!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(result.uci||""))
          throw new Error("The engine did not return a legal move.");
        try {this.game.move({from:result.uci.slice(0,2),to:result.uci.slice(2,4),promotion:result.uci[4]});}
        catch {throw new Error("The engine returned an illegal move. Try New game.");}
        this.score=result.score ? {...result.score,whiteValue:result.score.value*(turn==="w" ? 1 : -1)} : null;
        this.phase="playing"; this.status="Playing in your browser · no server or API calls."; this.emit();
        if (generation!==this.generation) return;
        await this.wait(this.settings.paceMs);
      }
    } catch (error) {
      if (generation!==this.generation) return;
      this.cancel(); this.running=false; this.phase="error";
      this.status=error instanceof EngineStopped ? "Engines stopped." : error.message;
      this.emit();
    }
  }
  pgn() {
    this.game.header("Event","PESC-I browser self-play","White",this.players.white,
      "Black",this.players.black,"Result",resultOf(this.game,this.settings.maxPlies)?.result || "*");
    return this.game.pgn()+"\n";
  }
}
