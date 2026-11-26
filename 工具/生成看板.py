# -*- coding: utf-8 -*-
r"""生成单文件线索看板：数据\线索台账.jsonl -> 看板\index.html

用法：
    python 工具\生成看板.py
产物不依赖网络与外部资源，可直接双击打开、发微信/邮件，或由静态服务器托管。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LEDGER = BASE / "数据" / "线索台账.jsonl"
OUT = BASE / "看板" / "index.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="./manifest.webmanifest">
<meta name="theme-color" content="#0b3d5c">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="武汉线索">
<link rel="apple-touch-icon" href="./icon-180.png">
<title>武汉诉求线索看板</title>
<style>
  :root{
    --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --bg:#f6f8fb;
    --brand:#0b3d5c; --brand2:#155e85; --red:#c8102e;
    --amber:#b45309; --amber-bg:#fef3c7;
    --orange:#c2410c; --orange-bg:#ffedd5;
    --danger:#b91c1c; --danger-bg:#fee2e2;
    --gray:#475569; --gray-bg:#e2e8f0;
    --green:#15803d; --green-bg:#dcfce7;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.6}
  body.modal-open{overflow:hidden}
  .wrap{max-width:1180px;margin:0 auto;padding:0 20px}
  .hero{background:linear-gradient(135deg,#0b3d5c 0%,#155e85 70%,#1d6f9c 100%);color:#fff;padding:34px 0 28px}
  .kicker{font-size:13px;letter-spacing:.18em;opacity:.8;margin-bottom:6px}
  h1{margin:0 0 6px;font-size:30px;letter-spacing:.02em}
  .sub{margin:0 0 20px;opacity:.86;font-size:14px}
  .stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
  .stat{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:12px 14px}
  .stat b{display:block;font-size:26px;line-height:1.2}
  .stat span{font-size:12px;opacity:.85}
  main{padding:22px 0 8px}
  .toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
  .filters{display:flex;flex-wrap:wrap;gap:10px;align-items:center;flex:1 1 auto}
  .filterToggle{display:none}
  .toolbar input,.toolbar select{height:38px;border:1px solid var(--line);border-radius:9px;padding:0 12px;font-size:14px;background:#fff;color:var(--ink);outline:none}
  .toolbar input{flex:1 1 280px;min-width:220px}
  .toolbar input:focus,.toolbar select:focus{border-color:#7aa8c4;box-shadow:0 0 0 3px rgba(21,94,133,.12)}
  .toolbar button{height:38px;border:1px solid var(--line);border-radius:9px;padding:0 14px;background:#fff;color:var(--muted);cursor:pointer;font-size:14px}
  .toolbar button:hover{color:var(--brand);border-color:#9dbdd0}
  #count{margin-left:auto;color:var(--muted);font-size:13px}
  .tablewrap{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:auto;box-shadow:0 1px 2px rgba(15,23,42,.04)}
  table{width:100%;border-collapse:collapse;min-width:920px}
  thead th{position:sticky;top:0;background:#f8fafc;color:var(--muted);font-weight:600;font-size:12.5px;text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);white-space:nowrap;z-index:1}
  tbody td{padding:12px 14px;border-bottom:1px solid #eef2f7;font-size:14px;vertical-align:top}
  tbody tr{cursor:pointer}
  tbody tr:hover{background:#f1f7fb}
  tbody tr:last-child td{border-bottom:none}
  .id{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px;color:var(--muted);white-space:nowrap}
  .title{font-weight:600}
  .src{color:var(--muted);font-size:12.5px;white-space:nowrap}
  .date{color:var(--muted);font-size:12.5px;white-space:nowrap}
  .badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
  .b-proc{color:var(--amber);background:var(--amber-bg)}
  .b-replied{color:var(--orange);background:var(--orange-bg)}
  .b-open{color:var(--danger);background:var(--danger-bg)}
  .b-none{color:var(--gray);background:var(--gray-bg)}
  .b-done{color:var(--green);background:var(--green-bg)}
  .cat{font-size:12px;padding:2px 8px;border-radius:6px;background:#eef4f9;color:#0b3d5c;white-space:nowrap}
  .cat-ent{background:#fdf2f4;color:#a3122b}
  .hint{color:var(--muted);font-size:12.5px;margin:10px 2px 0}
  .empty{padding:40px;text-align:center;color:var(--muted)}
  .cards{display:none}
  .grp{margin-bottom:14px}
  .grp-title{display:flex;justify-content:space-between;align-items:center;font-size:13px;font-weight:600;color:var(--muted);margin:4px 2px 8px}
  .bottomnav{display:none}
  .card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px;cursor:pointer}
  .card:active{background:#eef6fb}
  .card .top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
  .card h3{margin:0 0 6px;font-size:15.5px;line-height:1.45;font-weight:600}
  .card .meta{color:var(--muted);font-size:12px;display:flex;flex-wrap:wrap;gap:6px}
  .card .sum{color:#475569;font-size:13px;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .modal{position:fixed;inset:0;background:rgba(15,23,42,.55);backdrop-filter:blur(2px);display:none;align-items:center;justify-content:center;padding:20px;z-index:50}
  .modal.open{display:flex}
  .panel{background:#fff;border:1px solid #dbe4ee;border-radius:16px;max-width:760px;width:100%;max-height:86vh;overflow:auto;padding:26px 28px;position:relative;-webkit-overflow-scrolling:touch;box-shadow:0 24px 60px rgba(15,23,42,.30)}
  .panel h2{margin:6px 0 4px;font-size:21px;line-height:1.45}
  .panel .meta{color:var(--muted);font-size:13px;margin-bottom:14px}
  .panel dl{display:grid;grid-template-columns:92px 1fr;gap:12px 14px;margin:0}
  .panel dt{color:var(--muted);font-size:13px;padding-top:2px}
  .panel dd{margin:0;font-size:14px;padding-bottom:10px;border-bottom:1px dashed #e8eef6}
  .panel dl dd:last-child{border-bottom:0;padding-bottom:0}
  .panel .close{position:absolute;right:16px;top:14px;border:none;background:#f1f5f9;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer;color:var(--muted)}
  .panel a{color:var(--brand2)}
  .panel .quote{background:#f8fafc;border-left:3px solid #9dbdd0;padding:8px 12px;border-radius:0 8px 8px 0;color:#334155}
  footer{border-top:1px solid var(--line);margin-top:26px;padding:20px 0 30px;color:var(--muted);font-size:12.5px}
  @media (max-width:720px){
    .stats{grid-template-columns:repeat(2,1fr)}
    h1{font-size:24px}
    .panel dl{grid-template-columns:1fr}
  }
  @media (max-width:760px){
    .tablewrap{display:none}
    .cards{display:grid;gap:10px}
    .hero{padding:22px 0 16px}
    h1{font-size:22px}
    .sub{font-size:12.5px;margin-bottom:14px}
    .stats{grid-template-columns:repeat(4,1fr);gap:8px}
    .stat{padding:8px 6px;border-radius:10px}
    .stat b{font-size:19px}
    .stat span{font-size:10.5px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .toolbar{position:sticky;top:0;z-index:20;background:rgba(246,248,251,.97);backdrop-filter:blur(8px);padding:8px 0;margin:0 0 10px;flex-wrap:nowrap}
    .toolbar input{flex:1 1 auto;min-width:0;font-size:16px;height:36px}
    .filterToggle{display:inline-flex;align-items:center;justify-content:center;height:36px;padding:0 14px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--brand);font-size:14px;flex:0 0 auto}
    .filters{display:none;position:absolute;left:0;right:0;top:48px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;box-shadow:0 14px 34px rgba(15,23,42,.16);flex-direction:column;gap:10px;z-index:25}
    .filters.open{display:flex}
    .filters select{width:100%;height:38px;font-size:16px}
    .filters button{width:100%;height:38px}
    #count{display:none}
    .modal{align-items:flex-end;padding:0}
    .panel{max-width:none;width:100%;max-height:92vh;border-radius:18px 18px 0 0;padding:30px 18px calc(26px + env(safe-area-inset-bottom))}
    .panel::before{content:"";position:absolute;top:9px;left:50%;transform:translateX(-50%);width:42px;height:4px;border-radius:2px;background:#d7e0ea}
    .panel .close{top:16px}
    .panel h2{font-size:18px}
    footer{padding-bottom:calc(20px + env(safe-area-inset-bottom))}
    main{padding-bottom:78px}
    .bottomnav{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:30;background:#fff;border-top:1px solid var(--line);padding:6px 0 calc(6px + env(safe-area-inset-bottom));box-shadow:0 -2px 10px rgba(15,23,42,.06)}
    .bottomnav button{flex:1;border:0;background:none;color:var(--muted);font-size:13px;padding:7px 0;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px}
    .bottomnav button b{font-size:11px;font-weight:600;line-height:1}
    .bottomnav button.on b{color:var(--brand)}
    .stat{padding:10px 12px}
    .stat b{font-size:22px}
    .grp{scroll-margin-top:112px}
  }
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <div class="kicker">武汉市 · 民生与涉企诉求线索库</div>
    <h1>武汉诉求线索看板</h1>
    <p class="sub">公开网络线索归集 · 每条可溯源 · 投诉人已脱敏 · 剔除官媒/官方已办结事项</p>
    <div class="stats" id="stats"></div>
  </div>
</header>
<main class="wrap">
  <div class="toolbar">
    <input id="q" type="search" placeholder="搜索标题、摘要、承办单位、编号…">
    <button id="filterToggle" class="filterToggle" type="button">筛选</button>
    <div class="filters" id="filters">
      <select id="cat"><option value="">全部类别</option></select>
      <select id="status"><option value="">全部状态</option></select>
      <select id="src"><option value="">全部渠道</option></select>
      <select id="sort">
        <option value="date_desc">发布时间 新→旧</option>
        <option value="id_desc">编号 新→旧</option>
        <option value="id_asc">编号 旧→新</option>
      </select>
      <button id="reset" type="button">重置</button>
    </div>
    <span id="count"></span>
  </div>
  <div class="tablewrap">
    <table>
      <thead><tr><th>编号</th><th>类别</th><th>标题</th><th>渠道</th><th>发布时间</th><th>状态</th><th>核验</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
  <div id="cards" class="cards"></div>
  <p class="hint">点击任意一条查看诉求摘要、投诉人（脱敏）、承办单位、状态依据与原文链接。</p>
</main>
<footer>
  <div class="wrap">
    <div id="gen"></div>
    <div style="margin-top:6px">数据来源：武汉市政府门户“来信公示”、委办局来信公示、武汉城市留言板、人民网领导留言板、黑猫投诉等公开页面。投诉人信息已按规范脱敏，不含身份证号、房号等敏感信息；内容仅反映公开页面记载，不构成对事实的最终认定。</div>
    <div style="margin-top:6px">维护：服务器 systemd 定时任务，每 12 小时自动归集；台账与逐期报告见 GitHub 仓库。</div>
  </div>
</footer>
<nav class="bottomnav" id="bottomnav">
  <button type="button" data-cat="" class="on"><b id="navAll">0</b>全部</button>
  <button type="button" data-cat="民生"><b id="navCivil">0</b>民生</button>
  <button type="button" data-cat="涉企"><b id="navEnt">0</b>涉企</button>
</nav>
<div class="modal" id="modal">
  <div class="panel">
    <button class="close" id="close" type="button" aria-label="关闭">×</button>
    <div id="detail"></div>
  </div>
</div>
<script>
const DATA = __DATA__;

const esc = s => String(s == null ? "" : s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;");

const fmtDate = s => {
  if(!s) return "";
  const t = String(s).replace("T"," ").replace("+08:00","");
  return t.length >= 16 ? t.slice(0,16) : t.slice(0,10);
};

const statusClass = s => {
  if(/已办结|已解决/.test(s)) return "b-done";
  if(/已回复未办结/.test(s)) return "b-replied";
  if(/处理中/.test(s)) return "b-proc";
  if(/未办结/.test(s)) return "b-open";
  return "b-none";
};

const catClass = c => c === "涉企" ? "cat cat-ent" : "cat";
let sorted = DATA.slice();

function sortBy(mode){
  const arr = DATA.slice();
  if(mode === "id_asc") arr.sort((a,b)=> String(a.id||"").localeCompare(String(b.id||"")));
  else if(mode === "date_desc") arr.sort((a,b)=> String(b.published_at||"").localeCompare(String(a.published_at||"")));
  else arr.sort((a,b)=> String(b.id||"").localeCompare(String(a.id||"")));
  return arr;
}

function cardHtml(x){
  const idx = sorted.indexOf(x);
  return `<article class="card" data-i="${idx}">
      <div class="top">
        <span class="badge ${statusClass(x.status)}">${esc(x.status)}</span>
        <span class="${catClass(x.category)}">${esc(x.category)}</span>
        <span class="date">${esc(x.verify_level)} 级</span>
      </div>
      <h3>${esc(x.title)}</h3>
      <div class="meta"><span>${esc(x.id)}</span><span>${esc(fmtDate(x.published_at))}</span><span>${esc(x.channel)}</span></div>
      <div class="sum">${esc(x.summary)}</div>
    </article>`;
}

function uniq(key){  return [...new Set(sorted.map(x=>x[key]).filter(Boolean))];
}

function initSelects(){
  uniq("category").forEach(v=>{
    const o=document.createElement("option"); o.value=v; o.textContent=v; cat.appendChild(o);
  });
  uniq("status").forEach(v=>{
    const o=document.createElement("option"); o.value=v; o.textContent=v; document.getElementById("status").appendChild(o);
  });
  const srcKey = x => x.channel;
  [...new Set(sorted.map(srcKey).filter(Boolean))].forEach(v=>{
    const o=document.createElement("option"); o.value=v; o.textContent=v.length>22?v.slice(0,22)+"…":v; src.appendChild(o);
  });
}

function renderStats(list){
  const total=list.length;
  const civil=list.filter(x=>x.category==="民生").length;
  const ent=list.filter(x=>x.category==="涉企").length;
  const active=list.filter(x=>!/已办结|已解决/.test(x.status||"")).length;
  const a=list.filter(x=>x.verify_level==="A").length;
  const items=[["总数",total],["民生",civil],["涉企",ent],["待办",active]];
  stats.innerHTML = items.map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join("");
}

function render(){
  sorted = sortBy(document.getElementById("sort").value);
  const q=(document.getElementById("q").value||"").trim().toLowerCase();
  const c=cat.value, s=document.getElementById("status").value, sr=src.value;
  const list=sorted.filter(x=>{
    if(c && x.category!==c) return false;
    if(s && x.status!==s) return false;
    if(sr && x.channel!==sr) return false;
    if(q){
      const hay=[x.id,x.title,x.summary,x.handler,x.channel,x.ref_no].join(" ").toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  count.textContent = `当前 ${list.length} / ${sorted.length} 条`;
  if(!list.length){
    rows.innerHTML = `<tr><td colspan="7"><div class="empty">没有匹配的线索</div></td></tr>`;
    document.getElementById("cards").innerHTML = `<div class="empty">没有匹配的线索</div>`;
    return;
  }
  rows.innerHTML = list.map((x,i)=>{
    const idx = sorted.indexOf(x);
    return `<tr data-i="${idx}">
      <td class="id">${esc(x.id)}</td>
      <td><span class="${catClass(x.category)}">${esc(x.category)}</span></td>
      <td class="title">${esc(x.title)}</td>
      <td class="src">${esc(x.channel)}</td>
      <td class="date">${esc(fmtDate(x.published_at))}</td>
      <td><span class="badge ${statusClass(x.status)}">${esc(x.status)}</span></td>
      <td class="date">${esc(x.verify_level)}</td>
    </tr>`;
  }).join("");
  const groups = new Map();
  list.forEach(x=>{
    const k = x.category || "其他";
    if(!groups.has(k)) groups.set(k, []);
    groups.get(k).push(x);
  });
  const order = ["民生","涉企"];
  const keys = [...groups.keys()].sort((a,b)=>{
    const ia = order.indexOf(a), ib = order.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  document.getElementById("cards").innerHTML = keys.map(k=>`
    <section class="grp" data-cat="${esc(k)}">
      <div class="grp-title"><span>${esc(k)}</span><span>${groups.get(k).length} 条</span></div>
      ${groups.get(k).map(cardHtml).join("")}
    </section>`).join("");
  updateNav();
}

function openDetail(i){
  const x=sorted[i]; if(!x) return;
  const link = x.channel_url || x.source_url || "";
  detail.innerHTML = `
    <div class="meta">${esc(x.id)} · ${esc(x.category)} · ${esc(fmtDate(x.published_at))}</div>
    <h2>${esc(x.title)}</h2>
    <div class="meta">${esc(x.channel)}${x.ref_no? " · 编号 "+esc(x.ref_no):""}</div>
    <dl>
      <dt>诉求摘要</dt><dd>${esc(x.summary)}</dd>
      <dt>投诉人</dt><dd>${esc(x.complainant || "未披露")}</dd>
      <dt>承办单位</dt><dd>${esc(x.handler || "原文未载")}</dd>
      <dt>当前状态</dt><dd><span class="badge ${statusClass(x.status)}">${esc(x.status)}</span></dd>
      <dt>状态依据</dt><dd class="quote">${esc(x.status_evidence || "原文未载")}</dd>
      <dt>溯源</dt><dd>${esc(x.verify_level)} 级 · ${esc(x.confidence || "")}置信度${x.notes? " · "+esc(x.notes):""}</dd>
      <dt>原文链接</dt><dd>${link? `<a href="${esc(link)}" target="_blank" rel="noopener">${esc(link)}</a>` : "无"}</dd>
      <dt>去重指纹</dt><dd class="id">${esc(x.fingerprint || "")}</dd>
    </dl>`;
  modal.classList.add("open");
  document.body.classList.add("modal-open");
}

function closeModal(){
  modal.classList.remove("open");
  document.body.classList.remove("modal-open");
}

document.getElementById("rows").addEventListener("click", e=>{
  const tr=e.target.closest("tr[data-i]"); if(tr) openDetail(Number(tr.dataset.i));
});
document.getElementById("cards").addEventListener("click", e=>{
  const c=e.target.closest(".card[data-i]"); if(c) openDetail(Number(c.dataset.i));
});

function updateNav(){
  const cur = cat.value || "";
  document.querySelectorAll("#bottomnav button").forEach(b=>{
    b.classList.toggle("on", (b.dataset.cat || "") === cur);
  });
}

function initNavCounts(){
  navAll.textContent = DATA.length;
  navCivil.textContent = DATA.filter(x=>x.category==="民生").length;
  navEnt.textContent = DATA.filter(x=>x.category==="涉企").length;
}

document.getElementById("bottomnav").addEventListener("click", e=>{
  const b = e.target.closest("button[data-cat]"); if(!b) return;
  cat.value = b.dataset.cat || "";
  render();
  requestAnimationFrame(()=>{
    const c = cat.value;
    if(c){
      const g = document.querySelector(`.grp[data-cat="${c}"]`);
      if(g){ g.scrollIntoView({behavior:"smooth", block:"start"}); return; }
    }
    window.scrollTo({top:0, behavior:"smooth"});
  });
});
document.getElementById("close").addEventListener("click", closeModal);
modal.addEventListener("click", e=>{ if(e.target===modal) closeModal(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape") closeModal(); });
["q","cat","status","src","sort"].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener(el.tagName==="INPUT"?"input":"change", render);
});
reset.addEventListener("click", ()=>{ document.getElementById("q").value=""; cat.value=""; document.getElementById("status").value=""; src.value=""; document.getElementById("sort").value="date_desc"; document.getElementById("filters").classList.remove("open"); render(); });

const filtersEl = document.getElementById("filters");
document.getElementById("filterToggle").addEventListener("click", ()=>filtersEl.classList.toggle("open"));
filtersEl.addEventListener("change", ()=>filtersEl.classList.remove("open"));
document.addEventListener("click", e=>{
  if(!filtersEl.contains(e.target) && e.target.id !== "filterToggle") filtersEl.classList.remove("open");
});

document.getElementById("gen").textContent = "生成时间：" + __GEN__ + " · 共 " + DATA.length + " 条 · 覆盖窗口 __WINDOW__";
initSelects(); initNavCounts(); renderStats(sorted); render();

if ("serviceWorker" in navigator && location.protocol === "https:") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  });
}
</script>
</body>
</html>
"""


def main() -> int:
    if not LEDGER.exists():
        print(f"未找到台账：{LEDGER}")
        return 1
    rows = []
    for lineno, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:  # noqa: BLE001
            print(f"第 {lineno} 行无法解析：{exc}")
            return 1
    if not rows:
        print("台账为空，先生成线索后再看板")
        return 1

    data_js = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    gen = datetime.now().strftime("%Y-%m-%d %H:%M")
    window = "2026-10-26 至 2026-11-25"
    html_text = (
        TEMPLATE.replace("__DATA__", data_js)
        .replace("__GEN__", json.dumps(gen, ensure_ascii=False))
        .replace("__WINDOW__", window)
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html_text, encoding="utf-8")
    print(f"已生成 {len(rows)} 条 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
