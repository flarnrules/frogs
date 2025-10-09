/* topogridmaker */
(()=>{
// ── guards / helpers ─────────────────────────────────────────────────────────
const SVG=BTLDR&&BTLDR.svg; if(!SVG) throw new Error('BTLDR.svg missing');
const R=BTLDR.rnd;
const E=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,String(a[k]));return e};
const rad=d=>d*Math.PI/180, clamp=(x,a,b)=>x<a?a:x>b?b:x, lerp=(a,b,t)=>a+(b-a)*t, H0=(R()*360)|0;
const poly=pts=>pts.map(p=>`${p.x},${p.y}`).join(' ');

// ── knobs ────────────────────────────────────────────────────────────────────
const S=900, BG="#fff";
const LIMIT_FPS=24, CYCLE_SECONDS=10;

const STEP=28, CELL_SKIP=2, SEG=72, RES_CURVE=72;  // slight perf trims
const C={x:S*0.52, y:S*0.46}, L1=S*0.36, L2=S*0.30, DEPTH=S*0.20;
const FACE_SAMPLES=84;

// feature toggles (quick A/B while tuning)
const SHOW={ WATER_SHEET:true, TERRAIN:true, SHORE:true, GRID_FLAT:true, GRID_CURVE:true, RIMS:true };

// ── stage ────────────────────────────────────────────────────────────────────
SVG.setAttribute('viewBox',`0 0 ${S} ${S}`);
SVG.setAttribute('preserveAspectRatio','xMidYMid meet');
SVG.appendChild(E('rect',{x:0,y:0,width:S,height:S,fill:BG}));
const DEF=E('defs',{}); SVG.appendChild(DEF);

// basis
const A1=5+R()*20, SEP=110+R()*30, A2=A1+SEP;
const g1={x:Math.cos(rad(A1))*STEP, y:Math.sin(rad(A1))*STEP};
const g2={x:Math.cos(rad(A2))*STEP, y:Math.sin(rad(A2))*STEP};
const norm=v=>{const m=Math.hypot(v.x,v.y)||1; return {x:v.x/m,y:v.y/m}};
const u1=norm(g1), u2=norm(g2);

// pane corners
const baseCorners=(k1=1,k2=1)=>{
  const A={x:C.x + u1.x*L1*k1 + u2.x*L2*k2, y:C.y + u1.y*L1*k1 + u2.y*L2*k2};
  const B={x:C.x + u1.x*L1*k1 - u2.x*L2*k2, y:C.y + u1.y*L1*k1 - u2.y*L2*k2};
  const Cc={x:C.x - u1.x*L1*k1 - u2.x*L2*k2, y:C.y - u1.y*L1*k1 - u2.y*L2*k2};
  const D={x:C.x - u1.x*L1*k1 + u2.x*L2*k2, y:C.y - u1.y*L1*k1 + u2.y*L2*k2};
  return [A,B,Cc,D];
};
const P0=baseCorners(1,1), P0B=P0.map(p=>({x:p.x,y:p.y+DEPTH}));

// flat bbox for shoreline sampling
const flatBBox=(()=>{const xs=P0.map(p=>p.x), ys=P0.map(p=>p.y);
  return {minx:Math.min(...xs), maxx:Math.max(...xs), miny:Math.min(...ys), maxy:Math.max(...ys)};
})();

// top-face clip
const clipPane=E('clipPath',{id:'clipPane',clipPathUnits:'userSpaceOnUse'});
DEF.appendChild(clipPane);
const clipPlanePath=E('path',{d:''});
clipPane.appendChild(clipPlanePath);

// groups (painter’s order): backs → plane (sheet/land/shore/grid) → fronts → front outlines
const GfacesBack = E('g',{}); SVG.appendChild(GfacesBack);
const Gplane     = E('g',{'clip-path':'url(#clipPane)'}); SVG.appendChild(Gplane);
const GfacesFront= E('g',{}); SVG.appendChild(GfacesFront);
const GfrontLines= E('g',{}); SVG.appendChild(GfrontLines); // crisp rims (front only)

