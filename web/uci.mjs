// A small UCI adapter. Future browser engines can implement this same interface.
export class EngineStopped extends Error {
  constructor() { super("Engine stopped"); this.name="EngineStopped"; }
}
export function parseScore(line) {
  if (/multipv (?!1(?: |$))/.test(line) || /(?:lowerbound|upperbound)/.test(line)) return null;
  const match=line.match(/\bscore (cp|mate) (-?\d+)/);
  return match ? {type:match[1], value:Number(match[2])} : null;
}
export class UciEngine {
  constructor(url, {workerFactory = url => new Worker(url), startupTimeout = 30000} = {}) {
    this.worker=workerFactory(url);
    this.waiters=new Set(); this.listeners=new Set();
    this.options=new Map(); this.name="Stockfish"; this.closed=false;
    this.startupTimeout=startupTimeout;
    this.worker.onmessage=event=>{
      for (const line of String(event.data).split(/\r?\n/)) this.receive(line);
    };
    this.worker.onerror=()=>{
      this.fail(new Error("Could not load Stockfish. Run npm run build:web and serve the web folder over HTTP."));
    };
    this.worker.onmessageerror=()=>this.fail(new Error("Could not read the engine response."));
  }
  receive(line) {
    if (line.startsWith("id name ")) this.name=line.slice(8);
    const option=line.match(/^option name (.+?) type (\w+)(.*)$/);
    if (option) this.options.set(option[1],{
      type:option[2], min:Number(option[3].match(/ min (-?\d+)/)?.[1]),
      max:Number(option[3].match(/ max (-?\d+)/)?.[1])
    });
    for (const listener of this.listeners) listener(line);
    for (const waiter of [...this.waiters]) {
      if (line.startsWith(waiter.prefix)) {
        clearTimeout(waiter.timer); this.waiters.delete(waiter); waiter.resolve(line);
      }
    }
  }
  fail(error) {
    if (this.closed) return;
    this.closed=true;
    for (const waiter of this.waiters) {clearTimeout(waiter.timer); waiter.reject(error);}
    this.waiters.clear(); this.listeners.clear(); this.worker.terminate();
  }
  stop() { this.fail(new EngineStopped()); }
  send(command) {
    if (this.closed) throw new EngineStopped();
    this.worker.postMessage(command);
  }
  request(command, prefix, timeout) {
    return new Promise((resolve,reject)=>{
      if (this.closed) {reject(new EngineStopped()); return;}
      const waiter={prefix,resolve,reject,timer:null};
      waiter.timer=setTimeout(()=>{
        this.fail(new Error("Stockfish did not respond in time. Try New game or a shorter search."));
      },timeout);
      this.waiters.add(waiter); // Register first: synchronous test workers cannot race this.
      try {this.send(command);} catch (error) {this.fail(error);}
    });
  }
  async init(strength="full") {
    await this.request("uci","uciok",this.startupTimeout);
    if (this.options.has("Hash")) this.send("setoption name Hash value 16");
    if (strength !== "full") {
      const elo=Number(strength), option=this.options.get("UCI_Elo");
      if (!Number.isFinite(elo) || !option || elo<option.min || elo>option.max ||
          !this.options.has("UCI_LimitStrength")) {
        throw new Error("This strength cap is not supported by the selected engine.");
      }
      this.send("setoption name UCI_LimitStrength value true");
      this.send("setoption name UCI_Elo value "+elo);
    } else if (this.options.has("UCI_LimitStrength")) {
      this.send("setoption name UCI_LimitStrength value false");
    }
    this.send("ucinewgame");
    await this.request("isready","readyok",this.startupTimeout);
    return this.name;
  }
  async bestMove(moves, milliseconds) {
    if (!Number.isFinite(milliseconds) || milliseconds<10 || milliseconds>5000)
      throw new Error("Invalid search duration.");
    let score=null;
    const track=line=>{const next=parseScore(line); if (next) score=next;};
    this.listeners.add(track);
    try {
      this.send("position startpos"+(moves.length ? " moves "+moves.join(" ") : ""));
      const line=await this.request("go movetime "+milliseconds,"bestmove ",Math.max(15000,milliseconds+10000));
      return {uci:line.split(/\s+/)[1],score};
    } finally {this.listeners.delete(track);}
  }
}
