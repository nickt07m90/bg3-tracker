#!/usr/bin/env python3
"""
BG3 Honor Mode / Dark Urge Walkthrough Tracker Builder
Reads walkthrough.txt -> produces index.html with interactive checklist
"""
import re, json

def read_file(path="walkthrough.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SECTION_PATTERNS = [
    (r"^7\.\s+Honor Mode", "Act 1 - Honor Mode / Dark Urge"),
    (r"^8\.\s+Honor Mode", "Act 2 - Honor Mode / Dark Urge"),
    (r"^9\.\s+Honor Mode", "Act 3 - Honor Mode / Dark Urge"),
    (r"^Character Creation$", "Character Creation"),
    (r"^Prologue$", "Prologue"),
    (r"^(Day \d+)\s*$", None),
    (r"^(Mini Day \d+)\s*$", None),
]

ACHIEVEMENTS = {
    "Sins of the Father",
    "Critical Hit",
    "Foehammer",
    "Embrace Your Urge",
}

def detect_section(line):
    s = line.strip()
    for pat, name in SECTION_PATTERNS:
        m = re.match(pat, s)
        if m:
            if name is not None:
                return name
            return m.group(1)
    return None

def is_toc_line(line):
    s = line.strip()
    if re.match(r"^Links to different sections", s):
        return True
    if re.match(r"^\s*[*\u2022\u25cf]\s+(Day|Mini Day|Prologue)", s):
        return True
    return False

TABLE_STARTS = re.compile(
    r"^\s*(Level \d+|"
    r"Tav\b|Karlach\b|Gale\b|Shadowheart\b|Shdaowheart\b|Lae'zel\b|"
    r"Handheld explosives|Main sources|Optional inclusions|Unsure how|"
    r"Summonable Allies|Attacks/Heals|Characters that|"
    r"Offensive spells|Buff/Defensive|Scrolls)"
)

TABLE_CONT = re.compile(
    r"^\s*("
    r"[\u2022\u25cf\u25cb]\s+|"
    r"Abilities:|Cantrips:|Spells:|Subclass:|Feat:|Spellbook:|"
    r"Fighting Style:|Skill Proficiency:|Metamagic:|Prepared Spells:|"
    r"Replace Spell:|Add Class:|Skill Expertise:|Remove:|Background:|"
    r"Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma|"
    r"Nothing to|choose\.|Choose\.|"
    r"\+\d+\s*bonus|"
    r"Weapon\b|Hand\b|Domain\b|Sorcery\b|Open Hand|Evocation|Storm|Life|Thief|"
    r"Way of|Fighting\b|Armor\b|Missile\b|Bolt\b|Frost\b|Grasp\b|Chill\b|"
    r"Smite\b|Wounds\b|Command\b|Sanctuary\b|Guiding\b|Thunderwave|Grease\b|"
    r"Strider\b|Daggers\b|Person\b|Warding\b|Lightning\b|Dead\b|Fire\b|"
    r"Favour\b|Cold\b|Strike\b|Blast\b|Ward\b|Plague\b|Feast\b|Spell\b|"
    r"Caster\b|Attacker\b|Brawler\b|Wielder\b|Resilient\b|Master\b|"
    r"Sniper\b|Eldritch\b|Improvement\b|Protection\b|Religion\b|Insight\b|"
    r"History\b|Medicine\b|Investigation\b|Acrobatics\b|Vigilance\b|"
    r"Monk Level|Rogue Level|Rogue level|"
    r"provide buffs|damage|Popdrakes|Squidjins|Wogglims|Acid Vial|"
    r"Smokepowder|Holy Water|Runepowder|Brilliant|Caustic|Flammable|"
    r"Poisonous|Fungal|Hearthlight|Sanguine|Spiked|Void|Purple Worm|"
    r"Serpent Fang|Wyvern|Arrow of|"
    r"Artistry|Disintergrate|Blight\b|Circle of Death|Chain Lightning|"
    r"Lightning Bolt|Cloudkill|Cone of Cold|Ice Storm|Otiluke|Wall of|"
    r"Fireball\b|Sunbeam|Conjure|Globe|Haste\b|Mirror Image|"
    r"Mizora\b|Aylin\b|Strange Ox|Zevlor\b|Florrick|Barcus\b|"
    r"Rolan\b|Kithrak|Isobel\b|Volo\b|Arabella\b|Mol\b|"
    r"\d+d\d+|Freedom of|Gain \+|"
    r"Compelled|Animate|Wall of Fire|War\b|Warden|Heroes|Insect|"
    r"Elemental\b|Alert\b|Great\b|Savage|Tavern|Ability|"
    r"Deva\b|Image\b|Resilient\b|Distant\b|Twinned\b|Quickened\b|Careful\b|"
    r"Healing Word|Shield of Faith|Hold Person|Spirit|Glyph|"
    r"Mass Healing|Counterspell|Fireball|Enlarge|Reduce|"
    r"Magic Weapon|Bless\b|Branding|Divine|Cloud of|Knock\b|"
    r"Darkness\b|Arcane Lock|Long\s*Strider|Tasha|Hideous|"
    r"Chromatic|Ice Knife|Mage Armor|Magic Missile|"
    r"Shocking|Bone Chill|Fire Bolt|Ray of Frost|Sacred Flame|"
    r"Resistance\b|Guidance\b|Light\b|Blade\b|Acid Splash|"
    r"Disintegrate|Chain|Planar|Flame\b|Cone of|Whatever you|"
    r"\d+\s*$|\(\+?\d|added\)|bonus\s+added"
    r")"
)