// plane content in the exact draw order we want
const GwaterSheet=E('g',{}); Gplane.appendChild(GwaterSheet);
const Gterrain   =E('g',{}); Gplane.appendChild(Gterrain);
const Gshore     =E('g',{}); Gplane.appendChild(Gshore);
const Ggrid      =E('g',{}); Gplane.appendChild(Ggrid);
const Gcurve     =E('g',{}); Gplane.appendChild(Gcurve);

// border rim (debug/edge)
const Grim=E('path',{d:'',fill:'none',stroke:`hsl(${H0} 0% 15% / 0.65)`,'stroke-width':2}); SVG.appendChild(Grim);

// ── field / terrain ──────────────────────────────────────────────────────────
const ORIGIN={x:C.x,y:C.y};
const LINES=Math.ceil((Math.max(L1,L2)*2*1.1)/STEP), LSPAN=LINES*2+6;
const U=(i,j)=>({x:ORIGIN.x + g1.x*i + g2.x*j, y:ORIGIN.y + g1.y*i + g2.y*j});

const AMP=STEP*(1.8+R()*2.4), f1=0.004+R()*0.004, f2=0.006+R()*0.004;
const th1=rad(R()*360), th2=rad(R()*360);
const n1={x:Math.cos(th1),y:Math.sin(th1)}, n2={x:Math.cos(th2),y:Math.sin(th2)};
const p1={x:-n1.y,y:n1.x}, p2={x:-n2.y,y:n2.x};
const SEA=-AMP*0.08;

const CP=[
  {h:SEA-0.70*AMP, c:{h:210,s:70,l:24}},
  {h:SEA-0.15*AMP, c:{h:204,s:65,l:42}},
  {h:SEA+0.00*AMP, c:{h: 50,s:80,l:62}},
  {h:SEA+0.20*AMP, c:{h: 95,s:60,l:58}},
  {h:SEA+0.55*AMP, c:{h:115,s:50,l:36}},
  {h:SEA+0.90*AMP, c:{h:  0,s: 0,l:94}},
];
const colorAtH=h=>{
  if(h<=CP[0].h) return CP[0].c;
  for(let k=0;k<CP.length-1;k++){
    const a=CP[k], b=CP[k+1];
    if(h<=b.h){const t=(h-a.h)/(b.h-a.h||1e-6); return {h:lerp(a.c.h,b.c.h,t), s:lerp(a.c.s,b.c.s,t), l:lerp(a.c.l,b.c.l,t)};}
  }
  return CP[CP.length-1].c;
};
const LDIR=(()=>{const v={x:-0.7,y:-0.6}; const m=Math.hypot(v.x,v.y)||1; return {x:v.x/m,y:v.y/m};})();
const SHADE_K=0.35;

function makePhase(phase){
  const z=(x,y)=>AMP*(0.6*Math.sin((x*n1.x+y*n1.y)*f1+phase)+0.4*Math.sin((x*n2.x+y*n2.y)*f2+phase));
  const grad=(x,y)=>{const a1=(x*n1.x+y*n1.y)*f1+phase,a2=(x*n2.x+y*n2.y)*f2+phase;const d1=AMP*0.6*f1*Math.cos(a1),d2=AMP*0.4*f2*Math.cos(a2);return{gx:d1*n1.x+d2*n2.x,gy:d1*n1.y+d2*n2.y}};
  const W=(p)=>{const a1=(p.x*n1.x+p.y*n1.y)*f1+phase,a2=(p.x*n2.x+p.y*n2.y)*f2+phase;const d1=AMP*0.6*f1*Math.cos(a1),d2=AMP*0.4*f2*Math.cos(a2);const h=AMP*(0.6*Math.sin(a1)+0.4*Math.sin(a2));return{x:p.x+0.9*(d1*p1.x+d2*p2.x),y:p.y-1.0*h}};
  const shade=(base,ux,uy,a=1)=>{const g=grad(ux,uy);const lam=clamp(0.5 - SHADE_K*(g.gx*LDIR.x+g.gy*LDIR.y),0,1);const l=clamp(base.l*(0.75+0.5*lam),5,95);return`hsl(${base.h} ${base.s}% ${l}% / ${a})`};
  return {z,W,shade};
}

