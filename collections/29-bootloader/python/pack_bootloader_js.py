#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

TEMPLATE = """/**
 * bootloader: v0.0.1
 */
(()=>{const D=BTLDR.svg,E=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,a[k]);return e};
const S=`__PAYLOAD__`;
const [wh,pp,rr]=S.split('|');const [w,h]=wh.split(',').map(x=>parseInt(x,36)||parseInt(x,10));
const pal=pp.slice(2).split(',');const rows=rr.slice(2).split(';').map(r=>r? r.split(',').map(s=>{const [L,I]=s.split('.');return [parseInt(L,36),parseInt(I,36)];}) : []);
D.setAttribute('viewBox',`0 0 ${w} ${h}`);D.setAttribute('preserveAspectRatio','xMidYMid meet');D.setAttribute('width','100%');D.setAttribute('height','100%');D.setAttribute('overflow','visible');
const ST=E('style',{});ST.textContent='*{shape-rendering:crispEdges}';D.appendChild(ST);
const G={};pal.forEach((c,i)=>{const g=E('g',{fill:c});D.appendChild(g);G[i]=g;});
for(let y=0;y<rows.length;y++){let x=0;const r=rows[y];for(let k=0;k<r.length;k++){const len=r[k][0],ci=r[k][1];const a=E('rect',{x:String(x),y:String(y),width:String(len),height:'1'});G[ci].appendChild(a);x+=len;}}})();
"""

def minify_js(s: str) -> str:
    # brutal but safe for this template: drop linebreaks + tabs + leading spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def main():
    ap = argparse.ArgumentParser(description="Pack payload → bootloader snippet and size stats")
    ap.add_argument("--generator", "-g", required=True, help="generator name (matches out/<gen>)")
    ap.add_argument("--out-root", type=str, default=str(Path(__file__).resolve().parents[1] / "out"))
    args = ap.parse_args()

    out_dir = Path(args.out_root) / args.generator
    payload_path = out_dir / "packed.txt"
    if not payload_path.is_file():
        raise FileNotFoundError(f"missing {payload_path}. run raster_to_runs.py first.")

    payload = payload_path.read_text()
    js = TEMPLATE.replace("__PAYLOAD__", payload)
    js_min = minify_js(js)

    (out_dir / "bootloader_snippet.js").write_text(js)
    (out_dir / "bootloader_snippet.min.js").write_text(js_min)

    # sizes
    raw_bytes = len(js.encode("utf-8"))
    min_bytes = len(js_min.encode("utf-8"))
    payload_bytes = len(payload.encode("utf-8"))

    stats_path = out_dir / "stats.json"
    stats = {}
    if stats_path.is_file():
        stats = json.loads(stats_path.read_text())
    stats.update({
        "payload_bytes": payload_bytes,
        "snippet_bytes": raw_bytes,
        "snippet_min_bytes": min_bytes
    })
    stats_path.write_text(json.dumps(stats, indent=2))

    print(f"[ok] wrote: {out_dir/'bootloader_snippet.js'}")
    print(f"[ok] wrote: {out_dir/'bootloader_snippet.min.js'}")
    print(f"[stat] payload={payload_bytes}B snippet={raw_bytes}B min={min_bytes}B")

if __name__=="__main__":
    main()