def parse_sections(text):
    lines = text.split("\n")
    sections = []
    cur_name = None
    cur_items = []
    skip_toc = False
    i = 0
    n = len(lines)

    def flush():
        nonlocal cur_items
        if cur_name and cur_items:
            sections.append((cur_name, cur_items))
        cur_items = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Skip blank
        if not stripped:
            i += 1
            continue

        # Skip TOC
        if re.match(r"^Links to different sections", stripped):
            skip_toc = True
            i += 1
            continue
        if skip_toc:
            if is_toc_line(line):
                i += 1
                continue
            skip_toc = False

        # Section header?
        sec = detect_section(line)
        if sec:
            flush()
            cur_name = sec
            cur_items = []
            i += 1
            continue

        # Achievement?
        if stripped in ACHIEVEMENTS:
            ach_lines = [stripped]
            i += 1
            while i < n and not lines[i].strip():
                i += 1
            desc = []
            while i < n:
                s2 = lines[i].strip()
                if not s2:
                    i += 1
                    continue
                if re.match(r"^\d+\s+guide", s2):
                    ach_lines.append(" ".join(desc))
                    ach_lines.append(s2)
                    i += 1
                    break
                # Next achievement starts immediately (no guide line between)
                if s2 in ACHIEVEMENTS:
                    ach_lines.append(" ".join(desc))
                    break
                desc.append(s2)
                i += 1
            while i < n and not lines[i].strip():
                i += 1
            cur_items.append(("achievement", "\n".join(ach_lines)))
            continue

        # Table block?
        if TABLE_STARTS.match(stripped):
            tbl = [stripped]
            i += 1
            blank_run = 0
            while i < n:
                s2 = lines[i].strip()
                if not s2:
                    blank_run += 1
                    if blank_run > 2:
                        break
                    tbl.append("")
                    i += 1
                    continue
                blank_run = 0
                if TABLE_STARTS.match(s2) or TABLE_CONT.match(s2) or (len(s2) < 30 and not re.match(r"^[A-Z].*[.!?]\s*$", s2)):
                    tbl.append(s2)
                    i += 1
                    continue
                break
            # Trim trailing blanks
            while tbl and not tbl[-1].strip():
                tbl.pop()
            cur_items.append(("table", "\n".join(tbl)))
            continue

        # Regular text
        cur_items.append(("text", stripped))
        i += 1

    flush()
    return sections

