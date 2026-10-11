#!/usr/bin/env python3
"""Turn a 512x512 EDG8 PNG into a self-contained, springy SVG."""
import argparse
import json
import math
import re
from collections import defaultdict, deque
from pathlib import Path

from PIL import Image

# ── Edit these paths, then run: python3.11 svgize.py ─────────────────────────
# Relative folders are based on this script's folder. Absolute WSL paths work.
INPUT_FOLDER = "sample"       # Example: "/home/you/repos/frogs/collections/experiments/art"
INPUT_FILE = "experiment1.png"
OUTPUT_FOLDER = "output"      # Example: "/home/you/repos/frogs/collections/experiments/svg"
OUTPUT_FILE = "experiment1.svg"

# Use None to infer what is behind the foreground, or give a background PNG.
BACKGROUND_PNG = None         # Example: "art/experiment1-background.png"
EXPORT_BACKGROUND_PNG = None  # Example: "output/background-draft.png"
CONFIG_JSON = "effects.json"
ACTIVE_BOX = None             # Example: (120, 280, 440, 470); None animates all eligible art.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent


def configured_path(value):
    """Resolve script settings independently of the current shell folder."""
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else SCRIPT_DIR / path


def configured_file(folder, name):
    return configured_path(Path(folder).expanduser() / name)


PALETTE = (
    "#fdfdf8", "#d32734", "#da7d22", "#e6da29",
    "#28c641", "#2d93dd", "#7b53ad", "#1b1c33",
)
EFFECTS = {"still", "push", "swirl", "ripple", "jitter", "puff", "supernova"}


def load_config(path):
    data=json.loads(path.read_text(encoding="utf-8"))
    def number(value,label,minimum=0,maximum=None):
        if (isinstance(value,bool) or not isinstance(value,(int,float)) or
            not math.isfinite(value) or value<minimum or
            (maximum is not None and value>maximum)):
            raise ValueError(f"{label} must be a number from {minimum}"
                             + (f" to {maximum}" if maximum is not None else " or greater"))
    if set(data["colors"]) != set(PALETTE):
        raise ValueError("effects.json must define exactly the eight EDG8 colors")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", data["outer_background"]):
        raise ValueError("outer_background must be a six-digit hex color")
    for color, effect in data["colors"].items():
        if effect["effect"] not in EFFECTS:
            raise ValueError(f"{color}: effect must be one of {sorted(EFFECTS)}")
        for key in ("force", "noise", "chroma"):
            number(effect[key],f"{color}: {key}")
        if not isinstance(effect["include_edge"],bool):
            raise ValueError(f"{color}: include_edge must be true or false")
        if effect["effect"]=="puff":
            number(effect["fragment_size"],f"{color}: fragment_size",4)
            if int(effect["fragment_size"])!=effect["fragment_size"]:
                raise ValueError(f"{color}: fragment_size must be a whole number")
    for key in ("radius","strength","stiffness","damping","max_displacement",
                "squiggle","base_chroma","click_gain","trip_cap","trip_decay",
                "activation_margin","activation_ease","motion_decay","hover_force"):
        number(data["behavior"][key],f"behavior.{key}")
    number(data["behavior"]["damping"],"behavior.damping",0.001,0.999)
    number(data["behavior"]["trip_decay"],"behavior.trip_decay",0.001,0.99999)
    number(data["behavior"]["activation_margin"],"behavior.activation_margin",1)
    number(data["behavior"]["activation_ease"],"behavior.activation_ease",0.001,1)
    number(data["behavior"]["motion_decay"],"behavior.motion_decay",0.001,0.99999)
    number(data["behavior"]["base_chroma"],"behavior.base_chroma",0,1)
    number(data["max_bytes"],"max_bytes",1)
    for key in ("ray_count","ray_opacity","background_warp","decay",
                "rotation_speed","click_gain","cap"):
        number(data["supernova"][key],f"supernova.{key}")
    number(data["supernova"]["ray_count"],"supernova.ray_count",0,160)
    number(data["supernova"]["ray_opacity"],"supernova.ray_opacity",0,1)
    number(data["supernova"]["decay"],"supernova.decay",0.001,0.99999)
    for key in ("max_blur","click_gain","decay","cap"):
        number(data["cloud"][key],f"cloud.{key}")
    number(data["cloud"]["decay"],"cloud.decay",0.001,0.99999)
    return data