// ── geometry helpers ─────────────────────────────────────────────────────────
const sampleEdge=(W,p0,p1,n=FACE_SAMPLES)=>{const pts=[];for(let s=0;s<=n;s++){const t=s/n;pts.push(W({x:p0.x+(p1.x-p0.x)*t,y:p0.y+(p1.y-p0.y)*t}));}return pts;};
const borderPoints=(W)=>{const [A,B,Cc,D]=P0;return [...sampleEdge(W,A,B),...sampleEdge(W,B,Cc).slice(1),...sampleEdge(W,Cc,D).slice(1),...sampleEdge(W,D,A).slice(1)]};
const borderPathD=(pts)=>{let d=`M ${pts[0].x} ${pts[0].y}`; for(let i=1;i<pts.length;i++) d+=` L ${pts[i].x} ${pts[i].y}`; return d+' Z'};

// faces
const buildRockFace=(W,top0,top1,bot0,bot1,fill)=>{
  const top=sampleEdge(W,top0,top1), bot=[]; 
  for(let s=0;s<=FACE_SAMPLES;s++){const t=s/FACE_SAMPLES; bot.push({x:bot0.x+(bot1.x-bot0.x)*t, y:bot0.y+(bot1.y-bot0.y)*t});}
  return {fill, pts: top.concat(bot.reverse()), avgY: top.reduce((a,p)=>a+p.y,0)/top.length};
};

// flat water side segments from straight edges (decide underwater in field space)
function buildWaterSegments(z, top0, top1, bot0, bot1){
  const N=FACE_SAMPLES, tvals=[], isUnder=[];
  for(let s=0;s<=N;s++){const t=s/N; tvals.push(t); const fx=top0.x+(top1.x-top0.x)*t, fy=top0.y+(top1.y-top0.y)*t; isUnder.push(z(fx,fy)<SEA);}
  const lerpPt=(a,b,t)=>({x:a.x+(b.x-a.x)*t, y:a.y+(b.y-a.y)*t});
  const refineT=(t0,t1)=>{const f=tt=>z(top0.x+(top1.x-top0.x)*tt, top0.y+(top1.y-top0.y)*tt); const v0=f(t0),v1=f(t1); const tt=(SEA-v0)/((v1-v0)||1e-6); return clamp(t0+(t1-t0)*tt, Math.min(t0,t1), Math.max(t0,t1));};
  const segs=[], tops=[]; let runStart=null;
  for(let s=0;s<=N;s++){
    const under=isUnder[s]; if(under && runStart===null) runStart=s;
    if((!under || s===N) && runStart!==null){
      let t0=tvals[runStart], t1=tvals[under?s:s-1];
      if(runStart>0 && !isUnder[runStart-1]) t0=refineT(tvals[runStart-1], t0);
      if(!under && s<=N && isUnder[s])     t1=refineT(t1, tvals[s]);
      const M=Math.max(2,Math.round((t1-t0)*N)), top=[], bot=[];
      for(let k=0;k<=M;k++){const tt=t0+(t1-t0)*(k/M); top.push(lerpPt(top0,top1,tt));}
      for(let k=M;k>=0;k--){const tt=t0+(t1-t0)*(k/M); bot.push(lerpPt(bot0,bot1,tt));}
      segs.push(top.concat(bot));
      tops.push(top);
      runStart=null;
    }
  }
  return {segs, tops};
}

