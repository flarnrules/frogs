#!/usr/bin/env python3
"""
bootloader pixel-art engine — one-shot runner
PNG/layers → RLE payload → bootloader snippet (minified)

Effects are probabilistic with strength ranges:
- Hue anim (prob, period range) — continuous loop
- Glitch: turbulence displacement (prob, amp & period)
- Glitch: chromatic aberration (prob, dx/dy)
- Glitch: film grain (prob, amount)
- Glitch: fray/smear (prob, direction, shift & density)  [NEW]
- Recursion per-channel (prob, mode weights, some_frac range, cap)

Compat: ES5 only, no backticks or //, no literal http://, whitespace-only minify.
"""

from __future__ import annotations
import json, re, argparse, random, colorsys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image

# ───────── CONFIG ─────────
CONFIG = {
    "GENERATOR": "sample",
    "INPUT_MODE": "auto",            # "auto" | "png" | "layers"
    "MAX_COLORS": 32,
    "TRIM_TRANSPARENT": True,
    "BACKGROUND_HEX": None,          # e.g. "#000" to replace alpha; None keep transparency
    "PROJECTS_ROOT": "../projects",
    "OUT_ROOT": "../out",

    # base transforms sampled per mint
    "FLIPX_PROB": 0.50,
    "FLIPY_PROB": 0.00,
    "ROT90_PROB": 0.00,

    # render mode for primitives
    "RENDER_MODE": "gradient",       # "rect" | "gradient"

    # seeded palette harmony (global hue shift + sat/lum scaling)
    "HUE_SHIFT_DEG_MIN": 0,
    "HUE_SHIFT_DEG_MAX": 360,
    "SAT_SCALE_MIN": 0.25,
    "SAT_SCALE_MAX": 2.05,
    "LUM_SCALE_MIN": 0.97,
    "LUM_SCALE_MAX": 1.03,

    # Probabilistic effects and ranges (all sampled inside the bootloader with the seed)
    "FX": {
        "hue_anim": {"prob": 0.4, "period_min": 1, "period_max": 14},
        "glitch_turb": {"prob": 0.4, "amp_min": 0.1, "amp_max": 5.5, "period_min": 1, "period_max": 12},
        "glitch_aberr": {"prob": 0.4, "dx_min": 0.0, "dx_max": 1.6, "dy_min": -1.25, "dy_max": 1.25},
        "glitch_noise": {"prob": 0.7, "amount_min": 0.02, "amount_max": 0.82},

        # NEW: directional fray/smear (edge tearing / bleed)
        # dir: "top" | "right" | "bottom" | "left" | "random"
        "glitch_fray": {"prob": 0.4, "dir": "random", "shift_min": 0.3, "shift_max": 2.6, "density_min": 0.25, "density_max": 1.75},

        "recursion": {
            "prob": 0.20,
            "mode_weights": {"one": 0.35, "some": 0.45, "all": 0.20},
            "some_frac_min": 0.2, "some_frac_max": 0.6,
            "max_pixels": 20000
        }
    }
}

# ───────── helpers ─────────
def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)
def to_hex(rgb: Tuple[int,int,int]) -> str: return "#{:02x}{:02x}{:02x}".format(*rgb)
def base36(n:int)->str:
    chars="0123456789abcdefghijklmnopqrstuvwxyz"
    if n==0: return "0"
    s=""; m=abs(n)
    while m>0:
        m,r = divmod(m,36); s = chars[r]+s
    return s if n>=0 else "-"+s
def parse_hex_color(s: Optional[str]) -> Optional[Tuple[int,int,int]]:
    if not s: return None
    t = s.strip().lstrip("#")
    if len(t)==3: t = "".join(ch*2 for ch in t)
    if len(t)!=6: raise ValueError("bg color must be 3 or 6 hex digits")
    return (int(t[0:2],16), int(t[2:4],16), int(t[4:6],16))
