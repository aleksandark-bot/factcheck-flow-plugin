#!/usr/bin/env python3
"""Local web-based keyword picker for /SEO (published-article path).

Opens a clean page in the browser showing the keyword lists with clickable controls,
and writes the user's selection back to a JSON file — no manual file editing.

Usage:
  keyword_picker.py --in <lists.json> --out <selection.json> [--port 0] [--no-open]

Input JSON:
  {
    "article_title": "...", "article_url": "...",
    "current_main": {"keyword": "...", "difficulty": <int|"N/A">, "volume": <int|null>},
    "lists": {
      "related":         [{"keyword","difficulty","volume","intent","why"}, ...],
      "variations":      [ ... same shape ... ],
      "competitor":      [ ... same shape ... ],
      "highly_relevant": [{"keyword","difficulty","volume","intent","relevance_rank"}, ...],
      "gsc_ranking":     [{"keyword","clicks","impressions","position","opportunity"}, ...]
    }
  }
  (Any list may be omitted or empty. gsc_ranking is absent for drafts.)

Output JSON (written to --out on Save):
  {
    "selected": [{"keyword","list","use_in_heading"}, ...],
    "new_main_keyword": "<keyword or null>"
  }

Blocks until the user clicks Save (or closes via the timeout). Exit 0 on save, 2 otherwise.
"""
import argparse, json, os, sys, threading, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>/SEO — choose keywords</title>
<style>
:root{--bg:#0f1220;--card:#181c2e;--line:#2a3050;--ink:#e7e9f2;--mut:#9aa3c0;--acc:#6ea8fe;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:#0f1220;color:#e7e9f2;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;background:#0f1220;border-bottom:1px solid #2a3050;padding:16px 24px;z-index:5}
h1{font-size:17px;margin:0 0 4px} .sub{color:#9aa3c0;font-size:13px}
.wrap{padding:20px 24px 120px;max-width:1100px;margin:0 auto}
h2{font-size:15px;margin:26px 0 8px;color:#cdd3ee;border-left:3px solid #6ea8fe;padding-left:8px}
table{width:100%;border-collapse:collapse;background:#181c2e;border:1px solid #2a3050;border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid #232946;font-size:14px}
th{color:#9aa3c0;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:none}
tr:hover td{background:#1d2237}
.kw{font-weight:600} .why{color:#9aa3c0;font-size:12px}
select{background:#0f1220;color:#e7e9f2;border:1px solid #2a3050;border-radius:7px;padding:6px 8px;font:inherit}
select.on{border-color:#3fb950;color:#fff}
.num{font-variant-numeric:tabular-nums;color:#c9d1e6}
.curmain{margin-top:24px;padding:12px 14px;background:#181c2e;border:1px solid #2a3050;border-radius:10px}
.cmeta{color:#9aa3c0;font-size:13px;margin-left:10px;font-variant-numeric:tabular-nums}
.newmain{display:flex;gap:10px;align-items:center;margin-top:8px}
.bar{position:fixed;left:0;right:0;bottom:0;background:#12162a;border-top:1px solid #2a3050;padding:14px 24px;display:flex;gap:14px;align-items:center;justify-content:flex-end}
.count{margin-right:auto;color:#9aa3c0}
button{background:#6ea8fe;color:#0b0e18;border:0;border-radius:9px;padding:11px 22px;font:600 15px system-ui;cursor:pointer}
button:hover{filter:brightness(1.08)} .done{color:#3fb950;font-weight:600}
a{color:#6ea8fe}
</style></head><body>
<header><h1>Choose keywords to optimize for</h1>
<div class="sub" id="meta"></div></header>
<div class="wrap" id="lists"></div>
<div class="bar"><span class="count" id="count"></span>
  <span id="msg"></span>
  <button id="save">Save &amp; return to Claude</button></div>
<script>
const DATA = /*__DATA__*/{};
const LABELS = {related:"Related keywords",variations:"Main keyword variations",competitor:"Competitor keywords",highly_relevant:"Highly relevant",gsc_ranking:"Already ranking (GSC)"};
const lists = document.getElementById('lists');
document.getElementById('meta').innerHTML = (DATA.article_title? '<b>'+esc(DATA.article_title)+'</b> — ':'') +
  (DATA.article_url? '<a href="'+esc(DATA.article_url)+'" target="_blank">'+esc(DATA.article_url)+'</a>':'');
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
const allKw=[]; const roleSel={};
for(const key of ["related","variations","competitor","highly_relevant","gsc_ranking"]){
  const rows=(DATA.lists||{})[key]; if(!rows||!rows.length) continue;
  const h=document.createElement('h2'); h.textContent=LABELS[key]+" ("+rows.length+")"; lists.appendChild(h);
  const gsc = key==="gsc_ranking";
  const t=document.createElement('table');
  t.innerHTML="<thead><tr><th>Keyword</th>"+(gsc?"<th>Clicks</th><th>Impr.</th><th>Pos.</th>":"<th>Diff.</th><th>Vol.</th><th>Intent</th>")+"<th>Use as</th></tr></thead>";
  const tb=document.createElement('tbody');
  rows.forEach((r,i)=>{
    const id=key+"::"+r.keyword; allKw.push({id,keyword:r.keyword,list:key});
    const tr=document.createElement('tr');
    const meta = gsc
      ? "<td class=num>"+(r.clicks??"")+"</td><td class=num>"+(r.impressions??"")+"</td><td class=num>"+(r.position??"")+"</td>"
      : "<td class=num>"+(r.difficulty??"N/A")+"</td><td class=num>"+(r.volume??"")+"</td><td>"+esc(r.intent||"")+"</td>";
    const why = r.why||r.opportunity;
    tr.innerHTML="<td><span class=kw>"+esc(r.keyword)+"</span>"+(why?"<br><span class=why>"+esc(why)+"</span>":"")+"</td>"+meta+
      "<td><select data-id='"+esc(id)+"'><option value=''>— skip —</option><option value='text'>Text</option><option value='heading'>Heading</option><option value='faq'>FAQ</option></select></td>";
    tb.appendChild(tr);
  });
  t.appendChild(tb); lists.appendChild(t);
}
// current focus keyphrase (Yoast) — shown directly above the new-main selector
if(DATA.current_main && DATA.current_main.keyword){
  const cm=document.createElement('div'); cm.className='curmain';
  const d=DATA.current_main.difficulty, v=DATA.current_main.volume;
  cm.innerHTML="<b>Current focus keyphrase:</b> <span class=kw>"+esc(DATA.current_main.keyword)+"</span>"+
    "<span class=cmeta>Difficulty "+esc(d==null?'N/A':d)+" · Volume "+esc(v==null?'N/A':v)+"</span>";
  lists.appendChild(cm);
}
// new-main selector
const nm=document.createElement('div'); nm.className='newmain';
nm.innerHTML="<b>New main keyword:</b> <select id='newmain'><option value=''>— keep current —</option>"+
  allKw.map(k=>"<option value='"+esc(k.id)+"'>"+esc(k.keyword)+"</option>").join("")+"</select>"+
  "<span class=why>(applied to H1, intro, meta description & SEO title — implies a heading)</span>";
lists.appendChild(nm);
function refresh(){
  let n=0; document.querySelectorAll('select[data-id]').forEach(s=>{s.classList.toggle('on',!!s.value); if(s.value)n++;});
  document.getElementById('count').textContent=n+" keyword"+(n==1?"":"s")+" selected";
}
document.addEventListener('change',refresh); refresh();
document.getElementById('save').onclick=async()=>{
  const selected=[];
  document.querySelectorAll('select[data-id]').forEach(s=>{ if(s.value){const [list,...kw]=s.dataset.id.split("::");
    selected.push({keyword:kw.join("::"),list:list,use_in_heading:s.value==='heading',use_as_faq:s.value==='faq'});}});
  let newMain=null; const nmv=document.getElementById('newmain').value;
  if(nmv){const [list,...kw]=nmv.split("::"); newMain=kw.join("::");
    // ensure the new-main keyword is selected + heading (new main is never an FAQ)
    if(!selected.find(x=>x.keyword===newMain)) selected.push({keyword:newMain,list:list,use_in_heading:true,use_as_faq:false});
    else selected.forEach(x=>{if(x.keyword===newMain){x.use_in_heading=true;x.use_as_faq=false;}});}
  const payload={selected:selected,new_main_keyword:newMain};
  document.getElementById('msg').textContent="Saving…";
  try{await fetch('/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    document.getElementById('msg').innerHTML="<span class=done>Saved. You can close this tab and return to Claude.</span>";
    document.getElementById('save').disabled=true;
  }catch(e){document.getElementById('msg').textContent="Error saving — is Claude still running?";}
};
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    with open(a.infile) as f:
        data = f.read()
    # sanity-parse
    json.loads(data)
    page = PAGE.replace("/*__DATA__*/{}", data)

    state = {"done": False}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep stdout clean
            pass

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            if self.path != "/submit":
                self.send_response(404); self.end_headers(); return
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n)
            try:
                sel = json.loads(raw)
            except Exception:
                self.send_response(400); self.end_headers(); return
            with open(a.outfile, "w") as f:
                json.dump(sel, f, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            state["done"] = True

    httpd = HTTPServer(("127.0.0.1", a.port), H)
    port = httpd.server_address[1]
    url = "http://127.0.0.1:%d/" % port
    sys.stderr.write("Keyword picker at %s\n" % url)

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    if not a.no_open:
        opener = (["xdg-open", url] if _has("xdg-open")
                  else ["google-chrome", url] if _has("google-chrome")
                  else ["firefox", url] if _has("firefox") else None)
        if opener:
            try:
                subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    deadline = time.time() + a.timeout
    while not state["done"] and time.time() < deadline:
        time.sleep(0.25)
    httpd.shutdown()
    if state["done"]:
        print("SELECTION_SAVED " + a.outfile)
        sys.exit(0)
    sys.stderr.write("picker timed out with no selection\n")
    sys.exit(2)


def _has(cmd):
    from shutil import which
    return which(cmd) is not None


if __name__ == "__main__":
    main()
