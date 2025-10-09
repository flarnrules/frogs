#!/usr/bin/env python3
"""
offline_terrain_gif.py

Render a browser-less GIF of the animated "topographic block" using pure Python:
- numpy for math
- Pillow (PIL) for raster drawing
- imageio for GIF encoding

It ports the core math from your JS (z field, W warp, faces, water sheet, painter's order).
No DOM/SVG/browser required.

Usage:
  python offline_terrain_gif.py --out terrain.gif --size 900 --seconds 6 --fps 24

Install:
  pip install pillow imageio numpy
"""

import argparse, math, random
from dataclasses import dataclass
from typing import List, Tuple
from PIL import Image, ImageDraw
import numpy as np
import imageio.v3 as iio

# -------------------- Helpers --------------------

def clamp(x, a, b): return a if x < a else b if x > b else x
def lerp(a,b,t): return a + (b-a)*t

def hsl_to_rgb(h, s, l):
    # h in [0,360], s,l in [0,100]
    import colorsys
    h01 = (h % 360) / 360.0
    s01 = clamp(s, 0, 100) / 100.0
    l01 = clamp(l, 0, 100) / 100.0
    r,g,b = colorsys.hls_to_rgb(h01, l01, s01)
    return int(round(r*255)), int(round(g*255)), int(round(b*255))

def color_rgba(h,s,l,a):
    r,g,b = hsl_to_rgb(h,s,l)
    return (r,g,b,int(round(clamp(a,0,1)*255)))

def poly_area(pts):
    a=0.0
    n=len(pts)
    for i in range(n):
        x1,y1 = pts[i]
        x2,y2 = pts[(i+1)%n]
        a += x1*y2 - x2*y1
    return 0.5*a

def inflate_poly(pts, eps):
    # screen-space inflation: average adjacent edge normals
    n = len(pts)
    out=[]
    # choose outward sign to increase area
    outward = -1.0 if poly_area(pts) > 0 else 1.0
    norms=[]
    for i in range(n):
        x1,y1 = pts[i]
        x2,y2 = pts[(i+1)%n]
        dx,dy = x2-x1, y2-y1
        L = math.hypot(dx,dy) or 1.0
        nx,ny = -dy/L, dx/L  # left normal
        norms.append((nx,ny))
    for i in range(n):
        px,py = pts[i]
        nx0,ny0 = norms[(i-1)%n]
        nx1,ny1 = norms[i]
        vx,vy = nx0+nx1, ny0+ny1
        L = math.hypot(vx,vy) or 1.0
        ux,uy = vx/L, vy/L
        out.append((px + outward*eps*ux, py + outward*eps*uy))
    return out

# -------------------- Core field --------------------

@dataclass
class Params:
    S:int=900
    STEP:float=28
    CELL_SKIP:int=2
    SEG:int=80
    RES_CURVE:int=72
    L1:float=0.36 # as fraction of S
    L2:float=0.30
    DEPTH:float=0.20
    CYCLE_SECONDS:float=10.0
    H0:float=0.0