// ── smoothed shoreline (stitched & quadratic) ───────────────────────────────
// 1) trace short segments via marching squares (in flat pane space)
function marchingSegments(z,bbox,nx=120,ny=120){
  const {minx,maxx,miny,maxy}=bbox, L=(a,b,t)=>a+(b-a)*t, idx=(ix,iy)=>iy*(nx+1)+ix;
  const Z=new Array((nx+1)*(ny+1));
  for(let iy=0;iy<=ny;iy++){const y=L(miny,maxy,iy/ny); for(let ix=0;ix<=nx;ix++){const x=L(minx,maxx,ix/nx); Z[idx(ix,iy)]=z(x,y);}}
  const P=(ix,iy)=>({x:L(minx,maxx,ix/nx), y:L(miny,maxy,iy/ny)});
  const interp=(p0,v0,p1,v1)=>{const t=(SEA-v0)/((v1-v0)||1e-6); return {x:p0.x+(p1.x-p0.x)*t, y:p0.y+(p1.y-p0.y)*t}};
  const segs=[];
  for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){
    const v00=Z[idx(ix,iy)], v10=Z[idx(ix+1,iy)], v11=Z[idx(ix+1,iy+1)], v01=Z[idx(ix,iy+1)];
    const id=((v00>=SEA)<<0)|((v10>=SEA)<<1)|((v11>=SEA)<<2)|((v01>=SEA)<<3);
    if(id===0||id===15) continue;
    const p00=P(ix,iy), p10=P(ix+1,iy), p11=P(ix+1,iy+1), p01=P(ix,iy+1);
    const edges=[];
    if(((id>>0)&1)!==((id>>1)&1)) edges.push(interp(p00,v00,p10,v10));
    if(((id>>1)&1)!==((id>>2)&1)) edges.push(interp(p10,v10,p11,v11));
    if(((id>>2)&1)!==((id>>3)&1)) edges.push(interp(p11,v11,p01,v01));
    if(((id>>3)&1)!==((id>>0)&1)) edges.push(interp(p01,v01,p00,v00));
    if(edges.length===2) segs.push(edges); // [A,B]
  }
  return segs;
}
// 2) stitch segments into polylines by endpoint proximity
function stitchPolylines(segs, eps=1e-3){
  const key=p=>`${p.x.toFixed(3)},${p.y.toFixed(3)}`;
  const map=new Map(); // point key -> indices
  segs.forEach((s,idx)=>{const a=key(s[0]), b=key(s[1]); if(!map.has(a)) map.set(a,[]); if(!map.has(b)) map.set(b,[]); map.get(a).push({idx,end:0}); map.get(b).push({idx,end:1});});
  const used=new Array(segs.length).fill(false), lines=[];
  for(let i=0;i<segs.length;i++){
    if(used[i]) continue;
    used[i]=true;
    let a=segs[i][0], b=segs[i][1], line=[a,b];
    let extended=true;
    while(extended){
      extended=false;
      // try extend at tail
      const kTail=key(line[line.length-1]), candT=(map.get(kTail)||[]).filter(c=>!used[c.idx]);
      for(const c of candT){const s=segs[c.idx]; const next=(Math.abs(s[0].x-line[line.length-1].x)<eps && Math.abs(s[0].y-line[line.length-1].y)<eps)?s[1]
                                      :(Math.abs(s[1].x-line[line.length-1].x)<eps && Math.abs(s[1].y-line[line.length-1].y)<eps)?s[0]:null;
        if(next){used[c.idx]=true; line.push(next); extended=true; break;}
      }
      if(extended) continue;
      // try extend at head
      const kHead=key(line[0]), candH=(map.get(kHead)||[]).filter(c=>!used[c.idx]);
      for(const c of candH){const s=segs[c.idx]; const next=(Math.abs(s[0].x-line[0].x)<eps && Math.abs(s[0].y-line[0].y)<eps)?s[1]
                                      :(Math.abs(s[1].x-line[0].x)<eps && Math.abs(s[1].y-line[0].y)<eps)?s[0]:null;
        if(next){used[c.idx]=true; line.unshift(next); extended=true; break;}
      }
    }
    if(line.length>1) lines.push(line);
  }
  return lines;
}
// 3) convert a polyline to a smoothed quadratic path (Catmull-Rom → Q)
function polyToQPath(points, W){
  if(points.length<2) return '';
  const P=points.map(W);
  let d=`M ${P[0].x} ${P[0].y}`;
  for(let i=1;i<P.length-1;i++){
    const p0=P[i-1], p1=P[i], p2=P[i+1];
    const mx=(p0.x+2*p1.x+p2.x)/4, my=(p0.y+2*p1.y+p2.y)/4; // simple CR-ish midpoint
    d+=` Q ${p1.x} ${p1.y} ${mx} ${my}`;
  }
  // last leg to final point
  const pen=P[P.length-2], last=P[P.length-1], mx=(pen.x+last.x)/2, my=(pen.y+last.y)/2;
  d+=` T ${last.x} ${last.y}`;
  return d;
}

