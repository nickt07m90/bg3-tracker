#!/usr/bin/env python3
"""
BG3 Honor Mode / Dark Urge Walkthrough Tracker Builder
Reads walkthrough.txt (with <<TABLE>>...<//TABLE>> markers) and outputs index.html
"""
import re, json, sys

# ── Section detection ──────────────────────────────────────────────

SECTION_RES = [
    (re.compile(r"^7\.\s*Honor Mode"), "Act 1 Overview"),
    (re.compile(r"^8\.\s*Honor Mode"), "Act 2 Overview"),
    (re.compile(r"^9\.\s*Honor Mode"), "Act 3 Overview"),
    (re.compile(r"^Character Creation$"), "Character Creation"),
    (re.compile(r"^Prologue$"), "Prologue"),
    (re.compile(r"^(Day \d+)$"), None),
    (re.compile(r"^(Mini Day \d+)$"), None),
]

def detect_section(line):
    s = line.strip()
    for pat, name in SECTION_RES:
        m = pat.match(s)
        if m:
            return name if name else m.group(1)
    return None

# ── Achievement names ──────────────────────────────────────────────

ACHIEVEMENTS = {"Sins of the Father", "Critical Hit", "Foehammer", "Embrace Your Urge"}

# ── Lines to skip (TOC / link lists) ──────────────────────────────

def is_toc_line(s):
    return bool(re.match(r"^Links to different sections", s) or
                re.match(r"^[*\u2022\u25cf]\s+(Day|Mini Day|Prologue)", s))

# ── Main parser ───────────────────────────────────────────────────

def parse(text):
    """Return list of {name, chunks:[{type, content}]}"""
    lines = text.split("\n")
    n = len(lines)
    sections = []
    cur_name = None
    cur_items = []  # list of (type, content)
    i = 0
    in_toc = False

    def flush():
        nonlocal cur_items
        if cur_name and cur_items:
            sections.append((cur_name, cur_items))
        cur_items = []

    while i < n:
        line = lines[i]
        s = line.strip()

        # blank
        if not s:
            i += 1
            continue

        # TOC block
        if re.match(r"^Links to different sections", s):
            in_toc = True
            i += 1
            continue
        if in_toc:
            if re.match(r"^[*\u2022\u25cf]\s+(Day|Mini Day|Prologue)", s):
                i += 1
                continue
            in_toc = False

        # section header
        sec = detect_section(line)
        if sec:
            flush()
            cur_name = sec
            cur_items = []
            i += 1
            continue

        # table block
        if s == "<<TABLE>>":
            tbl_lines = []
            i += 1
            while i < n and lines[i].strip() != "<</TABLE>>":
                tbl_lines.append(lines[i])
                i += 1
            i += 1  # skip <</TABLE>>
            cur_items.append(("table", "\n".join(tbl_lines)))
            continue

        # achievement
        if s in ACHIEVEMENTS:
            ach_parts = [s]
            i += 1
            # skip blanks
            while i < n and not lines[i].strip():
                i += 1
            # collect description
            desc = []
            while i < n:
                s2 = lines[i].strip()
                if not s2:
                    i += 1
                    continue
                if re.match(r"^\d+\s+guide", s2):
                    ach_parts.append(" ".join(desc))
                    ach_parts.append(s2)
                    i += 1
                    break
                if s2 in ACHIEVEMENTS:
                    # next achievement immediately follows (shared guide count)
                    ach_parts.append(" ".join(desc))
                    break
                desc.append(s2)
                i += 1
            # skip trailing blanks
            while i < n and not lines[i].strip():
                i += 1
            cur_items.append(("achievement", "\n".join(p for p in ach_parts if p)))
            continue

        # regular text
        cur_items.append(("text", s))
        i += 1

    flush()
    return sections

# ── Sentence splitter ─────────────────────────────────────────────

def split_sentences(text, lo=250, hi=500):
    """Split text at sentence boundaries into chunks of lo..hi chars."""
    if len(text) <= hi:
        return [text]
    # Split at sentence ends
    sents = re.split(r"(?<=[.!?])\s+", text)
    chunks, cur = [], ""
    for s in sents:
        test = (cur + " " + s).strip() if cur else s
        if len(test) > hi and cur:
            chunks.append(cur)
            cur = s
        else:
            cur = test
    if cur:
        if chunks and len(cur) < lo:
            chunks[-1] += " " + cur
        else:
            chunks.append(cur)
    return chunks