def components(pixels, width, height):
    """Return four-connected same-color pixel groups."""
    unseen = set(range(width * height))
    while unseen:
        start = unseen.pop()
        color = pixels[start]
        group = {start}
        queue = deque([start])
        while queue:
            i = queue.popleft()
            x, y = i % width, i // width
            for j in (i - 1 if x else -1, i + 1 if x + 1 < width else -1,
                      i - width if y else -1, i + width if y + 1 < height else -1):
                if j in unseen and pixels[j] == color:
                    unseen.remove(j)
                    group.add(j)
                    queue.append(j)
        yield color, group


def underpaint(pixels, width, height):
    """Extend edge-connected scenery beneath enclosed foreground shapes."""
    result=[None]*(width*height)
    queue=deque()
    for color,group in components(pixels,width,height):
        if any(i%width in (0,width-1) or i//width in (0,height-1) for i in group):
            for i in sorted(group):
                result[i]=color
                queue.append(i)
    if not queue:
        return [pixels[0]]*(width*height)
    while queue:
        i=queue.popleft()
        x,y=i%width,i//width
        for j in (i-1 if x else -1,i+1 if x+1<width else -1,
                  i-width if y else -1,i+width if y+1<height else -1):
            if j>=0 and result[j] is None:
                result[j]=result[i]
                queue.append(j)
    return result


def fragments(group,width,size):
    """Split one color region into small cells for cloud breakup."""
    cells=defaultdict(set)
    for i in group:
        cells[((i%width)//size,(i//width)//size)].add(i)
    return [part for _,part in sorted(cells.items())]


def outlines(indices, width):
    """Trace oriented pixel-boundary loops, preserving holes and exact edges."""
    cells = {(i % width, i // width) for i in indices}
    outgoing = defaultdict(list)
    edges = set()

    def add(a, b):
        edges.add((a, b))
        outgoing[a].append(b)

    for x, y in cells:
        if (x, y - 1) not in cells:
            add((x, y), (x + 1, y))
        if (x + 1, y) not in cells:
            add((x + 1, y), (x + 1, y + 1))
        if (x, y + 1) not in cells:
            add((x + 1, y + 1), (x, y + 1))
        if (x - 1, y) not in cells:
            add((x, y + 1), (x, y))

    loops = []
    while edges:
        a, b = next(iter(edges))
        start = a
        loop = [a]
        while True:
            edges.remove((a, b))
            if b == start:
                break
            loop.append(b)
            direction = (b[0] - a[0], b[1] - a[1])
            # At diagonal contacts, keep each filled area on the right.
            choices = [c for c in outgoing[b] if (b, c) in edges]
            if not choices:
                raise ValueError("Open contour in source image")
            def rank(c):
                d = (c[0] - b[0], c[1] - b[1])
                cross = direction[0] * d[1] - direction[1] * d[0]
                dot = direction[0] * d[0] + direction[1] * d[1]
                return {1: 0, 0: 1, -1: 2}[cross] if dot != -1 else 3
            a, b = b, min(choices, key=rank)
        # Remove points on straight runs; retains an exact pixel outline.
        reduced = []
        n = len(loop)
        for k, p in enumerate(loop):
            prev, nxt = loop[k - 1], loop[(k + 1) % n]
            if (p[0] - prev[0]) * (nxt[1] - p[1]) != (p[1] - prev[1]) * (nxt[0] - p[0]):
                reduced.append(p)
        if reduced:
            loops.append(reduced)
    return loops


def subdivide(loop, stride):
    points = []
    for a, b in zip(loop, loop[1:] + loop[:1]):
        distance = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        for i in range(0, distance, stride):
            points.append((a[0] + (b[0] - a[0]) * i // distance,
                           a[1] + (b[1] - a[1]) * i // distance))
    return points


def path_data(loops):
    return "".join("M" + "L".join(f"{x:g},{y:g}" for x, y in loop) + "Z" for loop in loops)


def static_path_data(loops):
    parts=[]
    for loop in loops:
        parts.append(f"M{loop[0][0]},{loop[0][1]}")
        for a,b in zip(loop,loop[1:]):
            parts.append(f"h{b[0]-a[0]}" if a[1]==b[1] else f"v{b[1]-a[1]}")
        parts.append('z')
    return ''.join(parts)


SCRIPT = r"""<![CDATA[
(function(){
  const svg=document.documentElement, paths=[...svg.querySelectorAll('[data-spring]')];
  function readLoops(d){
    const loops=[];let loop=[];
    for(const token of d.match(/[MZ]|-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?/g)){
      if(token==='M'){if(loop.length)loops.push(loop);loop=[]}
      else if(token==='Z'){if(loop.length)loops.push(loop);loop=[]}
      else {const [x,y]=token.split(',').map(Number);loop.push({x,y,px:x,py:y,vx:0,vy:0})}
    }
    if(loop.length)loops.push(loop);return loops;
  }
  const items=paths.map(el=>({
    el,original:el.getAttribute('d'),loops:readLoops(el.getAttribute('d')),
    mode:el.getAttribute('data-mode'),force:Number(el.getAttribute('data-force')),
    noise:Number(el.getAttribute('data-noise'))
  }));
  for(const item of items){
    const points=item.loops.flat();
    item.cx=points.reduce((s,p)=>s+p.x,0)/points.length;
    item.cy=points.reduce((s,p)=>s+p.y,0)/points.length;
  }
  const radius=Number(svg.getAttribute('data-radius'));
  const strength=Number(svg.getAttribute('data-strength'));
  const spring=Number(svg.getAttribute('data-stiffness'));
  const damping=Number(svg.getAttribute('data-damping'));
  const maximum=Number(svg.getAttribute('data-max-displacement'));
  const squiggle=Number(svg.getAttribute('data-squiggle'));
  const clickGain=Number(svg.getAttribute('data-click-gain'));
  const tripCap=Number(svg.getAttribute('data-trip-cap'));
  const tripDecay=Number(svg.getAttribute('data-trip-decay'));
  const baseChroma=Number(svg.getAttribute('data-base-chroma'));
  const margin=Number(svg.getAttribute('data-activation-margin'));
  const ease=Number(svg.getAttribute('data-activation-ease'));
  const motionDecay=Number(svg.getAttribute('data-motion-decay'));
  const hoverForce=Number(svg.getAttribute('data-hover-force'));
  const box=svg.getAttribute('data-active-box').split(',').map(Number);
  const novaConfig=svg.getAttribute('data-nova').split(',').map(Number);
  const cloudConfig=svg.getAttribute('data-cloud').split(',').map(Number);
  const novaRays=svg.querySelector('#nova-rays');
  const bgWarp=svg.querySelector('#background-warp');
  const cloudBlur=svg.querySelector('#cloud-blur');
  const filters=[...svg.querySelectorAll('[data-chroma-filter]')].map(el=>({
    el,level:Number(el.getAttribute('data-level')),
    red:el.querySelector('[data-red]'),blue:el.querySelector('[data-blue]'),
    left:el.querySelector('[data-left]'),right:el.querySelector('[data-right]')
  }));
  const pointers=new Map();let running=false,last=0,wobble=0,trip=0,motion=0,nova=0,cloud=0;
  function proximity(p){
    const dx=Math.max(box[0]-p.x,0,p.x-box[2]);
    const dy=Math.max(box[1]-p.y,0,p.y-box[3]);
    const t=Math.max(0,1-Math.hypot(dx,dy)/margin);
    return t*t*(3-2*t);
  }
  function start(){if(!running){running=true;requestAnimationFrame(tick)}}
  function updateChroma(){
    for(const f of filters){
      const offset=Math.min(28,(2+trip*3.2)*f.level);
      const alpha=Math.min(.68,(baseChroma+trip*.075)*f.level);
      f.left.setAttribute('dx',(-offset).toFixed(2));
      f.right.setAttribute('dx',offset.toFixed(2));
      f.red.setAttribute('values',`0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ${alpha.toFixed(3)} 0`);
      f.blue.setAttribute('values',`0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 ${alpha.toFixed(3)} 0`);
    }
  }
  function hash(x,y){
    let n=Math.imul(x,374761393)+Math.imul(y,668265263)|0;
    n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;
  }
  function noise(x,y){
    const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
    const u=fx*fx*(3-2*fx),v=fy*fy*(3-2*fy);
    const a=hash(ix,iy)*(1-u)+hash(ix+1,iy)*u;
    const b=hash(ix,iy+1)*(1-u)+hash(ix+1,iy+1)*u;
    return (a*(1-v)+b*v)*2-1;
  }
  function position(e){
    const p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse());
  }
  function disturb(x,y,power,now){
    for(const item of items) for(const loop of item.loops) for(const p of loop){
      const dx=(item.mode==='puff'?item.cx:p.px)-x;
      const dy=(item.mode==='puff'?item.cy:p.py)-y;
      const d=Math.hypot(dx,dy);
      if(d>=radius)continue;
      const falloff=(1-d/radius)**2;
      let ux=dx/(d||1),uy=dy/(d||1);
      if(item.mode==='swirl'){const t=ux;ux=-uy;uy=t}
      if(item.mode==='ripple'){
        const wave=Math.cos(d*.12-now*.015);
        ux*=wave;uy*=wave;
      }
      if(item.mode==='jitter'){
        const angle=noise((p.x+now*.03)/8,(p.y-now*.02)/8)*Math.PI*2;
        ux=Math.cos(angle);uy=Math.sin(angle);
      }
      if(item.mode==='puff'){
        const twist=noise(item.cx/11,item.cy/11)*.7;
        const t=ux;ux=ux*Math.cos(twist)-uy*Math.sin(twist);
        uy=t*Math.sin(twist)+uy*Math.cos(twist);
      }
      p.vx+=ux*power*item.force*falloff;
      p.vy+=uy*power*item.force*falloff;
    }
    start();
  }
  function draw(now){
    for(const item of items){
      let d='';
      for(const loop of item.loops){
        d+='M'+loop.map(p=>{
          const amplitude=wobble*squiggle*item.noise*(1+trip*.38);
          const x=p.px+amplitude*(noise((p.x+now*.018)/25,p.y/25)+.35*noise((p.x-now*.027)/8,p.y/8));
          const y=p.py+amplitude*(noise(p.x/25,(p.y-now*.016)/25)+.35*noise(p.x/8,(p.y+now*.023)/8));
          return x.toFixed(2)+','+y.toFixed(2);
        }).join('L')+'Z';
      }
      item.el.setAttribute('d',d);
    }
  }
  function tick(now){
    const dt=Math.min(2.5,Math.max(.5,(now-(last||now))/16.67));last=now;
    trip*=Math.pow(tripDecay,dt);
    nova*=Math.pow(novaConfig[3],dt);
    cloud*=Math.pow(cloudConfig[2],dt);
    motion*=Math.pow(motionDecay,dt);
    let near=0;
    for(const p of pointers.values())near=Math.max(near,proximity(p));
    const target=Math.min(2.5,motion*near*(1+trip*.15));
    wobble+=(target-wobble)*(1-Math.pow(1-ease,dt));
    for(const p of pointers.values()){
      if(near>0 && motion>.003)
        disturb(p.x,p.y,strength*hoverForce*wobble*motion*proximity(p)*(1+trip*.24),now);
    }
    let active=wobble>.002||motion*near>.002||trip>.01||nova>.01||cloud>.01;
    for(const item of items)for(const loop of item.loops)for(const p of loop){
      p.vx=(p.vx+(p.x-p.px)*spring*dt)*Math.pow(damping,dt);
      p.vy=(p.vy+(p.y-p.py)*spring*dt)*Math.pow(damping,dt);
      p.px+=p.vx*dt;p.py+=p.vy*dt;
      const dx=p.px-p.x,dy=p.py-p.y,dist=Math.hypot(dx,dy);
      const limit=Math.min(190,maximum*(1+trip*.15));
      if(dist>limit){p.px=p.x+dx/dist*limit;p.py=p.y+dy/dist*limit;p.vx*=.5;p.vy*=.5}
      if(dist>.035||Math.abs(p.vx)+Math.abs(p.vy)>.035)active=true;
      else if(motion*near<.002){p.px=p.x;p.py=p.y;p.vx=0;p.vy=0}
    }
    updateChroma();
    bgWarp.setAttribute('scale',(Math.min(100,nova*novaConfig[2])).toFixed(2));
    if(cloudBlur)cloudBlur.setAttribute('stdDeviation',(Math.min(cloudConfig[0],cloud*1.4)).toFixed(2));
    novaRays.setAttribute('opacity',(Math.min(.9,nova*novaConfig[7]/2)).toFixed(3));
    novaRays.setAttribute('transform',`rotate(${(now*novaConfig[4]).toFixed(2)} ${novaConfig[0]} ${novaConfig[1]})`);
    if(active){draw(now);requestAnimationFrame(tick)}
    else {for(const item of items)item.el.setAttribute('d',item.original);running=false;last=0;wobble=0;motion=0;trip=0;nova=0;cloud=0;updateChroma();bgWarp.setAttribute('scale','0');if(cloudBlur)cloudBlur.setAttribute('stdDeviation','0');novaRays.setAttribute('opacity','0')}
  }
  svg.addEventListener('pointermove',e=>{
    const p=position(e);p.down=e.buttons!==0;
    const old=pointers.get(e.pointerId);
    pointers.set(e.pointerId,p);
    const near=proximity(p);
    if(near===0)return;
    const moved=old?Math.hypot(p.x-old.x,p.y-old.y):2;
    if(moved<.03)return;
    motion=Math.max(motion,Math.min(1.35,moved/12)*near);
    start();
  });
  svg.addEventListener('pointerdown',e=>{
    const p=position(e);p.down=true;pointers.set(e.pointerId,p);
    const near=proximity(p);
    if(near===0)return;
    trip=Math.min(tripCap,trip+clickGain);motion=Math.max(motion,1.5*near);
    if(items.some(item=>item.mode==='supernova'&&Math.hypot(item.cx-p.x,item.cy-p.y)<radius))
      nova=Math.min(novaConfig[6],nova+novaConfig[5]);
    if(items.some(item=>item.mode==='puff'&&Math.hypot(item.cx-p.x,item.cy-p.y)<radius))
      cloud=Math.min(cloudConfig[3],cloud+cloudConfig[1]);
    svg.setPointerCapture(e.pointerId);disturb(p.x,p.y,strength*3*(1+trip*.26),performance.now());
  });
  for(const name of ['pointerup','pointercancel','pointerleave'])
    svg.addEventListener(name,e=>{pointers.delete(e.pointerId)});
})();
]]>"""


def convert(args):
    config=load_config(args.config)
    behavior=config["behavior"]
    for key in ("radius","strength","stiffness","damping","max_displacement","squiggle"):
        if getattr(args,key) is None:
            setattr(args,key,behavior[key])
    if args.max_bytes is None:
        args.max_bytes=config["max_bytes"]
    if (args.min_area<1 or args.stride<1 or args.radius<=0 or args.strength<0 or
        args.stiffness<=0 or args.max_displacement<=0 or args.squiggle<0 or args.max_bytes<1 or
        not 0<args.damping<1):
        raise ValueError("invalid controls: use positive sizes and 0<damping<1")
    outer=args.outer_bg or config["outer_background"]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}",outer):
        raise ValueError("--outer-bg must be a six-digit hex color")
    image = Image.open(args.input).convert("RGBA")
    width, height = image.size
    if (width, height) != (512, 512):
        raise ValueError(f"Expected 512x512; got {width}x{height}")
    raw = list(image.get_flattened_data() if hasattr(image,'get_flattened_data') else image.getdata())
    colors = [f"#{r:02x}{g:02x}{b:02x}" if a == 255 else None for r,g,b,a in raw]
    invalid = sorted(set(colors) - set(PALETTE))
    if invalid:
        raise ValueError(f"Colors outside EDG8 (or transparent): {invalid}")
    if args.background:
        bg_image=Image.open(args.background).convert("RGBA")
        if bg_image.size!=(width,height):
            raise ValueError("--background must be 512x512")
        bg_pixels=(bg_image.get_flattened_data() if hasattr(bg_image,'get_flattened_data')
                   else bg_image.getdata())
        background=[f"#{r:02x}{g:02x}{b:02x}" if a==255 else None
                    for r,g,b,a in bg_pixels]
        if set(background)-set(PALETTE):
            raise ValueError("--background must use opaque EDG8 colors")
    else:
        background=underpaint(colors,width,height)
    if args.export_background:
        out=Image.new("RGB",(width,height))
        out.putdata([tuple(bytes.fromhex(color[1:])) for color in background])
        args.export_background.parent.mkdir(parents=True,exist_ok=True)
        out.save(args.export_background)
    box = args.box or (0, 0, width, height)
    x0,y0,x1,y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("--box must be x0 y0 x1 y1 inside the canvas")

    static = defaultdict(set)
    moving = []
    for color, group in components(colors, width, height):
        effect=config["colors"][color]
        touches_edge = any(i % width in (0,width-1) or i // width in (0,height-1) for i in group)
        inside = all(x0 <= i % width < x1 and y0 <= i // width < y1 for i in group)
        if effect["effect"]!="still" and (not touches_edge or effect["include_edge"]) and inside and len(group) >= args.min_area:
            if effect["effect"]=="puff":
                moving.extend((color,part) for part in fragments(group,width,effect["fragment_size"]))
            else:
                moving.append((color, group))
        else:
            # The base underpainting already contains edge-connected scenery.
            if not touches_edge or any(background[i]!=color for i in group):
                static[color].update(group)
    if args.box:
        active_box=tuple(args.box)
    elif moving:
        all_indices=set().union(*(group for _,group in moving))
        xx=[i%width for i in all_indices]
        yy=[i//width for i in all_indices]
        active_box=(min(xx),min(yy),max(xx)+1,max(yy)+1)
    else:
        active_box=(0,0,0,0)
    sun_pixels=[i for color,group in moving if config["colors"][color]["effect"]=="supernova" for i in group]
    if sun_pixels:
        sun_x=sum(i%width for i in sun_pixels)/len(sun_pixels)
        sun_y=sum(i//width for i in sun_pixels)/len(sun_pixels)
    else:
        sun_x,sun_y=256,256
    nova=config["supernova"]
    cloud=config["cloud"]
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
              'width="100%" height="100%" preserveAspectRatio="xMidYMid meet" '
              f'data-radius="{args.radius:g}" data-strength="{args.strength:g}" '
              f'data-stiffness="{args.stiffness:g}" data-damping="{args.damping:g}" '
              f'data-max-displacement="{args.max_displacement:g}" data-squiggle="{args.squiggle:g}" '
              f'data-click-gain="{behavior["click_gain"]:g}" data-trip-cap="{behavior["trip_cap"]:g}" '
              f'data-trip-decay="{behavior["trip_decay"]:g}" data-base-chroma="{behavior["base_chroma"]:g}" '
              f'data-activation-margin="{behavior["activation_margin"]:g}" '
              f'data-activation-ease="{behavior["activation_ease"]:g}" '
              f'data-motion-decay="{behavior["motion_decay"]:g}" '
              f'data-hover-force="{behavior["hover_force"]:g}" '
              f'data-active-box="{",".join(map(str,active_box))}" '
              f'data-nova="{sun_x:g},{sun_y:g},{nova["background_warp"]:g},{nova["decay"]:g},'
              f'{nova["rotation_speed"]:g},{nova["click_gain"]:g},{nova["cap"]:g},{nova["ray_opacity"]:g}" '
              f'data-cloud="{cloud["max_blur"]:g},{cloud["click_gain"]:g},{cloud["decay"]:g},{cloud["cap"]:g}" '
              f'style="display:block;width:100vw;height:100vh;background:{outer};touch-action:none;user-select:none" '
              'aria-label="Interactive pixel art">']
    pieces.append('<defs>')
    pieces.append('<filter id="ambient-warp" filterUnits="userSpaceOnUse" x="-48" y="-48" width="608" height="608">'
                  '<feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves="2" seed="7" result="field"/>'
                  '<feDisplacementMap id="background-warp" in="SourceGraphic" in2="field" scale="0" '
                  'xChannelSelector="R" yChannelSelector="G"/></filter>')
    for index,color in enumerate(PALETTE):
        if not any(c==color for c,_ in moving):
            continue
        level=config["colors"][color]["chroma"]
        opacity=min(.68,behavior["base_chroma"]*level)
        offset=min(28,2*level)
        is_puff=config["colors"][color]["effect"]=="puff"
        source_name="cloudSoft" if is_puff else "SourceGraphic"
        pieces.append(f'<filter id="chroma{index}" data-chroma-filter="1" data-level="{level:g}" '
                      'filterUnits="userSpaceOnUse" x="-50" y="-50" width="612" height="612" '
                      'color-interpolation-filters="sRGB">')
        if is_puff:
            pieces.append('<feGaussianBlur id="cloud-blur" in="SourceGraphic" stdDeviation="0" result="cloudSoft"/>')
        pieces.append(f'<feColorMatrix data-red="1" in="{source_name}" type="matrix" values="0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {opacity:g} 0" result="red"/>'
                      f'<feOffset data-left="1" in="red" dx="{-offset:g}" dy="0" result="left"/>'
                      f'<feColorMatrix data-blue="1" in="{source_name}" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 {opacity:g} 0" result="blue"/>'
                      f'<feOffset data-right="1" in="blue" dx="{offset:g}" dy="0" result="right"/>'
                      '<feMerge><feMergeNode in="left"/><feMergeNode in="right"/>'
                      f'<feMergeNode in="{source_name}"/></feMerge></filter>')
    pieces.append('</defs>')
    # This also paints the letterbox area in viewers that ignore CSS background.
    pieces.append(f'<rect x="-8192" y="-8192" width="16896" height="16896" fill="{outer}"/>')
    pieces.append('<g filter="url(#ambient-warp)">')
    for color in PALETTE:
        indices={i for i,c in enumerate(background) if c==color}
        if indices:
            pieces.append(f'<path fill="{color}" fill-rule="evenodd" d="{static_path_data(outlines(indices,width))}"/>')
    pieces.append('</g>')
    ray_count=int(nova["ray_count"])
    pieces.append('<g id="nova-rays" opacity="0" style="pointer-events:none">')
    for k in range(ray_count):
        angle=2*math.pi*k/ray_count
        spread=(.018 if k%3 else .045)
        distance=750
        x1=sun_x+distance*math.cos(angle-spread)
        y1=sun_y+distance*math.sin(angle-spread)
        x2=sun_x+distance*math.cos(angle+spread)
        y2=sun_y+distance*math.sin(angle+spread)
        tint=("#e6da29","#7b53ad","#fdfdf8")[k%3]
        pieces.append(f'<path fill="{tint}" fill-opacity="0.28" d="M{sun_x:.2f},{sun_y:.2f}'
                      f'L{x1:.2f},{y1:.2f}L{x2:.2f},{y2:.2f}Z"/>')
    pieces.append('</g>')
    # Fixed enclosed art sits above the environment and the supernova rays.
    for color in PALETTE:
        if static[color]:
            pieces.append(f'<path fill="{color}" fill-rule="evenodd" d="{static_path_data(outlines(static[color],width))}"/>')
    for index,color in enumerate(PALETTE):
        groups=[group for c,group in moving if c==color]
        if not groups:
            continue
        fx=config["colors"][color]
        pieces.append(f'<g filter="url(#chroma{index})">')
        for group in groups:
            loops = [subdivide(loop,args.stride) for loop in outlines(group,width)]
            seam=f' stroke="{color}" stroke-width="0.8" stroke-linejoin="round"' if fx["effect"]=="puff" else ''
            pieces.append(f'<path fill="{color}"{seam} fill-rule="evenodd" d="{path_data(loops)}" '
                          f'data-spring="1" data-mode="{fx["effect"]}" '
                          f'data-force="{fx["force"]:g}" data-noise="{fx["noise"]:g}"/>')
        pieces.append('</g>')
    pieces.append('<script>'+SCRIPT+'</script></svg>')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(''.join(pieces),encoding='utf-8')
    size=args.output.stat().st_size
    print(f"{args.output}: {size:,} bytes; {len(moving)} moving regions; "
          f"{len(set(colors))} EDG8 colors")
    if size > args.max_bytes:
        raise ValueError(f"SVG is {size:,} bytes, above the {args.max_bytes:,}-byte limit. "
                         "Try a larger --stride or simplify scattered pixels.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',nargs='?',type=Path,help='optional override for INPUT_FOLDER / INPUT_FILE')
    parser.add_argument('output',nargs='?',type=Path,help='optional override for OUTPUT_FOLDER / OUTPUT_FILE')
    parser.add_argument('--box',nargs=4,type=int,default=ACTIVE_BOX,metavar=('X0','Y0','X1','Y1'),
                        help='only animate enclosed regions fully inside this rectangle')
    parser.add_argument('--config',type=Path,default=configured_path(CONFIG_JSON),help='palette effects and collection rules')
    parser.add_argument('--background',type=Path,default=configured_path(BACKGROUND_PNG),help='optional 512x512 EDG8 underpainting PNG')
    parser.add_argument('--export-background',type=Path,default=configured_path(EXPORT_BACKGROUND_PNG),help='save the inferred underpainting PNG for editing')
    parser.add_argument('--outer-bg',help='override outer background hex color')
    parser.add_argument('--min-area',type=int,default=2,help='minimum moving region area in pixels')
    parser.add_argument('--stride',type=int,default=10,help='maximum distance between spring points on long edges')
    parser.add_argument('--radius',type=float,help='override radius from effects.json')
    parser.add_argument('--strength',type=float,help='override strength from effects.json')
    parser.add_argument('--stiffness',type=float,help='override stiffness from effects.json')
    parser.add_argument('--damping',type=float,help='override damping from effects.json')
    parser.add_argument('--max-displacement',type=float,help='override maximum displacement from effects.json')
    parser.add_argument('--squiggle',type=float,help='override squiggle from effects.json')
    parser.add_argument('--max-bytes',type=int,help='override size limit from effects.json')
    args=parser.parse_args()
    if args.input is None:
        args.input=configured_file(INPUT_FOLDER,INPUT_FILE)
    if args.output is None:
        args.output=configured_file(OUTPUT_FOLDER,OUTPUT_FILE)
    try:
        convert(args)
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    main()
