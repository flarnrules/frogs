#!/usr/bin/env python3
"""Turn a 512x512 EDG8 PNG into a self-contained, springy SVG."""
import argparse
from collections import defaultdict, deque
from pathlib import Path

from PIL import Image

PALETTE = (
    "#fdfdf8", "#d32734", "#da7d22", "#e6da29",
    "#28c641", "#2d93dd", "#7b53ad", "#1b1c33",
)


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
  const items=paths.map(el=>({el,original:el.getAttribute('d'),loops:readLoops(el.getAttribute('d'))}));
  const radius=Number(svg.getAttribute('data-radius'));
  const strength=Number(svg.getAttribute('data-strength'));
  const spring=Number(svg.getAttribute('data-stiffness'));
  const damping=Number(svg.getAttribute('data-damping'));
  const maximum=Number(svg.getAttribute('data-max-displacement'));
  const squiggle=Number(svg.getAttribute('data-squiggle'));
  const pointers=new Map();let running=false, last=0, wobble=0;
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
  function disturb(x,y,power){
    for(const item of items) for(const loop of item.loops) for(const p of loop){
      const dx=p.px-x,dy=p.py-y, d=Math.hypot(dx,dy);
      if(d>=radius)continue;
      const falloff=(1-d/radius)**2;
      const angle=d>0.01?null:Math.random()*Math.PI*2;
      p.vx+=(angle===null?dx/d:Math.cos(angle))*power*falloff;
      p.vy+=(angle===null?dy/d:Math.sin(angle))*power*falloff;
    }
    if(!running){running=true;requestAnimationFrame(tick)}
  }
  function draw(now){
    for(const item of items){
      let d='';
      for(const loop of item.loops){
        d+='M'+loop.map(p=>{
          const x=p.px+wobble*squiggle*(noise((p.x+now*.018)/25,p.y/25)+.35*noise((p.x-now*.027)/8,p.y/8));
          const y=p.py+wobble*squiggle*(noise(p.x/25,(p.y-now*.016)/25)+.35*noise(p.x/8,(p.y+now*.023)/8));
          return x.toFixed(2)+','+y.toFixed(2);
        }).join('L')+'Z';
      }
      item.el.setAttribute('d',d);
    }
  }
  function tick(now){
    const dt=Math.min(2.5,Math.max(.5,(now-(last||now))/16.67));last=now;
    for(const p of pointers.values())disturb(p.x,p.y,p.down?strength*.28:strength*.12);
    if(!pointers.size)wobble*=Math.pow(.965,dt);
    let active=pointers.size>0||wobble>.002;
    for(const item of items)for(const loop of item.loops)for(const p of loop){
      p.vx=(p.vx+(p.x-p.px)*spring*dt)*Math.pow(damping,dt);
      p.vy=(p.vy+(p.y-p.py)*spring*dt)*Math.pow(damping,dt);
      p.px+=p.vx*dt;p.py+=p.vy*dt;
      const dx=p.px-p.x,dy=p.py-p.y,dist=Math.hypot(dx,dy);
      if(dist>maximum){p.px=p.x+dx/dist*maximum;p.py=p.y+dy/dist*maximum;p.vx*=.5;p.vy*=.5}
      if(dist>.035||Math.abs(p.vx)+Math.abs(p.vy)>.035)active=true;
      else if(!pointers.size){p.px=p.x;p.py=p.y;p.vx=0;p.vy=0}
    }
    if(active){draw(now);requestAnimationFrame(tick)}
    else {for(const item of items)item.el.setAttribute('d',item.original);running=false;last=0;wobble=0}
  }
  svg.addEventListener('pointermove',e=>{
    const p=position(e);p.down=e.buttons!==0;
    pointers.set(e.pointerId,p);
    wobble=Math.max(wobble,.75);
    if(!running){running=true;requestAnimationFrame(tick)}
  });
  svg.addEventListener('pointerdown',e=>{
    const p=position(e);p.down=true;pointers.set(e.pointerId,p);
    wobble=1;
    svg.setPointerCapture(e.pointerId);disturb(p.x,p.y,strength*3);
  });
  for(const name of ['pointerup','pointercancel','pointerleave'])
    svg.addEventListener(name,e=>{pointers.delete(e.pointerId)});
})();
]]>"""


def convert(args):
    image = Image.open(args.input).convert("RGBA")
    width, height = image.size
    if (width, height) != (512, 512):
        raise ValueError(f"Expected 512x512; got {width}x{height}")
    raw = list(image.get_flattened_data() if hasattr(image,'get_flattened_data') else image.getdata())
    colors = [f"#{r:02x}{g:02x}{b:02x}" if a == 255 else None for r,g,b,a in raw]
    invalid = sorted(set(colors) - set(PALETTE))
    if invalid:
        raise ValueError(f"Colors outside EDG8 (or transparent): {invalid}")
    box = args.box or (0, 0, width, height)
    x0,y0,x1,y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("--box must be x0 y0 x1 y1 inside the canvas")

    static = defaultdict(set)
    moving = []
    for color, group in components(colors, width, height):
        touches_edge = any(i % width in (0,width-1) or i // width in (0,height-1) for i in group)
        inside = all(x0 <= i % width < x1 and y0 <= i // width < y1 for i in group)
        if not touches_edge and inside and len(group) >= args.min_area:
            moving.append((color, group))
        else:
            static[color].update(group)
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
              'width="100%" height="100%" preserveAspectRatio="xMidYMid meet" '
              f'data-radius="{args.radius:g}" data-strength="{args.strength:g}" '
              f'data-stiffness="{args.stiffness:g}" data-damping="{args.damping:g}" '
              f'data-max-displacement="{args.max_displacement:g}" data-squiggle="{args.squiggle:g}" '
              f'style="display:block;width:100vw;height:100vh;background:{colors[0]};touch-action:none;user-select:none" '
              'aria-label="Interactive pixel art">']
    pieces.append('<defs><filter id="chroma" x="-30%" y="-30%" width="160%" height="160%" '
                  'color-interpolation-filters="sRGB">'
                  f'<feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {args.chroma:g} 0" result="red"/>'
                  '<feOffset in="red" dx="-3" dy="0" result="left"/>'
                  f'<feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 {args.chroma:g} 0" result="blue"/>'
                  '<feOffset in="blue" dx="3" dy="0" result="right"/>'
                  '<feMerge><feMergeNode in="left"/><feMergeNode in="right"/>'
                  '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    # A single path per static color keeps the bulk of a drawing compact.
    for color in PALETTE:
        if static[color]:
            pieces.append(f'<path fill="{color}" fill-rule="evenodd" d="{static_path_data(outlines(static[color],width))}"/>')
    pieces.append('<g filter="url(#chroma)">')
    for color, group in moving:
        loops = [subdivide(loop,args.stride) for loop in outlines(group,width)]
        pieces.append(f'<path fill="{color}" fill-rule="evenodd" d="{path_data(loops)}" data-spring="1"/>')
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
    parser.add_argument('input',type=Path,help='512x512 EDG8 PNG exported from Aseprite')
    parser.add_argument('output',type=Path,help='self-contained SVG destination')
    parser.add_argument('--box',nargs=4,type=int,metavar=('X0','Y0','X1','Y1'),
                        help='only animate enclosed regions fully inside this rectangle')
    parser.add_argument('--min-area',type=int,default=2,help='minimum moving region area in pixels')
    parser.add_argument('--stride',type=int,default=10,help='maximum distance between spring points on long edges')
    parser.add_argument('--radius',type=float,default=105,help='pointer influence radius in SVG pixels')
    parser.add_argument('--strength',type=float,default=6,help='pointer impulse strength')
    parser.add_argument('--stiffness',type=float,default=.035,help='spring pull toward original position')
    parser.add_argument('--damping',type=float,default=.87,help='velocity retained per frame (0..1)')
    parser.add_argument('--max-displacement',type=float,default=95,help='maximum warp distance')
    parser.add_argument('--squiggle',type=float,default=8,help='noise displacement while active')
    parser.add_argument('--chroma',type=float,default=.38,help='red/blue fringe opacity (0..1)')
    parser.add_argument('--max-bytes',type=int,default=900000,help='maximum output size (default: 900000)')
    args=parser.parse_args()
    if (args.min_area<1 or args.stride<1 or args.radius<=0 or args.strength<0 or
        args.stiffness<=0 or args.max_displacement<=0 or args.squiggle<0 or args.max_bytes<1 or
        not 0<args.damping<1 or not 0<=args.chroma<=1):
        parser.error('invalid controls: use positive sizes, 0<damping<1, and 0<=chroma<=1')
    try:
        convert(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__=='__main__':
    main()
