#!/usr/bin/env python3
"""Local web-based SERP-result picker for /SEO (published-article path, Stage 1).

Opens a clean page in the browser listing the organic SERP results (each title a clickable
live link) with a checkbox per result, and writes the chosen URLs back to a JSON file.

Usage:
  serp_picker.py --in <serp.json> --out <selection.json> [--port 0] [--no-open]

Input JSON:
  { "main_keyword": "...",
    "serp": [ {"rank": 1, "title": "...", "url": "https://exact/live/page/"}, ... ] }

Output JSON (written on Save):
  { "selected_urls": ["https://...", ...],
    "structural_changes": "<free-text custom instructions for larger updates, or \"\">" }

Blocks until the user clicks Save — there is NO timeout window; it waits indefinitely
(press Ctrl+C to abort). Exit 0 on save, 2 otherwise.
"""
import argparse, json, sys, threading, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>/SEO — choose SERP results</title>
<style>
body{margin:0;background:#0f1220;color:#e7e9f2;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;background:#0f1220;border-bottom:1px solid #2a3050;padding:16px 24px;z-index:5}
h1{font-size:17px;margin:0 0 4px} .sub{color:#9aa3c0;font-size:13px}
.wrap{padding:18px 24px 120px;max-width:960px;margin:0 auto}
.tools{display:flex;gap:14px;align-items:center;margin:6px 0 14px;color:#9aa3c0;font-size:13px}
.tools a{color:#6ea8fe;cursor:pointer}
.row{display:flex;gap:12px;align-items:flex-start;background:#181c2e;border:1px solid #2a3050;border-radius:10px;padding:12px 14px;margin-bottom:8px}
.row:hover{background:#1d2237}
.row input{margin-top:3px;width:18px;height:18px;accent-color:#3fb950;cursor:pointer}
.rank{color:#9aa3c0;font-variant-numeric:tabular-nums;min-width:34px;font-size:13px;margin-top:1px}
.body{flex:1;min-width:0}
.title{font-weight:600}
.title a{color:#e7e9f2;text-decoration:none} .title a:hover{color:#6ea8fe;text-decoration:underline}
.url{color:#6ea8fe;font-size:12px;word-break:break-all;margin-top:2px;display:block}
.struct{margin-top:24px;background:#181c2e;border:1px solid #2a3050;border-radius:10px;padding:14px 16px}
.struct label{display:block;margin-bottom:8px}
.struct .hint{color:#9aa3c0;font-size:12px;font-weight:400}
.struct textarea{width:100%;background:#0f1220;color:#e7e9f2;border:1px solid #2a3050;border-radius:8px;padding:10px 12px;font:inherit;resize:vertical;min-height:100px}
.struct textarea:focus{outline:none;border-color:#6ea8fe}
.bar{position:fixed;left:0;right:0;bottom:0;background:#12162a;border-top:1px solid #2a3050;padding:14px 24px;display:flex;gap:14px;align-items:center;justify-content:flex-end}
.count{margin-right:auto;color:#9aa3c0}
button{background:#6ea8fe;color:#0b0e18;border:0;border-radius:9px;padding:11px 22px;font:600 15px system-ui;cursor:pointer}
button:hover{filter:brightness(1.08)} .done{color:#3fb950;font-weight:600}
</style></head><body>
<header><h1>Choose SERP results to mine for keywords &amp; entities</h1>
<div class="sub" id="meta"></div></header>
<div class="wrap">
  <div class="tools"><a id="all">Select all</a> · <a id="none">Select none</a>
    <span style="margin-left:auto">Tip: click a title to open the live page in a new tab.</span></div>
  <div id="rows"></div>
  <div class="struct">
    <label for="struct"><b>Structural changes</b>
      <span class="hint">Optional. Add any specific structural changes you want — format overhauls, section reordering, or a bigger rewrite the SERPs imply (e.g. our article is the wrong format for this query). The SEO updater will do these <b>and</b> add its own structural improvements on top. Leave blank to let it decide the structure itself — either way it will restructure where the SERP and intent call for it. No time limit — take as long as you need.</span></label>
    <textarea id="struct" placeholder="e.g. The top results are all step-by-step how-to guides, but our article is a thin listicle — restructure it into a numbered how-to with an intro, prerequisites, and ordered steps."></textarea>
  </div>
</div>
<div class="bar"><span class="count" id="count"></span><span id="msg"></span>
  <button id="save">Save &amp; return to Claude</button></div>
<script>
const DATA = /*__DATA__*/{};
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
document.getElementById('meta').textContent = DATA.main_keyword ? ('Ranking for: "'+DATA.main_keyword+'"') : '';
const rows=document.getElementById('rows');
(DATA.serp||[]).forEach((r,i)=>{
  const d=document.createElement('div'); d.className='row';
  d.innerHTML="<input type=checkbox data-url='"+esc(r.url)+"' id='c"+i+"'>"+
    "<span class=rank>#"+esc(r.rank??(i+1))+"</span>"+
    "<div class=body><div class=title><a href='"+esc(r.url)+"' target='_blank' rel='noopener'>"+esc(r.title||r.url)+"</a></div>"+
    "<a class=url href='"+esc(r.url)+"' target='_blank' rel='noopener'>"+esc(r.url)+"</a></div>";
  rows.appendChild(d);
});
function refresh(){const n=document.querySelectorAll('input[data-url]:checked').length;
  document.getElementById('count').textContent=n+" result"+(n==1?"":"s")+" selected";}
document.getElementById('all').onclick=()=>{document.querySelectorAll('input[data-url]').forEach(c=>c.checked=true);refresh();};
document.getElementById('none').onclick=()=>{document.querySelectorAll('input[data-url]').forEach(c=>c.checked=false);refresh();};
document.addEventListener('change',refresh); refresh();
document.getElementById('save').onclick=async()=>{
  const urls=[...document.querySelectorAll('input[data-url]:checked')].map(c=>c.dataset.url);
  const structural=(document.getElementById('struct').value||'').trim();
  document.getElementById('msg').textContent="Saving…";
  try{await fetch('/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({selected_urls:urls,structural_changes:structural})});
    document.getElementById('msg').innerHTML="<span class=done>Saved. Close this tab and return to Claude.</span>";
    document.getElementById('save').disabled=true;
  }catch(e){document.getElementById('msg').textContent="Error saving — is Claude still running?";}
};
</script></body></html>"""


def _has(cmd):
    from shutil import which
    return which(cmd) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--timeout", type=int, default=0,
                    help="seconds to wait for a selection; 0 = wait indefinitely (default, no timeout)")
    a = ap.parse_args()

    with open(a.infile) as f:
        data = f.read()
    json.loads(data)  # sanity
    page = PAGE.replace("/*__DATA__*/{}", data)
    state = {"done": False}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
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
            try:
                sel = json.loads(self.rfile.read(n))
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
    sys.stderr.write("SERP picker at %s\n" % url)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    if not a.no_open:
        opener = (["xdg-open", url] if _has("xdg-open")
                  else ["google-chrome", url] if _has("google-chrome")
                  else ["firefox", url] if _has("firefox") else None)
        if opener:
            try:
                subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    # No timeout window by default: wait indefinitely for the user's Save.
    deadline = None if a.timeout <= 0 else time.time() + a.timeout
    try:
        while not state["done"] and (deadline is None or time.time() < deadline):
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    if state["done"]:
        print("SELECTION_SAVED " + a.outfile)
        sys.exit(0)
    sys.stderr.write("serp picker exited with no selection\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