def quantize(img: Image.Image, max_colors: Optional[int]) -> Image.Image:
    im = img.convert("RGBA")
    if not max_colors: return im
    return im.quantize(colors=max_colors, method=Image.FASTOCTREE, dither=Image.Dither.NONE).convert("RGBA")
def trim_alpha(img: Image.Image, thresh:int=0) -> Image.Image:
    bbox = img.split()[-1].point(lambda a: 255 if a>thresh else 0).getbbox()
    return img.crop(bbox) if bbox else img
def stack_layers(layer_paths: List[Path]) -> Image.Image:
    if not layer_paths: raise ValueError("No layer PNGs found.")
    base = Image.open(layer_paths[0]).convert("RGBA"); w,h = base.size
    for p in layer_paths[1:]:
        im = Image.open(p).convert("RGBA")
        if im.size != (w,h): raise ValueError(f"Layer size mismatch: {p.name} is {im.size}, expected {(w,h)}")
        base.alpha_composite(im)
    return base

def png_to_runs(img: Image.Image, max_colors: Optional[int], trim: bool, treat_transparent_as: Optional[Tuple[int,int,int]]):
    im = quantize(img, max_colors)
    if trim: im = trim_alpha(im)
    w,h = im.size; px = im.load()
    palette: List[Tuple[int,int,int]] = []; pindex = {}; runs = []
    def idx_of(rgb: Tuple[int,int,int]):
        if rgb not in pindex:
            pindex[rgb] = len(palette); palette.append(rgb)
        return pindex[rgb]
    for y in range(h):
        row = []
        r,g,b,a = px[0,y]
        cur = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
        length = 1
        for x in range(1,w):
            r,g,b,a = px[x,y]
            c = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
            if c == cur:
                length += 1
            else:
                row.append([length, idx_of(cur)])
                cur, length = c, 1
        row.append([length, idx_of(cur)])
        runs.append(row)
    pal_hex = [to_hex(rgb) for rgb in palette]
    return {"w": w, "h": h, "palette": pal_hex, "runs": runs}

def pack_blob(model: dict) -> str:
    w,h = model["w"], model["h"]
    rows = model["runs"]
    p = "P:" + ",".join(model["palette"])
    rparts=[]
    for row in rows:
        rparts.append(",".join(f"{base36(L)}.{base36(i)}" for (L,i) in row))
    r = "R:" + ";".join(rparts)
    return f"{base36(w)},{base36(h)}|{p}|{r}"