# ── Build final JSON structure ────────────────────────────────────

def build(text):
    raw = parse(text)
    sections = []
    for name, items in raw:
        # Skip the "overview" sections (just TOC pages)
        if "Overview" in name:
            continue
        chunks = []
        text_buf = []
        carryover = ""  # incomplete sentence fragment to bridge across tables

        def flush_buf(force_all=False):
            nonlocal carryover
            if not text_buf:
                return
            joined = carryover + (" " if carryover else "") + " ".join(text_buf)
            carryover = ""
            text_buf.clear()

            if force_all:
                # End of section: emit everything
                for c in split_sentences(joined):
                    chunks.append({"type": "text", "content": c})
                return

            # Check if the joined text ends mid-sentence
            stripped = joined.rstrip()
            if stripped and not re.search(r'[.!?:)\]]$', stripped):
                # Find last sentence boundary
                m = list(re.finditer(r'[.!?]\s+', joined))
                if m:
                    last = m[-1]
                    complete = joined[:last.end()].rstrip()
                    leftover = joined[last.end():].strip()
                    for c in split_sentences(complete):
                        chunks.append({"type": "text", "content": c})
                    carryover = leftover
                else:
                    # No sentence boundary at all - carry the whole thing
                    carryover = stripped
            else:
                for c in split_sentences(joined):
                    chunks.append({"type": "text", "content": c})

        for typ, content in items:
            if typ == "text":
                text_buf.append(content)
            else:
                flush_buf(force_all=False)
                chunks.append({"type": typ, "content": content})
        flush_buf(force_all=True)

        if chunks:
            sections.append({"name": name, "chunks": chunks})
    return sections

# ── HTML generation ───────────────────────────────────────────────

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="BG3 Tracker">
<meta name="theme-color" content="#1a0a0a">
<title>BG3 Honor Mode Tracker</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0d0d0d;--s1:#181410;--s2:#22201a;--bd:#3a342a;
  --tx:#ddd5c4;--txd:#8a7f6e;--ac:#c9a84c;--acg:#e6c24e;
  --ach:#9b6dff;--achb:#b394ff;
  --chk:#4ade80;--chkd:#14532d;--red:#ef4444;
  --pbg:#261e10;--pfill:linear-gradient(90deg,#c9a84c,#e6c24e);
}
html,body{background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.55;-webkit-text-size-adjust:100%}
body{padding-bottom:120px}