// ── Stable front/back sets (no popping) ──────────────────────────────────────
const EDGES=[
  {name:'AB', t0:P0[0], t1:P0[1], b0:P0B[0], b1:P0B[1], rockFill:`hsl(${(H0+22)%360} 28% 18%)`},
  {name:'BC', t0:P0[1], t1:P0[2], b0:P0B[1], b1:P0B[2], rockFill:`hsl(${(H0+10)%360} 28% 16%)`},
  {name:'CD', t0:P0[2], t1:P0[3], b0:P0B[2], b1:P0B[3], rockFill:`hsl(${(H0+22)%360} 28% 18%)`},
  {name:'DA', t0:P0[3], t1:P0[0], b0:P0B[3], b1:P0B[0], rockFill:`hsl(${(H0+10)%360} 28% 16%)`}
];
const _sorted=EDGES.map(e=>({...e,sortY:(e.t0.y+e.t1.y)/2})).sort((a,b)=> (a.sortY-b.sortY) || (a.name<b.name?-1:1));
const BACK_EDGES=[_sorted[0],_sorted[1]];
const FRONT_EDGES=[_sorted[2],_sorted[3]];

// ── cached height on lattice for terrain/water sheet ─────────────────────────
function makeHeightCache(z){
  const cache=new Map();
  const key=(i,j)=>`${i},${j}`;
  return {
    H(i,j,pt){
      const k=key(i,j);
      if(cache.has(k)) return cache.get(k);
      const h=z(pt.x,pt.y); cache.set(k,h); return h;
    }
  };
}