def make_scene(params:Params, seed=None):
    rnd = random.Random(seed)
    S = params.S
    Cx, Cy = S*0.52, S*0.46
    STEP = params.STEP

    A1 = 5 + rnd.random()*20
    SEP = 110 + rnd.random()*30
    A2 = A1 + SEP
    def rad(d): return d*math.pi/180
    g1 = (math.cos(rad(A1))*STEP, math.sin(rad(A1))*STEP)
    g2 = (math.cos(rad(A2))*STEP, math.sin(rad(A2))*STEP)
    def norm(v):
        x,y=v; L=math.hypot(x,y) or 1.0; return (x/L, y/L)
    u1 = norm(g1); u2 = norm(g2)

    L1 = params.L1 * S
    L2 = params.L2 * S
    DEPTH = params.DEPTH * S

    def base_corners(k1=1,k2=1):
        A=(Cx + u1[0]*L1*k1 + u2[0]*L2*k2, Cy + u1[1]*L1*k1 + u2[1]*L2*k2)
        B=(Cx + u1[0]*L1*k1 - u2[0]*L2*k2, Cy + u1[1]*L1*k1 - u2[1]*L2*k2)
        Cc=(Cx - u1[0]*L1*k1 - u2[0]*L2*k2, Cy - u1[1]*L1*k1 - u2[1]*L2*k2)
        D=(Cx - u1[0]*L1*k1 + u2[0]*L2*k2, Cy - u1[1]*L1*k1 + u2[1]*L2*k2)
        return [A,B,Cc,D]
    P0 = base_corners(1,1)
    P0B = [(x, y+DEPTH) for (x,y) in P0]

    ORIGIN = (Cx, Cy)
    def U(i,j):
        return (ORIGIN[0] + g1[0]*i + g2[0]*j, ORIGIN[1] + g1[1]*i + g2[1]*j)

    AMP = STEP*(1.8 + rnd.random()*2.4)
    f1 = 0.004 + rnd.random()*0.004
    f2 = 0.006 + rnd.random()*0.004
    th1 = rad(rnd.random()*360)
    th2 = rad(rnd.random()*360)
    n1 = (math.cos(th1), math.sin(th1))
    n2 = (math.cos(th2), math.sin(th2))
    p1 = (-n1[1], n1[0])
    p2 = (-n2[1], n2[0])
    SEA = -AMP*0.08

    def make_phase(phase):
        def z(x,y):
            a1 = (x*n1[0] + y*n1[1])*f1 + phase
            a2 = (x*n2[0] + y*n2[1])*f2 + phase
            return AMP*(0.6*math.sin(a1) + 0.4*math.sin(a2))
        def W(pt):
            x,y = pt
            a1 = (x*n1[0] + y*n1[1])*f1 + phase
            a2 = (x*n2[0] + y*n2[1])*f2 + phase
            d1 = AMP*0.6*f1*math.cos(a1)
            d2 = AMP*0.4*f2*math.cos(a2)
            h = AMP*(0.6*math.sin(a1) + 0.4*math.sin(a2))
            return (x + 0.9*(d1*p1[0] + d2*p2[0]), y - 1.0*h)
        return z, W, SEA, AMP

    # color ramp
    CP = [
        (SEA-0.70*AMP, (210,70,24)),
        (SEA-0.15*AMP, (204,65,42)),
        (SEA+0.00*AMP, (50,80,62)),
        (SEA+0.20*AMP, (95,60,58)),
        (SEA+0.55*AMP, (115,50,36)),
        (SEA+0.90*AMP, (0,0,94)),
    ]
    def colorAtH(h):
        if h <= CP[0][0]: return CP[0][1]
        for k in range(len(CP)-1):
            if h <= CP[k+1][0]:
                (h0,(H0,S0,L0)) = CP[k]
                (h1,(H1,S1,L1_)) = CP[k+1]
                t = (h-h0)/max(1e-6, (h1-h0))
                return (lerp(H0,H1,t), lerp(S0,S1,t), lerp(L0,L1_,t))
        return CP[-1][1]

    # grid extents
    LINES = int(math.ceil((max(L1,L2)*2*1.1)/STEP))
    LSPAN = LINES*2+6

    return {
        "S": S, "P0": P0, "P0B": P0B, "U": U, "ORIGIN": ORIGIN,
        "g1": g1, "g2": g2, "LINES": LINES, "LSPAN": LSPAN,
        "make_phase": make_phase, "colorAtH": colorAtH,
        "params": params
    }

# -------------------- Rendering --------------------

def sample_edge(W, p0, p1, n):
    pts = []
    for s in range(n+1):
        t = s/n
        x = p0[0] + (p1[0]-p0[0])*t
        y = p0[1] + (p1[1]-p0[1])*t
        pts.append(W((x,y)))
    return pts

def build_border_pts(W, P0, n):
    A,B,C,D = P0
    eAB = sample_edge(W,A,B,n)
    eBC = sample_edge(W,B,C,n)
    eCD = sample_edge(W,C,D,n)
    eDA = sample_edge(W,D,A,n)
    allpts = eAB + eBC[1:] + eCD[1:] + eDA[1:]
    return allpts

def draw_polygon(draw:ImageDraw.ImageDraw, pts:List[Tuple[float,float]], fill=None, outline=None, width=1):
    if fill is not None:
        draw.polygon(pts, fill=fill)
    if outline is not None and width>0:
        draw.line(pts+[pts[0]], fill=outline, width=width, joint="curve")

