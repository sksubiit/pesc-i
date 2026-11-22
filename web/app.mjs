import {boardCells,formatEvaluation} from "./view.mjs";
import {MatchController,DEFAULTS} from "./match.mjs";
import {UciEngine} from "./uci.mjs";
import {ENABLED} from "./config.mjs";

const $=id=>document.getElementById(id);
const glyph={k:"♚",q:"♛",r:"♜",b:"♝",n:"♞",p:"♟"};
const initial="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
let controller, flipped=false, lastState=null;

function drawBoard(fen,last) {
  const fragment=document.createDocumentFragment();
  for (const cell of boardCells(fen,flipped)) {
    const node=document.createElement("div");
    node.className="square "+(cell.light ? "light" : "dark");
    if (last && [last.slice(0,2),last.slice(2,4)].includes(cell.name)) node.classList.add("last");
    if (cell.piece) {
      const piece=document.createElement("span");
      piece.className="piece "+(cell.piece===cell.piece.toUpperCase() ? "white" : "black");
      piece.textContent=glyph[cell.piece.toLowerCase()]; node.append(piece);
    }
    if (cell.rankLabel) {
      const label=document.createElement("span");label.className="coordinate rank";
      label.textContent=cell.rank;node.append(label);
    }
    if (cell.fileLabel) {
      const label=document.createElement("span");label.className="coordinate file";
      label.textContent="abcdefgh"[cell.file];node.append(label);
    }
    fragment.append(node);
  }
  $("board").replaceChildren(fragment);
  $("board").setAttribute("aria-label","Chess position. FEN: "+fen);
}
function drawMoves(moves) {
  const fragment=document.createDocumentFragment();
  let row,white,black;
  for (let i=0;i<moves.length;i++) {
    const move=moves[i];
    if (!row || row.dataset.number!==String(move.number)) {
      row=document.createElement("li");row.dataset.number=move.number;
      const number=document.createElement("span");number.className="number";number.textContent=move.number+".";
      white=document.createElement("span");black=document.createElement("span");
      row.append(number,white,black);fragment.append(row);
    }
    const cell=move.side==="white" ? white : black;
    cell.textContent=move.san;
    if (i===moves.length-1) cell.className="current";
  }
  $("moves").replaceChildren(fragment);$("moves").scrollTop=$("moves").scrollHeight;
}
function render(state) {
  lastState=state;
  drawBoard(state.fen,state.lastMove?.uci);drawMoves(state.moves);
  $("white-name").textContent=state.players.white;$("black-name").textContent=state.players.black;
  $("pause").disabled=false;$("new").disabled=false;
  $("pause").textContent=state.running ? "Pause" : state.outcome ? "Play again" : "Resume";
  $("connection").textContent=state.phase==="error" ? "Engine error" : state.running ? "Browser live" : "Paused";
  $("turn").textContent=state.outcome ? state.outcome.message : state.turn+" to move"+(state.check ? " · Check." : ".");
  $("detail").textContent="Game "+state.gameNumber+" · this browser session";
  $("last").textContent=state.lastMove ?
    state.lastMove.number+(state.lastMove.side==="white" ? ". " : "… ")+state.lastMove.san : "Opening position";
  const score=state.score;
  const evaluation=formatEvaluation(score ? {
    cp:score.type==="cp" ? score.whiteValue : null,
    mate:score.type==="mate" ? score.whiteValue : null
  } : null);
  if (state.outcome && state.outcome.result!=="*") {
    evaluation.text=state.outcome.result;
    evaluation.percent=state.outcome.result==="1-0" ? 96 : state.outcome.result==="0-1" ? 4 : 50;
  }
  $("eval").textContent=evaluation.text;$("fill").style.width=evaluation.percent+"%";
  $("note").textContent=state.check ? "The king is in check." : "One position. Many possibilities.";
  $("status").textContent=state.status;
}
function settings() {
  return {...DEFAULTS,white:$("white").value,black:$("black").value,
    thinkMs:Number($("think").value),paceMs:Number($("pace").value),autoNext:$("auto").checked};
}
$("pause").addEventListener("click",()=>{
  if (!controller) return;
  if (controller.running) controller.pause();
  else if (lastState.outcome || lastState.phase==="error") controller.newGame(settings());
  else controller.start();
});
$("new").addEventListener("click",()=>controller?.newGame(settings()));
$("flip").addEventListener("click",()=>{
  flipped=!flipped;
  drawBoard(lastState?.fen||initial,lastState?.lastMove?.uci);
});
$("auto").addEventListener("change",()=>{if (controller) controller.settings.autoNext=$("auto").checked;});
$("pgn").addEventListener("click",event=>{
  event.preventDefault();if (!controller) return;
  const url=URL.createObjectURL(new Blob([controller.pgn()],{type:"application/x-chess-pgn"}));
  const link=document.createElement("a");link.href=url;link.download="pesc-i.pgn";link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
document.addEventListener("visibilitychange",()=>{
  if (document.hidden) controller?.pause("Tab hidden. Both engines are off; Resume to continue.");
});
window.addEventListener("pagehide",()=>controller?.pause());
drawBoard(initial,null);
async function launch() {
  if (!ENABLED) {
    $("board-message").hidden=false;$("board-message").textContent="The demo is currently switched off.";
    $("connection").textContent="Off";$("turn").textContent="The board is resting.";
    $("status").textContent="The repository owner has disabled this demo. No engines are running.";
    return;
  }
  try {
    const response=await fetch("./vendor/manifest.json");
    if (!response.ok) throw new Error("Missing browser assets. Run npm ci and npm run build:web.");
    const manifest=await response.json();
    const engineUrl=new URL("./vendor/"+manifest.engine,import.meta.url);
    controller=new MatchController(()=>new UciEngine(engineUrl),{onChange:render});
    controller.newGame(settings());
    if (document.hidden) controller.pause("Tab hidden. Both engines are off; Resume to continue.");
  } catch (error) {
    $("connection").textContent="Setup needed";$("turn").textContent="The engines could not start.";
    $("status").textContent=error.message+" Serve the web folder over HTTP, not file://.";
  }
}
void launch();
