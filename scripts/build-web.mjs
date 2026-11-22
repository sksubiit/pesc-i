import {createHash} from "node:crypto";
import {createRequire} from "node:module";
import {copyFile, mkdir, readFile, writeFile, access} from "node:fs/promises";
import {dirname, join, resolve} from "node:path";
import {fileURLToPath} from "node:url";

const require=createRequire(import.meta.url);
const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const vendor=join(root,"web/vendor"), engines=join(vendor,"stockfish");
const cache=join(root,"node_modules/.cache/pesc-i");
await mkdir(engines,{recursive:true}); await mkdir(cache,{recursive:true});
const sfRoot=dirname(require.resolve("stockfish"));
const sfPackage=JSON.parse(await readFile(join(sfRoot,"package.json"),"utf8"));
if (sfPackage.version!=="19.0.1") throw new Error("Unexpected Stockfish package version.");
const engine=require("stockfish").findEngine("lite-single");
const engineFile=engine.split(/[\\/]/).at(-1);
await copyFile(engine,join(engines,engineFile));
await copyFile(engine.replace(/\.js$/,".wasm"),join(engines,engineFile.replace(/\.js$/,".wasm")));
await copyFile(join(sfRoot,"Copying.txt"),join(engines,"COPYING.txt"));
const chessRoot=resolve(dirname(require.resolve("chess.js")),"../..");
await copyFile(join(chessRoot,"dist/esm/chess.js"),join(vendor,"chess.mjs"));
await copyFile(join(chessRoot,"LICENSE"),join(vendor,"chess-LICENSE.txt"));

const sourceCommit="0d5dd7944f88c817c07a26bc4fb1905d5f9c46d6";
const files=[
  {name:"stockfish-source.tar.gz",
   url:"https://codeload.github.com/nmrugg/stockfish.js/tar.gz/"+sourceCommit,
   sha:"e5289a920554bf0069a6601c228e81d957c00522bb31c4343588dc5d7d251879"},
  {name:"nn-61e7af4bb97d.nnue",
   url:"https://tests.stockfishchess.org/api/nn/nn-61e7af4bb97d.nnue?download=1",
   sha:"61e7af4bb97d51eeeb25d322916f86513b5cd3a827ce189c98c6e31946f99e5b"}
];
const sha=bytes=>createHash("sha256").update(bytes).digest("hex");
for (const file of files) {
  const cached=join(cache,file.name);
  try {await access(cached);} catch {
    const downloadUrl=file.name.endsWith(".nnue") ? file.url+"&cache="+Date.now() : file.url;
    const response=await fetch(downloadUrl,{signal:AbortSignal.timeout(60000)});
    if (!response.ok) throw new Error("Source download failed: HTTP "+response.status);
    const bytes=Buffer.from(await response.arrayBuffer());
    if (sha(bytes)!==file.sha) throw new Error("Source checksum mismatch: "+file.name);
    await writeFile(cached,bytes);
  }
  const bytes=await readFile(cached);
  if (sha(bytes)!==file.sha) throw new Error("Cached source checksum mismatch: "+file.name);
  await copyFile(cached,join(engines,file.name));
}
const manifest={
  version:sfPackage.version,name:"Stockfish 19 Lite WASM",
  engine:"stockfish/"+engineFile,sourceCommit,
  engineSha256:sha(await readFile(engine)),
  wasmSha256:sha(await readFile(engine.replace(/\.js$/,".wasm"))),
  sources:files.map(({name,sha})=>({name,sha256:sha})),
  chessVersion:"1.4.0"
};
await writeFile(join(vendor,"manifest.json"),JSON.stringify(manifest,null,2)+"\n");
await writeFile(join(vendor,"sources.html"),[
  '<!doctype html><html lang="en"><meta charset="utf-8"><title>Engine source and licenses</title>',
  '<h1>Browser engine source and licenses</h1>',
  '<p>PESC-I original code uses BSD-3-Clause. The engine retains GPLv3.</p>',
  '<p>Engine: stockfish npm 19.0.1, lite single-threaded build. The desktop binary is separate.</p>',
  '<ul><li><a href="stockfish/COPYING.txt">Stockfish GPLv3 license</a></li>',
  '<li><a href="stockfish/stockfish-source.tar.gz">Corresponding upstream source and build scripts</a> (commit '+sourceCommit+')</li>',
  '<li><a href="stockfish/nn-61e7af4bb97d.nnue">Embedded lite neural network</a></li>',
  '<li><a href="chess-LICENSE.txt">chess.js 1.4.0 BSD-2-Clause license</a></li>',
  '<li><a href="manifest.json">Artifact SHA-256 checksums and provenance</a></li></ul>',
  '<p>Unpack the source, place the network in src/, and follow its README build instructions.',
  'The upstream build uses Emscripten and build.js --single-threaded --lite.</p>',
  '<p><a href="../">Return to the board</a></p></html>'
].join("\n"));
await writeFile(join(root,"web/.nojekyll"),"");
console.log("Built browser assets: "+manifest.name+"; verified corresponding source and network included.");