def split_sentences(text, max_c=500, min_c=200):
    if len(text) <= max_c:
        return [text]
    sents = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    cur = ""
    for s in sents:
        if cur and len(cur) + len(s) + 1 > max_c:
            if len(cur) >= min_c:
                chunks.append(cur.strip())
                cur = s
            else:
                cur += " " + s
        else:
            cur = (cur + " " + s).strip() if cur else s
    if cur.strip():
        if chunks and len(cur.strip()) < min_c:
            chunks[-1] += " " + cur.strip()
        else:
            chunks.append(cur.strip())
    return chunks

def chunkify(items):
    chunks = []
    text_buf = []

    def flush_text():
        nonlocal text_buf
        if text_buf:
            joined = " ".join(text_buf)
            for c in split_sentences(joined):
                chunks.append({"type": "text", "content": c})
            text_buf = []

    for typ, content in items:
        if typ == "text":
            text_buf.append(content)
        else:
            flush_text()
            chunks.append({"type": typ, "content": content})
    flush_text()
    return chunks

def build(text):
    raw = parse_sections(text)
    sections = []
    for name, items in raw:
        ch = chunkify(items)
        if ch:
            sections.append({"name": name, "chunks": ch})
    return sections

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="BG3 Tracker">
<meta name="theme-color" content="#1a0a0a">
<title>BG3 Honor Mode Tracker</title>
<style>
:root{--bg:#0d0d0d;--sf:#1a1a1a;--sf2:#252525;--bd:#333;--tx:#e0d8c8;--txd:#8a8070;--ac:#c4a24e;--acg:#e8c84a;--ach:#8b5cf6;--achb:#a78bfa;--chk:#4ade80;--chkd:#166534;--dng:#ef4444;--pbg:#2a2218;--pf:#c4a24e}
*{margin:0;padding:0;box-sizing:border-box}
html{background:var(--bg)}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--tx);line-height:1.55;padding-bottom:100px;-webkit-text-size-adjust:100%}
.hdr{position:sticky;top:0;z-index:100;background:rgba(13,13,13,.95);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);padding:calc(env(safe-area-inset-top,0px)+8px) 16px 10px;border-bottom:1px solid var(--bd)}
.hdr-t{font-size:15px;font-weight:700;color:var(--ac);letter-spacing:.5px;text-transform:uppercase;margin-bottom:6px}
.pb-w{background:var(--pbg);border-radius:6px;height:10px;overflow:hidden;margin-bottom:4px}
.pb-f{height:100%;background:linear-gradient(90deg,var(--ac),var(--acg));border-radius:6px;transition:width .4s;width:0%}
.pt{font-size:12px;color:var(--txd);display:flex;justify-content:space-between}
.tb{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.tb button{font-size:12px;padding:5px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--sf);color:var(--tx);cursor:pointer;white-space:nowrap;-webkit-tap-highlight-color:transparent}
.tb button:active{background:var(--sf2)}
.tb .rb{background:var(--ac);color:#000;border-color:var(--ac);font-weight:600}
.tb .rb:active{background:var(--acg)}
.tb .db{border-color:var(--dng);color:var(--dng)}
.ct{padding:12px 12px 0}
.sec{margin-bottom:12px;border:1px solid var(--bd);border-radius:10px;overflow:hidden;background:var(--sf)}
.sec.done{border-color:var(--chkd)}
.sh{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;cursor:pointer;-webkit-tap-highlight-color:transparent;user-select:none;gap:10px}
.sh:active{background:var(--sf2)}
.sn{font-size:15px;font-weight:600;color:var(--ac);flex:1}
.sec.done .sn{color:var(--chk)}
.sc{font-size:13px;color:var(--txd);font-variant-numeric:tabular-nums;white-space:nowrap}
.sec.done .sc{color:var(--chk)}
.cv{font-size:14px;color:var(--txd);transition:transform .2s;flex-shrink:0}
.sec.op .cv{transform:rotate(90deg)}
.sb{display:none;padding:0 14px 14px}
.sec.op .sb{display:block}
.st{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--bd);align-items:flex-start}
.st:last-child{border-bottom:none}
.st.ck .st-t{color:var(--txd);text-decoration:line-through;text-decoration-color:var(--txd)}
.st-c{width:22px;height:22px;border:2px solid var(--bd);border-radius:5px;flex-shrink:0;display:flex;align-items:center;justify-content:center;cursor:pointer;margin-top:1px;-webkit-tap-highlight-color:transparent;transition:all .15s}
.st.ck .st-c{background:var(--chk);border-color:var(--chk)}
.st.ck .st-c::after{content:"\2713";color:#000;font-size:14px;font-weight:700}
.st-t{flex:1;font-size:14px;line-height:1.5}
.st.ach{border-left:3px solid var(--achb);padding-left:10px;margin-left:-2px;background:rgba(139,92,246,.06);border-radius:0 6px 6px 0}
.st.ach .st-t{color:#c4b5fd}
.st.ach.ck .st-t{color:var(--txd)}
.st.tbl .st-t{font-family:"SF Mono",Menlo,Monaco,monospace;font-size:11px;white-space:pre-wrap;line-height:1.35;background:var(--sf2);padding:10px;border-radius:6px;overflow-x:auto}
.st.hl{animation:hlp 1.5s ease}
@keyframes hlp{0%{background:rgba(196,162,78,.3)}100%{background:transparent}}
.mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;align-items:center;justify-content:center;padding:20px}
.mo.sh{display:flex}
.md{background:var(--sf);border:1px solid var(--bd);border-radius:14px;padding:24px;max-width:320px;width:100%;text-align:center}
.md h3{color:var(--dng);margin-bottom:10px;font-size:17px}
.md p{color:var(--txd);margin-bottom:18px;font-size:14px}
.mb{display:flex;gap:10px;justify-content:center}
.mb button{padding:8px 20px;border-radius:8px;border:1px solid var(--bd);font-size:14px;cursor:pointer}
.mb .cc{background:var(--sf2);color:var(--tx)}
.mb .cf{background:var(--dng);color:#fff;border-color:var(--dng)}
</style>
</head>
<body>
<div class="hdr">
<div class="hdr-t">BG3 Honor Mode / Dark Urge</div>
<div class="pb-w"><div class="pb-f" id="pf"></div></div>
<div class="pt"><span id="pc">0/0</span><span id="pp">0%</span></div>
<div class="tb">
<button class="rb" onclick="resume()">&#9654; Resume</button>
<button onclick="expAll()">Expand All</button>
<button onclick="colAll()">Collapse All</button>
<button class="db" onclick="showR()">Reset</button>
</div>
</div>
<div class="ct" id="ct"></div>
<div class="mo" id="rm">
<div class="md">
<h3>Reset Progress?</h3>
<p>This will uncheck all steps and cannot be undone.</p>
<div class="mb">
<button class="cc" onclick="hideR()">Cancel</button>
<button class="cf" onclick="doReset()">Reset All</button>
</div>
</div>
</div>
<script>
var K="bg3HonorDarkUrgeTrackerData",S=%%SECTIONS%%,st=ld();
function ld(){try{var r=localStorage.getItem(K);if(r)return JSON.parse(r)}catch(e){}return{}}
function sv(){try{localStorage.setItem(K,JSON.stringify(st))}catch(e){}}
function ky(a,b){return a+":"+b}
function ic(a,b){return!!st[ky(a,b)]}
function sc(a,b,v){var k=ky(a,b);if(v)st[k]=1;else delete st[k];sv()}
function esc(s){var d=document.createElement("div");d.appendChild(document.createTextNode(s));return d.innerHTML}
function render(){
var ct=document.getElementById("ct");ct.innerHTML="";var tt=0,tc=0;
S.forEach(function(sec,si){
var d=document.createElement("div");d.className="sec";d.id="s"+si;
var sc2=0,st2=sec.chunks.length;
sec.chunks.forEach(function(_,ci){tt++;if(ic(si,ci)){tc++;sc2++}});
if(sc2===st2)d.classList.add("done");
var h=document.createElement("div");h.className="sh";
h.innerHTML='<span class="sn">'+esc(sec.name)+'</span><span class="sc">'+(sc2===st2?"\u2713 ":"")+sc2+"/"+st2+'</span><span class="cv">\u25B6</span>';
h.onclick=function(){d.classList.toggle("op")};d.appendChild(h);
var b=document.createElement("div");b.className="sb";
sec.chunks.forEach(function(ch,ci){
var s=document.createElement("div");s.className="st";s.id="t"+si+"-"+ci;
if(ic(si,ci))s.classList.add("ck");
if(ch.type==="achievement")s.classList.add("ach");
else if(ch.type==="table")s.classList.add("tbl");
var cb=document.createElement("div");cb.className="st-c";
cb.onclick=function(e){e.stopPropagation();var nw=!ic(si,ci);sc(si,ci,nw);
if(nw)s.classList.add("ck");else s.classList.remove("ck");updSec(si);updProg()};
s.appendChild(cb);
var tx=document.createElement("div");tx.className="st-t";
if(ch.type==="achievement")tx.innerHTML='\uD83C\uDFC6 '+esc(ch.content).replace(/\n/g,"<br>");
else tx.textContent=ch.content;
s.appendChild(tx);b.appendChild(s)});
d.appendChild(b);ct.appendChild(d)});
updD(tc,tt)}
function updSec(si){var sec=S[si],d=document.getElementById("s"+si),c=0;
sec.chunks.forEach(function(_,ci){if(ic(si,ci))c++});
var done=c===sec.chunks.length;
if(done)d.classList.add("done");else d.classList.remove("done");
d.querySelector(".sc").textContent=(done?"\u2713 ":"")+c+"/"+sec.chunks.length}
function updProg(){var t=0,c=0;S.forEach(function(sec,si){sec.chunks.forEach(function(_,ci){t++;if(ic(si,ci))c++})});updD(c,t)}
function updD(c,t){var p=t>0?Math.round(c/t*100):0;
document.getElementById("pf").style.width=p+"%";
document.getElementById("pc").textContent=c+"/"+t;
document.getElementById("pp").textContent=p+"%"}
function resume(){for(var si=0;si<S.length;si++){for(var ci=0;ci<S[si].chunks.length;ci++){
if(!ic(si,ci)){var sec=document.getElementById("s"+si);sec.classList.add("op");
var s=document.getElementById("t"+si+"-"+ci);
setTimeout(function(){s.scrollIntoView({behavior:"smooth",block:"center"});
s.classList.add("hl");setTimeout(function(){s.classList.remove("hl")},1600)},100);return}}}}
function expAll(){document.querySelectorAll(".sec").forEach(function(s){s.classList.add("op")})}
function colAll(){document.querySelectorAll(".sec").forEach(function(s){s.classList.remove("op")})}
function showR(){document.getElementById("rm").classList.add("sh")}
function hideR(){document.getElementById("rm").classList.remove("sh")}
function doReset(){st={};sv();hideR();render()}
render();
</script>
</body>
</html>'''

def gen_html(sections):
    sj = json.dumps(sections, ensure_ascii=False)
    return HTML_TEMPLATE.replace("%%SECTIONS%%", sj)

def main():
    text = read_file("walkthrough.txt")
    sections = build(text)
    total = sum(len(s["chunks"]) for s in sections)
    print(f"Parsed {len(sections)} sections, {total} total steps")
    for s in sections:
        ach = sum(1 for c in s["chunks"] if c["type"] == "achievement")
        tbl = sum(1 for c in s["chunks"] if c["type"] == "table")
        txt = sum(1 for c in s["chunks"] if c["type"] == "text")
        extra = ""
        if ach:
            extra += f", {ach} achievements"
        if tbl:
            extra += f", {tbl} tables"
        print(f"  {s['name']}: {len(s['chunks'])} steps ({txt} text{extra})")
    html = gen_html(sections)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated index.html ({len(html)} bytes)")

if __name__ == "__main__":
    main()