def render_frame(scene, t, fps=24):
    S = scene["S"]; P0=scene["P0"]; P0B=scene["P0B"]; params=scene["params"]
    make_phase = scene["make_phase"]; colorAtH = scene["colorAtH"]
    U = scene["U"]; ORIGIN=scene["ORIGIN"]; g1=scene["g1"]; g2=scene["g2"]
    LINES=scene["LINES"]; LSPAN=scene["LSPAN"]
    STEP=params.STEP; CELL_SKIP=params.CELL_SKIP
    FACE_SAMPLES = 84

    phase = (t / params.CYCLE_SECONDS) * (2*math.pi)

    z, W, SEA, AMP = make_phase(phase)

    # layers
    img = Image.new("RGBA", (S,S), (255,255,255,255))
    back = Image.new("RGBA", (S,S), (0,0,0,0))
    plane = Image.new("RGBA", (S,S), (0,0,0,0))
    front = Image.new("RGBA", (S,S), (0,0,0,0))

    d_back = ImageDraw.Draw(back)
    d_plane = ImageDraw.Draw(plane)
    d_front = ImageDraw.Draw(front)

    # border path (for clipping plane content)
    bpts = build_border_pts(W, P0, FACE_SAMPLES)
    # mask for plane
    mask = Image.new("L", (S,S), 0)
    dm = ImageDraw.Draw(mask)
    dm.polygon(bpts, fill=255)

    # edge ordering (stable in flat space)
    def midy(p0,p1): return 0.5*(p0[1]+p1[1])
    edges = [
        ("AB", P0[0], P0[1], P0B[0], P0B[1], (params.H0+22)%360),
        ("BC", P0[1], P0[2], P0B[1], P0B[2], (params.H0+10)%360),
        ("CD", P0[2], P0[3], P0B[2], P0B[3], (params.H0+22)%360),
        ("DA", P0[3], P0[0], P0B[3], P0B[0], (params.H0+10)%360),
    ]
    edges_sorted = sorted(edges, key=lambda e: (midy(e[1],e[2]), e[0]))
    back_edges = edges_sorted[:2]
    front_edges = edges_sorted[2:]

    def rock_face(top0,top1,bot0,bot1,Hh):
        top = sample_edge(W, top0, top1, FACE_SAMPLES)
        bot = []
        for s in range(FACE_SAMPLES+1):
            t = s/ FACE_SAMPLES
            x = bot0[0] + (bot1[0]-bot0[0])*t
            y = bot0[1] + (bot1[1]-bot0[1])*t
            bot.append((x,y))
        pts = top + list(reversed(bot))
        fill = color_rgba(Hh, 28, 18, 1.0)
        return pts, fill

    def water_side_segments(top0,top1,bot0,bot1):
        # decide underwater by sampling z along flat top edge; build rectangles with straight top/bottom
        N=FACE_SAMPLES
        tvals = [s/N for s in range(N+1)]
        under = []
        for t_ in tvals:
            fx = top0[0] + (top1[0]-top0[0])*t_
            fy = top0[1] + (top1[1]-top0[1])*t_
            under.append(z(fx,fy) < SEA)
        # refine crossing approx via linear interpolation of z samples
        segs=[]
        run=None
        def lerp_pt(a,b,t_): return (a[0]+(b[0]-a[0])*t_, a[1]+(b[1]-a[1])*t_)
        for s in range(N+1):
            u = under[s]
            if u and run is None: run = s
            if ((not u) or s==N) and run is not None:
                s0 = run; s1 = s if u else s-1
                t0 = tvals[s0]; t1=tvals[s1]
                M = max(2, int(round((t1-t0)*N)))
                top=[]; bot=[]
                for k in range(M+1):
                    tt = t0 + (t1-t0)*(k/M)
                    top.append(lerp_pt(top0,top1,tt))
                for k in range(M, -1, -1):
                    tt = t0 + (t1-t0)*(k/M)
                    bot.append(lerp_pt(bot0,bot1,tt))
                segs.append(top+bot)
                run=None
        return segs

    # ---- draw backs (water sides then rock)
    water_fill = color_rgba(204,50,58,0.35)
    for name,t0,t1,b0,b1,Hh in back_edges:
        for seg in water_side_segments(t0,t1,b0,b1):
            draw_polygon(d_back, seg, fill=water_fill)
        pts, fill = rock_face(t0,t1,b0,b1,Hh)
        draw_polygon(d_back, pts, fill=fill)

    # ---- plane content: water sheet (flat), terrain (warped)
    def cell_poly(U00,U10,U11,U01):
        return [U00,U10,U11,U01]

    def water_opacity(havg, m):
        t = clamp((SEA - havg)/(0.7*AMP), 0, 1)
        if (m < SEA-AMP*0.02) or (havg < SEA):
            return 0.12 + 0.68*t
        return 0.0

    water_layer = Image.new("RGBA", (S,S), (0,0,0,0))
    d_w = ImageDraw.Draw(water_layer)

    terrain_layer = Image.new("RGBA", (S,S), (0,0,0,0))
    d_t = ImageDraw.Draw(terrain_layer)

    # grid cells
    for j in range(-LINES+1, LINES-1, params.CELL_SKIP):
        for i in range(-LINES+1, LINES-1, params.CELL_SKIP):
            U00=U(i,j); U10=U(i+params.CELL_SKIP,j); U11=U(i+params.CELL_SKIP,j+params.CELL_SKIP); U01=U(i,j+params.CELL_SKIP)
            h00=z(*U00); h10=z(*U10); h11=z(*U11); h01=z(*U01)
            havg = (h00+h10+h11+h01)/4.0
            m = max(h00,h10,h11,h01)

            # water (flat) polygon
            a = water_opacity(havg, m)
            if a > 0:
                d_w.polygon([U00,U10,U11,U01], fill=color_rgba(204,40,60,a))

            # terrain (warped) polygon
            P00=tuple(sample_edge(W,U00,U00,1)[0]) # micro-opt: single sample
            P10=tuple(sample_edge(W,U10,U10,1)[0])
            P11=tuple(sample_edge(W,U11,U11,1)[0])
            P01=tuple(sample_edge(W,U01,U01,1)[0])
            ux = (U00[0]+U10[0]+U11[0]+U01[0])/4.0
            uy = (U00[1]+U10[1]+U11[1]+U01[1])/4.0
            Hh,Ss,Ll = colorAtH(havg)
            # simple shade: we won't recompute grad here; darken inland a touch
            fill_col = color_rgba(Hh, Ss, Ll, 1.0)
            d_t.polygon([P00,P10,P11,P01], fill=fill_col)

    # composite plane with mask
    plane.alpha_composite(water_layer)
    plane.alpha_composite(terrain_layer)
    img.alpha_composite(back)
    img.alpha_composite(Image.composite(plane, Image.new("RGBA",(S,S),(0,0,0,0)), mask))

    # ---- front faces (water then rock)
    d_front = ImageDraw.Draw(front)
    for name,t0,t1,b0,b1,Hh in front_edges:
        for seg in water_side_segments(t0,t1,b0,b1):
            draw_polygon(d_front, seg, fill=water_fill)
        pts, fill = rock_face(t0,t1,b0,b1,Hh)
        draw_polygon(d_front, pts, fill=fill)

    img.alpha_composite(front)
    return np.array(img)  # for imageio

# -------------------- CLI --------------------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='terrain.gif')
    ap.add_argument('--size', type=int, default=900)
    ap.add_argument('--seconds', type=float, default=6.0)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--seed', type=int, default=12345, help='random seed for reproducibility')
    args = ap.parse_args()

    params = Params(S=args.size, H0=random.Random(args.seed).random()*360)
    scene = make_scene(params, seed=args.seed)

    frames = int(round(args.seconds*args.fps))
    imgs = []
    for i in range(frames):
        t = (i/args.fps)
        imgs.append(render_frame(scene, t, fps=args.fps))

    iio.imwrite(args.out, imgs, plugin='pillow', duration=1.0/args.fps, loop=0)
    print(f"Wrote {args.out} ({frames} frames @ {args.fps} fps)")

if __name__ == '__main__':
    main()
