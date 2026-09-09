from __future__ import annotations

import json
from pathlib import Path

from .perception import PALETTE


def render_replay(directory: Path):
    events = [
        json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines() if line.strip()
    ]
    result = json.loads((directory / "result.json").read_text())
    frames = [e["data"] for e in events if e["kind"] == "observation"]
    transitions = [e["data"] for e in events if e["kind"] == "transition"]
    data = json.dumps({"result": result, "frames": frames, "transitions": transitions, "palette": PALETTE})
    # Escape script delimiters even when model-generated evidence includes arbitrary text.
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = TEMPLATE.replace("__DATA__", data)
    path = directory / "replay.html"
    path.write_text(html, encoding="utf-8")
    return path


TEMPLATE = r"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARC Harness · Experiment replay</title>
<style>
:root{color-scheme:dark;font-family:ui-sans-serif,system-ui,sans-serif;background:#111513;color:#e8eee7}
*{box-sizing:border-box}body{max-width:1180px;margin:0 auto;padding:40px 28px}header{display:flex;justify-content:space-between;gap:24px;align-items:start;border-bottom:1px solid #354036;padding-bottom:24px}
.eyebrow{font:12px ui-monospace,monospace;letter-spacing:2px;color:#aabd9b}h1{font-size:36px;font-weight:500;margin:10px 0}p{color:#aab7aa;line-height:1.6}.pill{padding:8px 14px;border:1px solid #45573c;border-radius:20px;white-space:nowrap;color:#d2eabf;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:28px 0}.stat{padding:16px;border:1px solid #354036;border-radius:10px}.stat span{display:block;color:#8d9a8d;font-size:12px;margin-bottom:7px}.stat b{font:24px ui-monospace,monospace;font-weight:400}
main{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:28px}canvas{display:block;image-rendering:pixelated;width:100%;aspect-ratio:1;object-fit:contain;background:#080a08;border:1px solid #354036;border-radius:8px}aside{min-width:0}h2{font-size:15px;font-weight:500;color:#c5d6bd}.controls{display:flex;gap:12px;align-items:center;margin:18px 0}button{background:#263123;border:1px solid #516448;border-radius:6px;color:#e3efdd;padding:10px 14px;cursor:pointer}button:disabled{opacity:.4;cursor:default}input{width:100%;accent-color:#b6da91}pre{font:12px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#192019;border:1px solid #354036;border-radius:8px;padding:14px;max-height:300px;overflow:auto}.muted{color:#8c9a89;font-size:12px}#coords{font:12px ui-monospace,monospace;height:20px}footer{border-top:1px solid #354036;margin-top:28px;padding-top:16px;color:#8c9a89;font-size:12px;line-height:1.7}
@media(max-width:720px){body{padding:24px 16px}main{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}header{display:block}.pill{display:inline-block}h1{font-size:28px}}
</style>
<header><div><div class="eyebrow">ARC HARNESS / EXPERIMENT LOG</div><h1 id="title"></h1><p>Observe. Form a hypothesis. Act. Verify.</p></div><span class="pill" id="status"></span></header>
<div class="stats"><div class="stat"><span>Levels completed</span><b id="levels"></b></div><div class="stat"><span>Actions submitted</span><b id="actions"></b></div><div class="stat"><span>Model calls</span><b id="calls"></b></div><div class="stat"><span>Prediction failures</span><b id="failures"></b></div></div>
<main><section><canvas id="board" width="512" height="512" aria-label="Observed game frame"></canvas><div class="controls"><button id="prev" aria-label="Previous frame">←</button><input id="scrub" aria-label="Observation" type="range" min="0" value="0"><button id="next" aria-label="Next frame">→</button><button id="play">Play</button></div><div id="coords"></div><p class="muted" id="frameLabel"></p></section><aside><h2>Experiment</h2><p id="experiment"></p><h2>Prediction check</h2><pre id="prediction"></pre><h2>Observed changes</h2><pre id="delta"></pre></aside></main>
<footer id="footer"></footer>
<script type="application/json" id="data">__DATA__</script>
<script>
const d=JSON.parse(document.getElementById('data').textContent),r=d.result,$=id=>document.getElementById(id),slider=$('scrub'),canvas=$('board'),ctx=canvas.getContext('2d');let timer=null;
$('title').textContent=r.game_id;$('status').textContent=r.won?'Environment reports WIN':r.status;$('levels').textContent=`${r.levels_completed} / ${r.win_levels??'?'}`;$('actions').textContent=r.actions_submitted;$('calls').textContent=r.model_calls;$('failures').textContent=r.prediction_failures;slider.max=Math.max(0,d.frames.length-1);
$('footer').textContent=`Model: ${r.model} · Reasoning: ${r.effort} · ${r.elapsed_seconds}s · ${r.input_tokens+r.output_tokens} reported tokens. This is an individual research run, not a verified ARC-AGI-3 benchmark score. ${r.error||''}`;
function draw(){let i=Number(slider.value),o=d.frames[i],t=d.transitions[i-1];ctx.clearRect(0,0,512,512);if(!o){$('experiment').textContent='No observation was received.';return}let g=o.frames.at(-1),h=g.length,w=g[0].length;g.forEach((row,y)=>row.forEach((c,x)=>{ctx.fillStyle=d.palette[c];ctx.fillRect(x*512/w,y*512/h,Math.ceil(512/w),Math.ceil(512/h))}));$('experiment').textContent=t?t.experiment:'Initial observation. No action has been taken.';$('prediction').textContent=t?JSON.stringify(t.prediction,null,2):'—';$('delta').textContent=t?JSON.stringify(t.delta,null,2):'—';$('frameLabel').textContent=`Observation ${i} of ${d.frames.length-1} · ${o.state} · ${o.animation_frames} animation frame(s) · ${o.state_hash.slice(0,16)}`;$('prev').disabled=i===0;$('next').disabled=i===d.frames.length-1}
slider.addEventListener('input',draw);$('prev').onclick=()=>{slider.value=Math.max(0,Number(slider.value)-1);draw()};$('next').onclick=()=>{slider.value=Math.min(Number(slider.max),Number(slider.value)+1);draw()};$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='Play';return}if(slider.value===slider.max)slider.value=0;$('play').textContent='Pause';timer=setInterval(()=>{if(slider.value===slider.max){$('play').click();return}$('next').click()},700)};
canvas.addEventListener('mousemove',e=>{const o=d.frames[Number(slider.value)];if(!o)return;const g=o.frames.at(-1),b=canvas.getBoundingClientRect(),x=Math.min(g[0].length-1,Math.max(0,Math.floor((e.clientX-b.left)/b.width*g[0].length))),y=Math.min(g.length-1,Math.max(0,Math.floor((e.clientY-b.top)/b.height*g.length)));$('coords').textContent=`x ${x} · y ${y} · color ${g[y][x]}`});document.addEventListener('keydown',e=>{if(e.target===slider)return;if(e.key==='ArrowRight')$('next').click();if(e.key==='ArrowLeft')$('prev').click()});draw();
</script></html>"""