# ───────── bootloader template (ES5, no backticks/ //, http avoided) ─────────
BOOTLOADER_TEMPLATE = (
"(function(){"
"var D=BTLDR&&BTLDR.svg?BTLDR.svg:null; if(!D){throw new Error('BTLDR.svg missing');}"
"var NS='http:'+'\\x2F\\x2Fwww.w3.org/2000/svg';"
"function E(t,a){var e=document.createElementNS(NS,t);if(a){for(var k in a){if(a.hasOwnProperty(k)){e.setAttribute(k,String(a[k]));}}}return e;}"
"var PAYLOAD='__PAYLOAD__';"
"var BASE_PAL=__BASE_PAL__;"
"var PROBS=__PROBS__;"
"var MODE='__RENDER_MODE__';"
"var VAR=__VAR_CFG__;"
"var FX=__FX_CFG__;"
"var parts=PAYLOAD.split('|'); var wh=parts[0], rr=parts[2];"
"function i36(s){var n=parseInt(s,36);return isNaN(n)?0:n;}"
"var whp=wh.split(','); var W=i36(whp[0])||parseInt(whp[0],10); var H=i36(whp[1])||parseInt(whp[1],10);"
"var rstr=rr.indexOf('R:')===0? rr.slice(2) : rr;"
"var rows=(function(){var RWS=rstr.split(';'), out=[], i,j,tok,li,row; for(i=0;i<RWS.length;i++){ if(!RWS[i]){continue;} var toks=RWS[i].split(','); row=[]; for(j=0;j<toks.length;j++){ tok=toks[j]; if(!tok){continue;} li=tok.split('.'); row.push([i36(li[0]), i36(li[1])]); } out.push(row);} return out;})();"
"function R(){ try{return (typeof BTLDR!=='undefined' && typeof BTLDR.rnd==='function')?BTLDR.rnd():Math.random();}catch(_){return Math.random();} }"
"function clamp01(x){return x<0?0:(x>1?1:x);} "
"function rotHex(hex,deg,ss,ll){var hx=(hex+'').replace('#',''); if(hx.length===3){hx=hx.charAt(0)+hx.charAt(0)+hx.charAt(1)+hx.charAt(1)+hx.charAt(2)+hx.charAt(2);} var r=parseInt(hx.substr(0,2),16)/255, g=parseInt(hx.substr(2,2),16)/255, b=parseInt(hx.substr(4,2),16)/255; var maxV=r>g?(r>b?r:b):(g>b?g:b), minV=r<g?(r<b?r:b):(g<b?g:b); var h=0,s=0,l=(maxV+minV)/2; var d=maxV-minV; if(d!==0){ s=l>0.5? d/(2-maxV-minV) : d/(maxV+minV); if(maxV===r){ h=(g-b)/d + (g<b?6:0);} else if(maxV===g){ h=(b-r)/d + 2;} else { h=(r-g)/d + 4;} h/=6; } h=(h+(deg/360))%1; s=clamp01(s*ss); l=clamp01(l*ll); var q=l<0.5? l*(1+s) : l+s-l*s; var p=2*l-q; function Hc(t){ if(t<0)t+=1; if(t>1)t-=1; if(t<1/6)return p+(q-p)*6*t; if(t<1/2)return q; if(t<2/3)return p+(q-p)*(2/3-t)*6; return p;} var rr=Math.round(Hc(h+1/3)*255), gg=Math.round(Hc(h)*255), bb=Math.round(Hc(h-1/3)*255); function hx2(n){var s=n.toString(16); return s.length<2?('0'+s):s;} return '#'+hx2(rr)+hx2(gg)+hx2(bb);} "
"function pickRange(lo,hi){ var t=R(); return lo+(hi-lo)*t; } "
"function pickWeighted(w){ var s=0,k; for(k in w){ if(w.hasOwnProperty(k)){ s+=w[k]; } } var r=s*R(), acc=0; for(k in w){ if(w.hasOwnProperty(k)){ acc+=w[k]; if(r<=acc) return k; } } return k; } "
"var shift=pickRange((VAR&&VAR.hmin!=null)?VAR.hmin:0,(VAR&&VAR.hmax!=null)?VAR.hmax:360); "
"var ss=pickRange((VAR&&VAR.smin!=null)?VAR.smin:1,(VAR&&VAR.smax!=null)?VAR.smax:1); "
"var ll=pickRange((VAR&&VAR.lmin!=null)?VAR.lmin:1,(VAR&&VAR.lmax!=null)?VAR.lmax:1); "
"var palette=(function(){var i, out=[]; for(i=0;i<BASE_PAL.length;i++){ out.push(rotHex(BASE_PAL[i], shift, ss, ll)); } return out;})(); "
"var maxIdx=0; var y, r, k; for(y=0;y<rows.length;y++){ r=rows[y]; for(k=0;k<r.length;k++){ if(r[k][1]>maxIdx){maxIdx=r[k][1];}}} if(!(palette.length>maxIdx)){throw new Error('Palette too small');} "
"var flipX=R()<((PROBS&&PROBS.flipx)||0), flipY=R()<((PROBS&&PROBS.flipy)||0), rot90=R()<((PROBS&&PROBS.rot90)||0); "
"var vw=rot90?H:W, vh=rot90?W:H; "
"D.setAttribute('viewBox','0 0 '+vw+' '+vh); D.setAttribute('preserveAspectRatio','xMidYMid meet'); D.setAttribute('width','100%'); D.setAttribute('height','100%'); D.setAttribute('overflow','visible'); "
"var Root=E('g',{}); D.appendChild(Root); "
"var ST=E('style',{}); ST.textContent='*{shape-rendering:crispEdges}'; Root.appendChild(ST); "

"function buildFilter(){ var last='SourceGraphic', has=false; var F=E('filter',{id:'fx'}); "
"  if(FX && FX.hue_anim && R()<FX.hue_anim.prob){ var pmin=FX.hue_anim.period_min||8, pmax=FX.hue_anim.period_max||14; var per=String(pickRange(pmin,pmax)); var M=E('feColorMatrix',{in:last,type:'hueRotate',values:'0',result:'hue'}); var A=document.createElementNS(NS,'animate'); A.setAttribute('attributeName','values'); A.setAttribute('values','0;360'); A.setAttribute('dur',per+'s'); A.setAttribute('repeatCount','indefinite'); M.appendChild(A); F.appendChild(M); last='hue'; has=true; } "
"  if(FX && FX.glitch_turb && R()<FX.glitch_turb.prob){ var amin=FX.glitch_turb.amp_min||0.5, amax=FX.glitch_turb.amp_max||2.5; var pmin2=FX.glitch_turb.period_min||3, pmax2=FX.glitch_turb.period_max||8; var amp=String(pickRange(amin,amax)); var per2=String(pickRange(pmin2,pmax2)); var T=E('feTurbulence',{'type':'turbulence','baseFrequency':'0.02','numOctaves':'1','seed':'1','result':'n'}); var Ag=document.createElementNS(NS,'animate'); Ag.setAttribute('attributeName','seed'); Ag.setAttribute('values','0;6;0'); Ag.setAttribute('dur',per2+'s'); Ag.setAttribute('repeatCount','indefinite'); T.appendChild(Ag); F.appendChild(T); var Dm=E('feDisplacementMap',{'in':last,'in2':'n','scale':amp,'xChannelSelector':'R','yChannelSelector':'G','result':'gl'}); F.appendChild(Dm); last='gl'; has=true; } "
"  if(FX && FX.glitch_aberr && R()<FX.glitch_aberr.prob){ var dx=String(pickRange(FX.glitch_aberr.dx_min||0, FX.glitch_aberr.dx_max||0.6)); var dy=String(pickRange(FX.glitch_aberr.dy_min||-0.25, FX.glitch_aberr.dy_max||0.25)); var Rm=E('feColorMatrix',{'in':last,'type':'matrix','values':'1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0','result':'r1'}); var Gm=E('feColorMatrix',{'in':last,'type':'matrix','values':'0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0','result':'g1'}); var Bm=E('feColorMatrix',{'in':last,'type':'matrix','values':'0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0','result':'b1'}); F.appendChild(Rm); F.appendChild(Gm); F.appendChild(Bm); var Ro=E('feOffset',{'in':'r1','dx':dx,'dy':dy,'result':'r2'}); var Go=E('feOffset',{'in':'g1','dx':'0','dy':'0','result':'g2'}); var Bo=E('feOffset',{'in':'b1','dx':'-'+dx,'dy':'-'+dy,'result':'b2'}); F.appendChild(Ro); F.appendChild(Go); F.appendChild(Bo); var C1=E('feComposite',{'in':'r2','in2':'g2','operator':'lighter','result':'rg'}); var C2=E('feComposite',{'in':'rg','in2':'b2','operator':'lighter','result':'rgb'}); F.appendChild(C1); F.appendChild(C2); last='rgb'; has=true; } "
"  if(FX && FX.glitch_noise && R()<FX.glitch_noise.prob){ var amt=String(Math.max(0,Math.min(1,pickRange(FX.glitch_noise.amount_min||0.02, FX.glitch_noise.amount_max||0.12)))); var Nt=E('feTurbulence',{'type':'fractalNoise','baseFrequency':'0.9','numOctaves':'1','seed':'2','result':'grain'}); F.appendChild(Nt); var Na=E('feColorMatrix',{'in':'grain','type':'matrix','values':'1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 '+amt+' 0','result':'grainA'}); F.appendChild(Na); var Bn2=E('feBlend',{'in':last,'in2':'grainA','mode':'overlay','result':'noisy'}); F.appendChild(Bn2); last='noisy'; has=true; } "
"  if(FX && FX.glitch_fray && R()<FX.glitch_fray.prob){ var dir=FX.glitch_fray.dir||'random'; if(dir==='random'){ var dirs=['top','right','bottom','left']; dir=dirs[Math.floor(R()*dirs.length)]; } var sh=pickRange(FX.glitch_fray.shift_min||0.3, FX.glitch_fray.shift_max||1.6); var dens=pickRange(FX.glitch_fray.density_min||0.25, FX.glitch_fray.density_max||0.75); var dx='0', dy='0'; if(dir==='right'){ dx=String(sh); } else if(dir==='left'){ dx=String(-sh); } else if(dir==='bottom'){ dy=String(sh); } else if(dir==='top'){ dy=String(-sh); } var Off=E('feOffset',{'in':last,'dx':dx,'dy':dy,'result':'shifted'}); F.appendChild(Off); var Nt2=E('feTurbulence',{'type':'fractalNoise','baseFrequency':'0.8','numOctaves':'1','seed':'4','result':'n2'}); F.appendChild(Nt2); var thr=Math.max(0,min=1) || 0; var tlo=String(1-dens); var CM=E('feComponentTransfer',{'in':'n2','result':'mask'}); var Rf=document.createElementNS(NS,'feFuncR'); Rf.setAttribute('type','table'); Rf.setAttribute('tableValues','0 '+tlo+' 1'); var Gf=document.createElementNS(NS,'feFuncG'); Gf.setAttribute('type','table'); Gf.setAttribute('tableValues','0 '+tlo+' 1'); var Bf=document.createElementNS(NS,'feFuncB'); Bf.setAttribute('type','table'); Bf.setAttribute('tableValues','0 '+tlo+' 1'); var Af=document.createElementNS(NS,'feFuncA'); Af.setAttribute('type','table'); Af.setAttribute('tableValues','0 '+tlo+' 1'); CM.appendChild(Rf); CM.appendChild(Gf); CM.appendChild(Bf); CM.appendChild(Af); F.appendChild(CM); var Cut=E('feComposite',{'in':'shifted','in2':'mask','operator':'in','result':'frayBits'}); F.appendChild(Cut); var Over=E('feComposite',{'in':'frayBits','in2':last,'operator':'over','result':'frayed'}); F.appendChild(Over); last='frayed'; has=true; } "
"  if(has){ Root.setAttribute('filter','url(#fx)'); D.appendChild(F); } return has; } "

"function makeGroups(parent,useGradient){ var mp={},gi; if(useGradient){ var defsG=E('defs',{}); parent.appendChild(defsG); for(gi=0;gi<palette.length;gi++){ var id='g'+gi; var lg=E('linearGradient',{id:id,gradientUnits:'userSpaceOnUse',x1:'0',y1:'0',x2:String(vw),y2:'0'}); var c0=palette[gi], c1=palette[(gi+1)%palette.length]; var s0=E('stop',{'stop-color':c0,offset:'0%'}); var s1=E('stop',{'stop-color':c1,offset:'100%'}); lg.appendChild(s0); lg.appendChild(s1); defsG.appendChild(lg); mp[gi]=E('g',{fill:'url(#'+id+')'}); parent.appendChild(mp[gi]); } } else { for(gi=0;gi<palette.length;gi++){ mp[gi]=E('g',{fill:palette[gi]}); parent.appendChild(mp[gi]); } } return mp; } "
"function paintInto(groups){ var y2,x2,r2,k2,len,ci,x0,yy2,a,nx,ny; if(!rot90){ for(y2=0;y2<rows.length;y2++){ x2=0; r2=rows[y2]; yy2 = flipY ? (vh-1 - y2) : y2; for(k2=0;k2<r2.length;k2++){ len=r2[k2][0]; ci=r2[k2][1]; x0 = flipX ? (vw - (x2+len)) : x2; a=E('rect',{x:String(x0),y:String(yy2),width:String(len),height:'1'}); groups[ci].appendChild(a); x2+=len; } } } else { for(y2=0;y2<rows.length;y2++){ x2=0; r2=rows[y2]; for(k2=0;k2<r2.length;k2++){ len=r2[k2][0]; ci=r2[k2][1]; nx=(vh-1 - y2); ny=x2; if(flipX){ nx=(vh - 1) - nx; } if(flipY){ ny=(vw - len) - ny; } a=E('rect',{x:String(nx),y:String(ny),width:'1',height:String(len)}); groups[ci].appendChild(a); x2+=len; } } } } "
"function pickChannels(weights, frac){ var N=palette.length, arr=[], i; var mode=pickWeighted(weights||{'some':1}); if(mode==='all'){ for(i=0;i<N;i++){arr.push(i);} return arr; } if(mode==='one'){ arr.push(Math.floor(R()*N)); return arr; } var f=(frac!=null)?frac:0.4; for(i=0;i<N;i++){ if(R()<f){arr.push(i);} } if(arr.length===0){arr.push(Math.floor(R()*N));} return arr; } "
"function paintRectMode(){ var useGrad=(MODE==='gradient'); var G0=makeGroups(Root,useGrad); paintInto(G0); } "
"function paintRecursivePerChannel(rec){ var pix=W*H; if(pix>(rec.max_pixels||20000)){ paintRectMode(); return; } var defs=E('defs',{}); Root.appendChild(defs); var sym=E('symbol',{id:'T',viewBox:'0 0 '+W+' '+H}); defs.appendChild(sym); var Gs=makeGroups(sym,(MODE==='gradient')); paintInto(Gs); var someFrac=pickRange(rec.some_frac_min||0.2, rec.some_frac_max||0.6); var channels=(rec.mode_weights?pickChannels(rec.mode_weights, someFrac):pickChannels({'some':1}, someFrac)); var cmap={}, i; for(i=0;i<channels.length;i++){ cmap[channels[i]]=1; } var y3,x3,r3,k3,len3,ci3,x0,yy3,u,nx3,ny3,dx; if(!rot90){ for(y3=0;y3<rows.length;y3++){ x3=0; r3=rows[y3]; yy3 = flipY ? (H-1 - y3) : y3; for(k3=0;k3<r3.length;k3++){ len3=r3[k3][0]; ci3=r3[k3][1]; x0 = flipX ? (W - (x3+len3)) : x3; if(cmap[ci3]){ for(dx=0;dx<len3;dx++){ u=E('use',{'href':'#T',x:String(x0+dx),y:String(yy3),width:'1',height:'1'}); u.setAttribute('xlink:href','#T'); Root.appendChild(u);} } else { var a=E('rect',{x:String(x0),y:String(yy3),width:String(len3),height:'1'}); var gtmp=E('g',{fill:(MODE==='gradient'?'url(#g'+ci3+')':palette[ci3])}); gtmp.appendChild(a); Root.appendChild(gtmp); } x3+=len3; } } } else { for(y3=0;y3<rows.length;y3++){ x3=0; r3=rows[y3]; for(k3=0;k3<r3.length;k3++){ len3=r3[k3][0]; ci3=r3[k3][1]; nx3=(H-1 - y3); ny3=x3; if(flipX){ nx3=(H - 1) - nx3; } if(flipY){ ny3=(W - len3) - ny3; } if(cmap[ci3]){ for(dx=0;dx<len3;dx++){ u=E('use',{'href':'#T',x:String(nx3),y:String(ny3+dx),width:'1',height:'1'}); u.setAttribute('xlink:href','#T'); Root.appendChild(u);} } else { var a2=E('rect',{x:String(nx3),y:String(ny3),width:'1',height:String(len3)}); var gtmp2=E('g',{fill:(MODE==='gradient'?'url(#g'+ci3+')':palette[ci3])}); gtmp2.appendChild(a2); Root.appendChild(gtmp2); } x3+=len3; } } } } "
"var usedFilter = buildFilter(); "
"var doRec = false; if(FX && FX.recursion && R()<FX.recursion.prob){ doRec = true; } "
"if(doRec){ paintRecursivePerChannel(FX.recursion); } else { paintRectMode(); } "
"})();"
)