// ── frame build ──────────────────────────────────────────────────────────────
function buildFrame(phase){
  GfacesBack.textContent=''; GfacesFront.textContent=''; GfrontLines.textContent='';
  GwaterSheet.textContent=''; Gterrain.textContent=''; Gshore.textContent=''; Ggrid.textContent=''; Gcurve.textContent='';

  const {z,W,shade}=makePhase(phase);
  const {H}=makeHeightCache(z);

  // dynamic border
  const bpts=borderPoints(W), bpath=borderPathD(bpts);
  clipPlanePath.setAttribute('d', bpath);
  Grim.setAttribute('d', bpath);

  const rockOf=e=>buildRockFace(W,e.t0,e.t1,e.b0,e.b1,e.rockFill);
  const waterSegsOf=e=>buildWaterSegments(z,e.t0,e.t1,e.b0,e.b1);

  // BACK faces (behind plane): water walls + rock
  for(const e of BACK_EDGES){
    const res=waterSegsOf(e);
    for(const seg of res.segs) GfacesBack.appendChild(E('polygon',{points:poly(seg), fill:'hsl(204 50% 58% / 0.35)'}));
    GfacesBack.appendChild(E('polygon',{points:poly(rockOf(e).pts), fill:e.rockFill}));
    // back water rim (thin line along edge where underwater)
    if(SHOW.RIMS) for(const top of res.tops){
      let d=`M ${top[0].x} ${top[0].y}`; for(let i=1;i<top.length;i++) d+=` L ${top[i].x} ${top[i].y}`;
      GfacesBack.appendChild(E('path',{d, fill:'none', stroke:'hsl(204 45% 50% / 0.65)', 'stroke-width':1.6, 'stroke-linecap':'round'}));
    }
  }

  // flat water sheet (inside pane) — before terrain so land overlaps
  const waterFilm=h=>{const t=clamp((SEA-h)/(.7*AMP),0,1); return `hsl(204 40% 60% / ${0.12+0.68*t})`;};
  if(SHOW.WATER_SHEET){
    for(let j=-LINES+1;j<LINES-1;j+=CELL_SKIP){
      for(let i=-LINES+1;i<LINES-1;i+=CELL_SKIP){
        const U00=U(i,j), U10=U(i+CELL_SKIP,j), U11=U(i+CELL_SKIP,j+CELL_SKIP), U01=U(i,j+CELL_SKIP);
        const h00=H(i,j,U00), h10=H(i+CELL_SKIP,j,U10), h11=H(i+CELL_SKIP,j+CELL_SKIP,U11), h01=H(i,j+CELL_SKIP,U01);
        const m=Math.max(h00,h10,h11,h01);
        const hAvg=(h00+h10+h11+h01)/4;
        if(m<SEA-AMP*0.02 || hAvg<SEA){
          GwaterSheet.appendChild(E('polygon',{points:poly([U00,U10,U11,U01]), fill:waterFilm(hAvg)}));
        }
      }
    }
  }

  // terrain polys (over water sheet)
  if(SHOW.TERRAIN){
    for(let j=-LINES+1;j<LINES-1;j+=CELL_SKIP){
      for(let i=-LINES+1;i<LINES-1;i+=CELL_SKIP){
        const U00=U(i,j), U10=U(i+CELL_SKIP,j), U11=U(i+CELL_SKIP,j+CELL_SKIP), U01=U(i,j+CELL_SKIP);
        const h00=H(i,j,U00), h10=H(i+CELL_SKIP,j,U10), h11=H(i+CELL_SKIP,j+CELL_SKIP,U11), h01=H(i,j+CELL_SKIP,U01);
        const hAvg=(h00+h10+h11+h01)/4;
        const P00=W(U00), P10=W(U10), P11=W(U11), P01=W(U01);
        const ux=(U00.x+U10.x+U11.x+U01.x)/4, uy=(U00.y+U10.y+U11.y+U01.y)/4;
        Gterrain.appendChild(E('polygon',{points:poly([P00,P10,P11,P01]), fill:shade(colorAtH(hAvg),ux,uy,1)}));
      }
    }
  }

  // curved shoreline on top surface (z==SEA), warped with W — smoothed
  if(SHOW.SHORE){
    const segs=marchingSegments(z,flatBBox,120,120);
    const polylines=stitchPolylines(segs,1e-2);
    for(const line of polylines){
      const d=polyToQPath(line, W);
      if(d) Gshore.appendChild(E('path',{
        d, fill:'none',
        stroke:'hsl(204 45% 55% / 0.9)',
        'stroke-width':1.6, 'stroke-linecap':'round','stroke-linejoin':'round'
      }));
    }
  }

  // grids
  const alphaFlat=h=>{const aW=0.75,s0=SEA-0.04*AMP,s1=SEA+0.22*AMP; if(h<=s0)return aW; if(h>=s1)return 0; const t=(h-s0)/(s1-s0); return aW*(1-t);};
  const drawSeg=(a,b,stroke)=>{let p0=a; for(let s=1;s<=SEG;s++){const u=s/SEG,p1={x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u};const mid={x:(p0.x+p1.x)/2,y:(p0.y+p1.y)/2},h=z(mid.x,mid.y),al=alphaFlat(h); if(al>0.02 && SHOW.GRID_FLAT) Ggrid.appendChild(E('line',{x1:p0.x,y1:p0.y,x2:p1.x,y2:p1.y,stroke,'stroke-opacity':al,'stroke-width':1})); p0=p1;}};  
  const s1=`hsl(${H0} 22% 32% / 0.55)`, s2=`hsl(${(H0+12)%360} 22% 32% / 0.55)`;
  for(let k=-LINES-2;k<=LINES+2;k++){
    const a={x:ORIGIN.x+g2.x*k-g1.x*LSPAN,y:ORIGIN.y+g2.y*k-g1.y*LSPAN};
    const b={x:ORIGIN.x+g2.x*k+g1.x*LSPAN,y:ORIGIN.y+g2.y*k+g1.y*LSPAN};
    drawSeg(a,b,s1);
  }
  for(let k=-LINES-2;k<=LINES+2;k++){
    const a={x:ORIGIN.x+g1.x*k-g2.x*LSPAN,y:ORIGIN.y+g1.y*k-g2.y*LSPAN};
    const b={x:ORIGIN.x+g1.x*k+g2.x*LSPAN,y:ORIGIN.y+g1.y*k+g2.y*LSPAN};
    drawSeg(a,b,s2);
  }
  const addLand=(a,b,stroke,w)=>{if(!SHOW.GRID_CURVE) return; let d="",pen=false; for(let t=0;t<=RES_CURVE;t++){const u=t/RES_CURVE,x=a.x+(b.x-a.x)*u,y=a.y+(b.y-a.y)*u; if(z(x,y)>SEA){const p=W({x,y}); d+=pen?`L ${p.x} ${p.y} `:`M ${p.x} ${p.y} `; pen=true;} else pen=false;} if(d) Gcurve.appendChild(E('path',{d,fill:'none',stroke,'stroke-width':w,'stroke-opacity':'0.85','stroke-linecap':'round','stroke-linejoin':'round'}));};
  for(let k=-LINES-2;k<=LINES+2;k+=2){
    const a1={x:ORIGIN.x+g2.x*k-g1.x*LSPAN,y:ORIGIN.y+g2.y*k-g1.y*LSPAN};
    const b1={x:ORIGIN.x+g2.x*k+g1.x*LSPAN,y:ORIGIN.y+g2.y*k+g1.y*LSPAN};
    addLand(a1,b1,`hsl(${H0} 32% 42%)`,1.05);
    const a2={x:ORIGIN.x+g1.x*k-g2.x*LSPAN,y:ORIGIN.y+g1.y*k-g2.y*LSPAN};
    const b2={x:ORIGIN.x+g1.x*k+g2.x*LSPAN,y:ORIGIN.y+g1.y*k+g2.y*LSPAN};
    addLand(a2,b2,`hsl(${(H0+12)%360} 32% 42%)`,1.05);
  }

  // FRONT faces (on top): water walls + rock, then crisp front water rim
  for(const e of FRONT_EDGES){
    const res=waterSegsOf(e);
    for(const seg of res.segs) GfacesFront.appendChild(E('polygon',{points:poly(seg), fill:'hsl(204 50% 58% / 0.35)'}));
    GfacesFront.appendChild(E('polygon',{points:poly(rockOf(e).pts), fill:e.rockFill}));
    if(SHOW.RIMS) for(const top of res.tops){
      let d=`M ${top[0].x} ${top[0].y}`; for(let i=1;i<top.length;i++) d+=` L ${top[i].x} ${top[i].y}`;
      GfrontLines.appendChild(E('path',{d, fill:'none', stroke:'hsl(204 45% 50% / 0.95)', 'stroke-width':1.8, 'stroke-linecap':'round'}));
    }
  }
}

// ── RAF loop ─────────────────────────────────────────────────────────────────
const TWO_PI=Math.PI*2; let tPrev=null, acc=0, frameInt=LIMIT_FPS?(1000/LIMIT_FPS):0;
function tick(ts){
  if(tPrev==null) tPrev=ts; const dt=ts-tPrev; tPrev=ts; acc+=dt;
  const phase=((ts/1000)/CYCLE_SECONDS)*TWO_PI % TWO_PI;
  if(!frameInt || acc>=frameInt){ buildFrame(phase); acc=frameInt?(acc-frameInt):0; }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
})();
