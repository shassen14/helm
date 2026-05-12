from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>helmd</title></head>
<body>
<h1>helmd dashboard</h1>
<ul>
  <li><a href="/status">/status</a></li>
  <li><a href="/profiles">/profiles</a></li>
  <li><a href="/mixer">/mixer</a></li>
</ul>
</body>
</html>"""

_MIXER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>helmd · mixer</title>
<style>
  body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 1.5rem; max-width: 720px; }
  h1 { margin: 0 0 1rem; font-size: 1.25rem; }
  .channel { border: 1px solid #ccc; border-radius: 6px; padding: .75rem 1rem; margin-bottom: .75rem; }
  .row { display: flex; align-items: center; gap: .75rem; margin: .25rem 0; }
  .name { font-weight: 600; min-width: 7rem; }
  .level { flex: 1; }
  .outputs label { margin-right: .75rem; font-size: .9rem; }
  footer { margin-top: 1.5rem; padding-top: .75rem; border-top: 1px solid #ddd; color: #555; font-size: .85rem; }
  .err { color: #b00; }
</style>
</head>
<body>
<h1>mixer</h1>
<div id="channels">loading…</div>
<footer id="footer">connecting to mixd…</footer>

<script>
const BASELINE_OUTPUTS = ["stream", "monitor", "chat"];
const POLL_MS = 2000;
const LEVEL_DEBOUNCE_MS = 80;

let outputNames = [...BASELINE_OUTPUTS];
const levelTimers = {};

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["content-type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status}`);
  return r.json();
}

function unionOutputs(routing) {
  const s = new Set(BASELINE_OUTPUTS);
  for (const outs of Object.values(routing || {})) {
    for (const o of outs) s.add(o);
  }
  return [...s];
}

function renderChannels(channels) {
  const root = document.getElementById("channels");
  root.innerHTML = "";
  const names = Object.keys(channels).sort();
  if (!names.length) {
    root.textContent = "no channels";
    return;
  }
  for (const name of names) {
    const ch = channels[name];
    const card = document.createElement("div");
    card.className = "channel";
    card.dataset.channel = name;

    const top = document.createElement("div");
    top.className = "row";
    top.innerHTML = `<span class="name">${name}</span>`;

    const muteLbl = document.createElement("label");
    const muteBox = document.createElement("input");
    muteBox.type = "checkbox";
    muteBox.checked = !!ch.muted;
    muteBox.addEventListener("change", async () => {
      try { await api("POST", `/mixer/channels/${name}/mute`, { muted: muteBox.checked }); }
      catch (e) { setFooter(`mute failed: ${e.message}`, true); }
    });
    muteLbl.append(muteBox, " mute");

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = 0; slider.max = 1; slider.step = 0.01;
    slider.value = ch.level;
    slider.className = "level";
    slider.addEventListener("input", () => {
      clearTimeout(levelTimers[name]);
      levelTimers[name] = setTimeout(async () => {
        try { await api("POST", `/mixer/channels/${name}/level`, { level: parseFloat(slider.value) }); }
        catch (e) { setFooter(`level failed: ${e.message}`, true); }
      }, LEVEL_DEBOUNCE_MS);
    });

    top.append(slider, muteLbl);
    card.append(top);

    const outRow = document.createElement("div");
    outRow.className = "row outputs";
    const current = new Set(ch.outputs || []);
    for (const out of outputNames) {
      const lbl = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = current.has(out);
      box.addEventListener("change", async () => {
        const boxes = outRow.querySelectorAll("input[type=checkbox]");
        const outs = [];
        boxes.forEach((b, i) => { if (b.checked) outs.push(outputNames[i]); });
        try { await api("PUT", `/mixer/routing/${name}`, { outputs: outs }); }
        catch (e) { setFooter(`routing failed: ${e.message}`, true); }
      });
      lbl.append(box, " " + out);
      outRow.append(lbl);
    }
    card.append(outRow);
    root.append(card);
  }
}

function setFooter(msg, isErr) {
  const f = document.getElementById("footer");
  f.textContent = msg;
  f.className = isErr ? "err" : "";
}

async function refresh() {
  try {
    const channels = await api("GET", "/mixer/channels");
    renderChannels(channels);
    setFooter(`mixd ok · ${Object.keys(channels).length} channels`);
  } catch (e) {
    setFooter("mixd unreachable", true);
  }
}

async function init() {
  try {
    const routing = await api("GET", "/mixer/routing");
    outputNames = unionOutputs(routing);
  } catch (e) { /* fall back to baseline */ }
  await refresh();
  setInterval(refresh, POLL_MS);
}

init();
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(content=_DASHBOARD_HTML)


@router.get("/mixer", response_class=HTMLResponse)
async def mixer_page() -> HTMLResponse:
    return HTMLResponse(content=_MIXER_HTML)