def minify_js(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# ───────── pipeline ─────────
def resolve_input(gen: str, projects_root: Path, input_mode: str, explicit_png: Optional[str], explicit_layers: Optional[str]) -> Image.Image:
    if explicit_png:
        p = Path(explicit_png)
        if not p.is_file(): raise FileNotFoundError(f"PNG not found: {p}")
        return Image.open(p).convert("RGBA")
    if explicit_layers:
        d = Path(explicit_layers)
        if not d.is_dir(): raise FileNotFoundError(f"Layers folder not found: {d}")
        layer_paths = sorted([p for p in d.iterdir() if p.suffix.lower()==".png"])
        if not layer_paths: raise FileNotFoundError(f"No PNGs in layers dir: {d}")
        return stack_layers(layer_paths)
    base_png = projects_root / gen / "input" / "base.png"
    layers_dir = projects_root / gen / "input" / "layers"
    if input_mode == "png":
        if not base_png.is_file(): raise FileNotFoundError(f"Expected PNG at {base_png}")
        return Image.open(base_png).convert("RGBA")
    if input_mode == "layers":
        if not layers_dir.is_dir(): raise FileNotFoundError(f"Expected layers at {layers_dir}")
        layer_paths = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
        if not layer_paths: raise FileNotFoundError(f"No PNGs in {layers_dir}")
        return stack_layers(layer_paths)
    if layers_dir.is_dir():
        layer_paths = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
        if layer_paths: return stack_layers(layer_paths)
    if base_png.is_file():
        return Image.open(base_png).convert("RGBA")
    raise FileNotFoundError(f"No input found under {projects_root/gen/'input'} (need base.png or layers/*.png)")

def run_pipeline(
    generator: str,
    projects_root: Path,
    out_root: Path,
    input_mode: str,
    max_colors: Optional[int],
    trim_transparent: bool,
    background_hex: Optional[str],
    cli_png: Optional[str],
    cli_layers: Optional[str],
):
    out_dir = out_root / generator
    ensure_dir(out_dir)
    img = resolve_input(generator, projects_root, input_mode, cli_png, cli_layers)
    treat_transparent = parse_hex_color(background_hex)
    model = png_to_runs(img, max_colors=max_colors, trim=trim_transparent, treat_transparent_as=treat_transparent)

    runs_path = out_dir / "runs.json"; packed_path = out_dir / "packed.txt"
    runs_path.write_text(json.dumps(model, separators=(',',':')))
    payload = pack_blob(model); packed_path.write_text(payload)

    BASE_PAL_JS = json.dumps(model["palette"], separators=(',',':'))
    PROBS_JS = json.dumps({"flipx": CONFIG["FLIPX_PROB"], "flipy": CONFIG["FLIPY_PROB"], "rot90": CONFIG["ROT90_PROB"]}, separators=(',',':'))
    FX_JS = json.dumps(CONFIG["FX"], separators=(',',':'))
    VARCFG = {
        "hmin": CONFIG["HUE_SHIFT_DEG_MIN"], "hmax": CONFIG["HUE_SHIFT_DEG_MAX"],
        "smin": CONFIG["SAT_SCALE_MIN"], "smax": CONFIG["SAT_SCALE_MAX"],
        "lmin": CONFIG["LUM_SCALE_MIN"], "lmax": CONFIG["LUM_SCALE_MAX"],
    }
    VARCFG_JS = json.dumps(VARCFG, separators=(',',':'))

    js = (BOOTLOADER_TEMPLATE
          .replace("__PAYLOAD__", payload.replace("\\","\\\\").replace("'","\\'"))
          .replace("__BASE_PAL__", BASE_PAL_JS)
          .replace("__PROBS__", PROBS_JS)
          .replace("__RENDER_MODE__", CONFIG.get("RENDER_MODE","rect"))
          .replace("__VAR_CFG__", VARCFG_JS)
          .replace("__FX_CFG__", FX_JS))
    js_min = minify_js(js)

    (out_dir / "bootloader_snippet.js").write_text(js)
    (out_dir / "bootloader_snippet.min.js").write_text(js_min)

    stats_path = out_dir / "stats.json"
    stats = {
        "generator": generator,
        "width": model["w"], "height": model["h"],
        "rows": len(model["runs"]), "palette_size": len(model["palette"]),
        "payload_bytes": len(payload.encode("utf-8")),
        "snippet_bytes": len(js.encode("utf-8")),
        "snippet_min_bytes": len(js_min.encode("utf-8")),
    }
    stats_path.write_text(json.dumps(stats, indent=2))

    print(f"[ok] {generator}: {model['w']}×{model['h']}, palette={len(model['palette'])}, rows={len(model['runs'])}")
    print(f"[out] {runs_path}")
    print(f"[out] {packed_path}")
    print(f"[out] {out_dir/'bootloader_snippet.js'}")
    print(f"[out] {out_dir/'bootloader_snippet.min.js'}")
    print(f"[out] {stats_path}")
    print(f"[bytes] payload={stats['payload_bytes']} | snippet={stats['snippet_bytes']} | min={stats['snippet_min_bytes']}")

# ───────── main ─────────
def main():
    here = Path(__file__).resolve().parent
    gen = CONFIG["GENERATOR"]; input_mode = CONFIG["INPUT_MODE"]; max_colors = CONFIG["MAX_COLORS"]
    trim_transparent = CONFIG["TRIM_TRANSPARENT"]; background_hex = CONFIG["BACKGROUND_HEX"]
    projects_root = (here / CONFIG["PROJECTS_ROOT"]).resolve()
    out_root = (here / CONFIG["OUT_ROOT"]).resolve()

    ap = argparse.ArgumentParser(description="projects/<GEN>/input → out/<GEN>/ bootloader snippet")
    ap.add_argument("-g","--generator", help=f"default: {gen}")
    ap.add_argument("--input-mode", choices=["auto","png","layers"], help=f"default: {input_mode}")
    ap.add_argument("--max-colors", type=int, help=f"default: {max_colors}")
    ap.add_argument("--no-trim", action="store_true", help="disable trimming transparent border")
    ap.add_argument("--bg", type=str, help="transparent → this hex (e.g. #000)")
    ap.add_argument("--png", type=str, help="explicit PNG path")
    ap.add_argument("--layers", type=str, help="explicit layers dir")
    ap.add_argument("--projects-root", type=str, help=f"default: {projects_root}")
    ap.add_argument("--out-root", type=str, help=f"default: {out_root}")
    args = ap.parse_args()

    if args.generator: gen = args.generator
    if args.input_mode: input_mode = args.input_mode
    if args.max_colors is not None: max_colors = args.max_colors
    if args.no_trim: trim_transparent = False
    if args.bg is not None: background_hex = args.bg
    if args.projects_root: projects_root = Path(args.projects_root).resolve()
    if args.out_root: out_root = Path(args.out_root).resolve()

    ensure_dir(out_root)
    run_pipeline(
        generator=gen,
        projects_root=projects_root,
        out_root=out_root,
        input_mode=input_mode,
        max_colors=max_colors,
        trim_transparent=trim_transparent,
        background_hex=background_hex,
        cli_png=args.png,
        cli_layers=args.layers,
    )

if __name__ == "__main__":
    main()