/* ── Header ── */
.hdr{position:sticky;top:0;z-index:100;background:rgba(13,13,13,.96);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);padding:calc(env(safe-area-inset-top,0px) + 10px) 16px 12px;border-bottom:1px solid var(--bd)}
.hdr h1{font-size:14px;font-weight:700;color:var(--ac);letter-spacing:.6px;text-transform:uppercase;margin-bottom:8px}
.bar-wrap{background:var(--pbg);border-radius:6px;height:8px;overflow:hidden}
.bar-fill{height:100%;background:var(--pfill);border-radius:6px;transition:width .35s ease;width:0}
.bar-info{display:flex;justify-content:space-between;font-size:12px;color:var(--txd);margin-top:4px}
.tools{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.tools button{font-size:12px;padding:6px 12px;border-radius:7px;border:1px solid var(--bd);background:var(--s1);color:var(--tx);cursor:pointer;-webkit-tap-highlight-color:transparent}
.tools button:active{background:var(--s2)}
.btn-resume{background:var(--ac)!important;color:#000!important;border-color:var(--ac)!important;font-weight:600}
.btn-reset{border-color:var(--red)!important;color:var(--red)!important}

/* ── Sections ── */
.wrap{padding:14px 12px 0}
.sec{margin-bottom:14px;border:1px solid var(--bd);border-radius:12px;overflow:hidden;background:var(--s1)}
.sec.done{border-color:var(--chkd)}
.sec-h{display:flex;align-items:center;padding:14px;cursor:pointer;-webkit-tap-highlight-color:transparent;user-select:none;gap:10px}
.sec-h:active{background:var(--s2)}
.sec-n{flex:1;font-size:15px;font-weight:600;color:var(--ac)}
.sec.done .sec-n{color:var(--chk)}
.sec-c{font-size:13px;color:var(--txd);font-variant-numeric:tabular-nums;white-space:nowrap}
.sec.done .sec-c{color:var(--chk)}
.chv{color:var(--txd);font-size:13px;transition:transform .2s;flex-shrink:0}
.sec.open .chv{transform:rotate(90deg)}
.sec-b{display:none;padding:0 14px 14px}
.sec.open .sec-b{display:block}

/* ── Steps ── */
.stp{display:flex;gap:12px;padding:11px 0;border-bottom:1px solid var(--bd);align-items:flex-start}
.stp:last-child{border-bottom:none}
.stp.ck .s-txt{color:var(--txd);text-decoration:line-through;text-decoration-color:rgba(138,127,110,.5)}
.s-cb{width:24px;height:24px;border:2px solid var(--bd);border-radius:6px;flex-shrink:0;display:flex;align-items:center;justify-content:center;cursor:pointer;margin-top:1px;-webkit-tap-highlight-color:transparent;transition:all .15s}
.stp.ck .s-cb{background:var(--chk);border-color:var(--chk)}
.stp.ck .s-cb::after{content:"\2713";color:#000;font-size:14px;font-weight:700}
.s-txt{flex:1;font-size:14px;line-height:1.55}

/* achievement */
.stp.ach{border-left:3px solid var(--achb);padding-left:12px;margin-left:-3px;background:rgba(155,109,255,.05);border-radius:0 8px 8px 0}
.stp.ach .s-txt{color:#d4c4ff}
.stp.ach.ck .s-txt{color:var(--txd)}

/* table */
.stp.tbl .s-txt{font-family:"SF Mono",Menlo,Monaco,"Courier New",monospace;font-size:11px;white-space:pre;overflow-x:auto;-webkit-overflow-scrolling:touch;line-height:1.4;background:var(--s2);padding:12px;border-radius:8px;border:1px solid var(--bd)}

/* highlight */
.stp.hl{animation:pulse 1.6s ease}
@keyframes pulse{0%{background:rgba(201,168,76,.25)}100%{background:transparent}}

/* ── Modal ── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;align-items:center;justify-content:center;padding:20px}
.modal-bg.vis{display:flex}
.modal{background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:28px 24px;max-width:300px;width:100%;text-align:center}
.modal h3{color:var(--red);margin-bottom:8px}
.modal p{color:var(--txd);font-size:14px;margin-bottom:20px}
.modal-btns{display:flex;gap:10px;justify-content:center}
.modal-btns button{padding:9px 22px;border-radius:9px;border:1px solid var(--bd);font-size:14px;cursor:pointer}
.modal-btns .m-cancel{background:var(--s2);color:var(--tx)}
.modal-btns .m-ok{background:var(--red);color:#fff;border-color:var(--red)}
</style>
</head>
<body>
<div class="hdr">
  <h1>BG3 Honor Mode / Dark Urge</h1>
  <div class="bar-wrap"><div class="bar-fill" id="bf"></div></div>
  <div class="bar-info"><span id="bc">0 / 0</span><span id="bp">0%</span></div>
  <div class="tools">
    <button class="btn-resume" onclick="goNext()">&#9654; Resume</button>
    <button onclick="expAll()">Expand All</button>
    <button onclick="colAll()">Collapse All</button>
    <button class="btn-reset" onclick="showR()">Reset</button>
  </div>
</div>
<div class="wrap" id="wrap"></div>
<div class="modal-bg" id="mbg">
  <div class="modal">
    <h3>Reset all progress?</h3>
    <p>Every checkbox will be cleared. This cannot be undone.</p>
    <div class="modal-btns">
      <button class="m-cancel" onclick="hideR()">Cancel</button>
      <button class="m-ok" onclick="doReset()">Reset</button>
    </div>
  </div>
</div>
<script>
var KEY="bg3HonorDarkUrgeTrackerData";
var SEC=%%DATA%%;
var st;try{st=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){st={}}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}
function k(a,b){return a+"."+b}
function chk(a,b){return!!st[k(a,b)]}
function set(a,b,v){if(v)st[k(a,b)]=1;else delete st[k(a,b)];save()}
function esc(s){var d=document.createElement("span");d.textContent=s;return d.innerHTML}

function render(){
  var w=document.getElementById("wrap");w.innerHTML="";
  var tt=0,tc=0;
  SEC.forEach(function(sec,si){
    var el=document.createElement("div");el.className="sec";el.id="S"+si;
    var sc=0;
    sec.chunks.forEach(function(_,ci){tt++;if(chk(si,ci)){tc++;sc++}});
    var full=sc===sec.chunks.length;
    if(full)el.classList.add("done");

    var h=document.createElement("div");h.className="sec-h";
    h.innerHTML='<span class="sec-n">'+esc(sec.name)+'</span>'
      +'<span class="sec-c">'+(full?"\u2713 ":"")+sc+"/"+sec.chunks.length+'</span>'
      +'<span class="chv">\u25B6</span>';
    h.onclick=function(){el.classList.toggle("open")};
    el.appendChild(h);

    var body=document.createElement("div");body.className="sec-b";
    sec.chunks.forEach(function(ch,ci){
      var s=document.createElement("div");
      s.className="stp"+(ch.type==="achievement"?" ach":"")+(ch.type==="table"?" tbl":"");
      s.id="T"+si+"-"+ci;
      if(chk(si,ci))s.classList.add("ck");

      var cb=document.createElement("div");cb.className="s-cb";
      cb.onclick=function(e){e.stopPropagation();
        var nv=!chk(si,ci);set(si,ci,nv);
        s.classList.toggle("ck",nv);updSec(si);updBar()};
      s.appendChild(cb);

      var tx=document.createElement("div");tx.className="s-txt";
      if(ch.type==="achievement"){
        tx.innerHTML="\uD83C\uDFC6 "+esc(ch.content).replace(/\n/g,"<br>");
      } else {
        tx.textContent=ch.content;
      }
      s.appendChild(tx);body.appendChild(s);
    });
    el.appendChild(body);w.appendChild(el);
  });
  updBarD(tc,tt);
}

function updSec(si){
  var sec=SEC[si],el=document.getElementById("S"+si),c=0;
  sec.chunks.forEach(function(_,ci){if(chk(si,ci))c++});
  var full=c===sec.chunks.length;
  el.classList.toggle("done",full);
  el.querySelector(".sec-c").textContent=(full?"\u2713 ":"")+c+"/"+sec.chunks.length;
}
function updBar(){
  var t=0,c=0;
  SEC.forEach(function(s,si){s.chunks.forEach(function(_,ci){t++;if(chk(si,ci))c++})});
  updBarD(c,t);
}
function updBarD(c,t){
  var p=t?Math.round(c/t*100):0;
  document.getElementById("bf").style.width=p+"%";
  document.getElementById("bc").textContent=c+" / "+t;
  document.getElementById("bp").textContent=p+"%";
}
function goNext(){
  for(var si=0;si<SEC.length;si++)for(var ci=0;ci<SEC[si].chunks.length;ci++){
    if(!chk(si,ci)){
      document.getElementById("S"+si).classList.add("open");
      var el=document.getElementById("T"+si+"-"+ci);
      setTimeout(function(){
        el.scrollIntoView({behavior:"smooth",block:"center"});
        el.classList.add("hl");
        setTimeout(function(){el.classList.remove("hl")},1700);
      },120);
      return;
    }
  }
}
function expAll(){document.querySelectorAll(".sec").forEach(function(s){s.classList.add("open")})}
function colAll(){document.querySelectorAll(".sec").forEach(function(s){s.classList.remove("open")})}
function showR(){document.getElementById("mbg").classList.add("vis")}
function hideR(){document.getElementById("mbg").classList.remove("vis")}
function doReset(){st={};save();hideR();render()}
render();
</script>
</body>
</html>'''

def main():
    with open("walkthrough.txt", "r", encoding="utf-8") as f:
        text = f.read()
    sections = build(text)
    total = sum(len(s["chunks"]) for s in sections)
    print(f"Parsed {len(sections)} sections, {total} total steps")
    for s in sections:
        types = {}
        for c in s["chunks"]:
            types[c["type"]] = types.get(c["type"], 0) + 1
        info = ", ".join(f"{v} {k}" for k, v in types.items())
        print(f"  {s['name']}: {len(s['chunks'])} steps ({info})")
    sj = json.dumps(sections, ensure_ascii=False)
    html = HTML.replace("%%DATA%%", sj)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nGenerated index.html ({len(html):,} bytes)")

if __name__ == "__main__":
    main()
