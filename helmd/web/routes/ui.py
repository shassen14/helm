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
  h2 { margin: 1.25rem 0 .5rem; font-size: 1rem; color: #333; }
  .channel { border: 1px solid #ccc; border-radius: 6px; padding: .75rem 1rem; margin-bottom: .75rem; }
  .row { display: flex; align-items: center; gap: .75rem; margin: .25rem 0; }
  .name { font-weight: 600; min-width: 7rem; }
  .kind { color: #777; font-size: .8rem; font-weight: normal; margin-left: .35rem; }
  .level { flex: 1; }
  .outputs label { margin-right: .75rem; font-size: .9rem; }
  .remove { margin-left: auto; background: none; border: 1px solid #ccc; border-radius: 4px; padding: .15rem .5rem; cursor: pointer; font-size: .8rem; }
  .remove:hover { background: #fee; border-color: #b00; color: #b00; }
  .add { display: flex; gap: .5rem; align-items: center; }
  .add select { flex: 1; padding: .35rem; }
  .add button { padding: .35rem .75rem; cursor: pointer; }
  footer { margin-top: 1.5rem; padding-top: .75rem; border-top: 1px solid #ddd; color: #555; font-size: .85rem; }
  .err { color: #b00; }
</style>
</head>
<body>
<h1>mixer</h1>
<div id="channels">loading…</div>

<h2>add channel</h2>
<div class="add">
  <select id="add-source"><option value="">loading apps…</option></select>
  <button id="add-btn">add</button>
</div>

<footer id="footer">connecting to mixd…</footer>

<script>
const OUTPUTS = ["stream", "monitor", "chat"];
const POLL_MS = 2000;
const LEVEL_DEBOUNCE_MS = 80;

const levelTimers = {};
let appsCache = [];

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["content-type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(path, opts);
  if (!r.ok) {
    let detail = `${method} ${path} → ${r.status}`;
    try { const j = await r.json(); if (j.detail) detail += `: ${j.detail}`; } catch (_) {}
    throw new Error(detail);
  }
  if (r.status === 204) return null;
  return r.json();
}

function renderChannels(channels) {
  const root = document.getElementById("channels");
  root.innerHTML = "";
  const ids = Object.keys(channels).sort((a, b) => channels[a].slot - channels[b].slot);
  if (!ids.length) {
    root.textContent = "no channels yet — add one below";
    return;
  }
  for (const id of ids) {
    const ch = channels[id];
    const card = document.createElement("div");
    card.className = "channel";
    card.dataset.channel = id;

    const top = document.createElement("div");
    top.className = "row";
    const label = document.createElement("span");
    label.className = "name";
    label.textContent = ch.name;
    const kindTag = document.createElement("span");
    kindTag.className = "kind";
    kindTag.textContent = ch.kind;
    label.append(kindTag);
    top.append(label);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = 0; slider.max = 1; slider.step = 0.01;
    slider.value = ch.level;
    slider.className = "level";
    slider.addEventListener("input", () => {
      clearTimeout(levelTimers[id]);
      levelTimers[id] = setTimeout(async () => {
        try { await api("POST", `/mixer/channels/${encodeURIComponent(id)}/level`, { level: parseFloat(slider.value) }); }
        catch (e) { setFooter(`level failed: ${e.message}`, true); }
      }, LEVEL_DEBOUNCE_MS);
    });
    top.append(slider);

    const muteLbl = document.createElement("label");
    const muteBox = document.createElement("input");
    muteBox.type = "checkbox";
    muteBox.checked = !!ch.muted;
    muteBox.addEventListener("change", async () => {
      try { await api("POST", `/mixer/channels/${encodeURIComponent(id)}/mute`, { muted: muteBox.checked }); }
      catch (e) { setFooter(`mute failed: ${e.message}`, true); }
    });
    muteLbl.append(muteBox, " mute");
    top.append(muteLbl);

    const removeBtn = document.createElement("button");
    removeBtn.className = "remove";
    removeBtn.textContent = "remove";
    removeBtn.addEventListener("click", async () => {
      try {
        await api("DELETE", `/mixer/channels/${encodeURIComponent(id)}`);
        await refresh();
      } catch (e) { setFooter(`remove failed: ${e.message}`, true); }
    });
    top.append(removeBtn);
    card.append(top);

    const outRow = document.createElement("div");
    outRow.className = "row outputs";
    const current = new Set(ch.outputs || []);
    for (const out of OUTPUTS) {
      const lbl = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = current.has(out);
      box.addEventListener("change", async () => {
        const boxes = outRow.querySelectorAll("input[type=checkbox]");
        const outs = [];
        boxes.forEach((b, i) => { if (b.checked) outs.push(OUTPUTS[i]); });
        try { await api("PUT", `/mixer/routing/${encodeURIComponent(id)}`, { outputs: outs }); }
        catch (e) { setFooter(`routing failed: ${e.message}`, true); }
      });
      lbl.append(box, " " + out);
      outRow.append(lbl);
    }
    card.append(outRow);
    root.append(card);
  }
}

function computeAddOptions(apps, existingIds) {
  const opts = [];
  if (!existingIds.has("mic")) opts.push({ value: "mic", label: "Mic (input device)" });
  if (!existingIds.has("system")) opts.push({ value: "system", label: "System (full mix)" });
  for (const a of apps) {
    if (!existingIds.has(a.bundleIdentifier)) {
      opts.push({ value: `app:${a.bundleIdentifier}`, label: `${a.applicationName} (${a.bundleIdentifier})` });
    }
  }
  return opts;
}

function renderAddOptions(apps, existingIds) {
  const sel = document.getElementById("add-source");
  const opts = computeAddOptions(apps, existingIds);
  const newSig = opts.map(o => o.value).join("|");
  // Skip rebuild when nothing changed — otherwise the 2 s poll wipes the
  // user's pending selection before they click "add".
  if (sel.dataset.sig === newSig) return;
  sel.dataset.sig = newSig;
  const prev = sel.value;
  sel.innerHTML = "";
  if (!opts.length) {
    sel.innerHTML = "<option value=''>nothing left to add</option>";
    return;
  }
  for (const o of opts) {
    const el = document.createElement("option");
    el.value = o.value;
    el.textContent = o.label;
    sel.append(el);
  }
  if (prev && opts.some(o => o.value === prev)) sel.value = prev;
}

async function addChannel() {
  const sel = document.getElementById("add-source");
  const v = sel.value;
  if (!v) return;
  let body;
  if (v === "mic") body = { kind: "mic", outputs: ["stream", "monitor"] };
  else if (v === "system") body = { kind: "system", outputs: ["stream", "monitor"] };
  else if (v.startsWith("app:")) body = { kind: "app", bundle_id: v.slice(4), outputs: ["stream"] };
  else return;
  try {
    await api("POST", "/mixer/channels", body);
    await refresh();
  } catch (e) { setFooter(`add failed: ${e.message}`, true); }
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
    renderAddOptions(appsCache, new Set(Object.keys(channels)));
    setFooter(`mixd ok · ${Object.keys(channels).length} channels`);
  } catch (e) {
    setFooter("mixd unreachable", true);
  }
}

async function init() {
  try { appsCache = await api("GET", "/mixer/apps"); }
  catch (e) { appsCache = []; setFooter(`apps unavailable: ${e.message}`, true); }
  document.getElementById("add-btn").addEventListener("click", addChannel);
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
