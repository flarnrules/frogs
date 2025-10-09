(()=>{
  const SVG=BTLDR&&BTLDR.svg; if(!SVG) throw new Error('BTLDR.svg missing');
  const R=BTLDR.rnd, NS='http://www.w3.org/2000/svg';
  const E=(t,a)=>{const el=document.createElementNS(NS,t);for(const k in a)el.setAttribute(k,String(a[k]));return el};
  const S=900; SVG.setAttribute('viewBox',`0 0 ${S} ${S}`); SVG.setAttribute('preserveAspectRatio','xMidYMid meet');

  // ── loop + flow controls ────────────────────────────────────────────────────
  const LOOP_SECS=8;                 // exact loop period
  const STEP=Math.round(10+R()*50);  // lattice scale
  const LINES=Math.ceil((S*2.4)/STEP);
  const FLOW_STEPS_G1=1;             // how many whole g1 steps the grid slides per loop (integer)
  const FLOW_STEPS_G2=1;             // how many whole g2 steps the grid slides per loop (integer)
  const FLOW_M1=1, FLOW_M2=1;        // how many 2π cycles each terrain sine advances per loop (integers)

  // ── basis ───────────────────────────────────────────────────────────────────
  const rad=d=>d*Math.PI/180;
  const A1=5+R()*20, SEP=110+R()*30, A2=A1+SEP;
  const g1={x:Math.cos(rad(A1))*STEP, y:Math.sin(rad(A1))*STEP};
  const g2={x:Math.cos(rad(A2))*STEP, y:Math.sin(rad(A2))*STEP};
  const add=(a,b)=>({x:a.x+b.x,y:a.y+b.y}), sc=(a,k)=>({x:a.x*k,y:a.y*k});
  const polyPts=pts=>pts.map(p=>`${p.x},${p.y}`).join(' ');

  // ── palette ─────────────────────────────────────────────────────────────────
  const H0=(R()*360|0), col=(h,s,l,a=1)=>`hsl(${(h%360+360)%360} ${s}% ${l}% / ${a})`;
  const grid1=col(H0,30,40,.6), grid2=col(H0+12,30,40,.6), waterCol=col(H0+190,45,55,.18);

  // ── terrain (same shape, but we'll add time-phased version for grid) ───────
  const AMP=STEP*(1.8+R()*2.4);
  const f1=0.004+R()*0.004, f2=0.006+R()*0.004;
  const th1=rad(R()*360), th2=rad(R()*360);
  const n1={x:Math.cos(th1),y:Math.sin(th1)}, n2={x:Math.cos(th2),y:Math.sin(th2)};
  const p1={x:-n1.y,y:n1.x}, p2={x:-n2.y,y:n2.x};
  const Kx=0.9, Ky=1.0;

  // static warp for city/water geometry (unchanged between frames)
  const zS =(x,y)=> AMP*(0.6*Math.sin((x*n1.x+y*n1.y)*f1)+0.4*Math.sin((x*n2.x+y*n2.y)*f2));
  const dz1S=(x,y)=> AMP*0.6*f1*Math.cos((x*n1.x+y*n1.y)*f1);
  const dz2S=(x,y)=> AMP*0.4*f2*Math.cos((x*n2.x+y*n2.y)*f2);
  const Wstatic=(p)=>{const h=zS(p.x,p.y),sx=dz1S(p.x,p.y)*p1.x+dz2S(p.x,p.y)*p2.x;return {x:p.x+Kx*sx,y:p.y-Ky*h};};

  // time-phased warp for the *grid* (this is what makes it traverse)
  const ω1=2*Math.PI*FLOW_M1/LOOP_SECS, ω2=2*Math.PI*FLOW_M2/LOOP_SECS;
  const Wgrid=(p,t)=>{
    const a1=(p.x*n1.x+p.y*n1.y)*f1 + ω1*t;
    const a2=(p.x*n2.x+p.y*n2.y)*f2 + ω2*t;
    const h = AMP*(0.6*Math.sin(a1)+0.4*Math.sin(a2));
    const sx= AMP*(0.6*f1*Math.cos(a1)*p1.x + 0.4*f2*Math.cos(a2)*p2.x);
    return {x:p.x+Kx*sx, y:p.y-Ky*h};
  };

  // ── containers ──────────────────────────────────────────────────────────────
  const Groot=E('g',{}); SVG.appendChild(Groot);
  const Ggrid=E('g',{}), Gwater=E('g',{}), Gcity=E('g',{}); Groot.append(Ggrid,Gwater,Gcity);

  // ── curved grid: store param lines, animate by recomputing 'd' each frame ──
  const SPAN=LINES*2+6, RES=80;
  const lines=[]; // each: {a:{x,y}, b:{x,y}, stroke, el:<path>}
  const mkLine=(a,b,stroke)=>{
    const el=E('path',{'fill':'none','stroke':stroke,'stroke-width':1.1,'stroke-linecap':'round','stroke-linejoin':'round'});
    Ggrid.appendChild(el);
    lines.push({a,b,stroke,el});
  };
  // build initial param lines (in lattice space)
  for(let k=-LINES-2;k<=LINES+2;k++){
    const off=sc(g2,k), a=add(off,sc(g1,-SPAN)), b=add(off,sc(g1,SPAN)); mkLine(a,b,grid1);
  }
  for(let k=-LINES-2;k<=LINES+2;k++){
    const off=sc(g1,k), a=add(off,sc(g2,-SPAN)), b=add(off,sc(g2,SPAN)); mkLine(a,b,grid2);
  }

  // ── water (static geometry) ─────────────────────────────────────────────────
  const SEA=-AMP*0.08, clamp=(x,a,b)=>x<a?a:x>b?b:x;
  const cellAboveSea=(i,j)=>{
    const P=[add(sc(g1,i),   sc(g2,j)),
             add(sc(g1,i+1), sc(g2,j)),
             add(sc(g1,i),   sc(g2,j+1)),
             add(sc(g1,i+1), sc(g2,j+1))];
    return zS(P[0].x,P[0].y)>SEA && zS(P[1].x,P[1].y)>SEA && zS(P[2].x,P[2].y)>SEA && zS(P[3].x,P[3].y)>SEA;
  };
  for(let j=-LINES+1;j<LINES-2;j+=2){
    for(let i=-LINES+1;i<LINES-2;i+=2){
      if(!cellAboveSea(i,j)){
        const p0=Wstatic(add(sc(g1,i),   sc(g2,j)));
        const p1=Wstatic(add(sc(g1,i+1), sc(g2,j)));
        const p2=Wstatic(add(sc(g1,i+1), sc(g2,j+1)));
        const p3=Wstatic(add(sc(g1,i),   sc(g2,j+1)));
        Gwater.appendChild(E('polygon',{points:polyPts([p0,p1,p2,p3]),fill:waterCol}));
      }
    }
  }

  // ── city (static faces) ────────────────────────────────────────────────────
  const faces=[], RADIUS=LINES-3, iMin=-RADIUS, iMax=RADIUS-1, jMin=-RADIUS, jMax=RADIUS-1;
  const used=new Set(), kkey=(i,j)=>i+'_'+j;
  const dryFactor=(i,j)=>{ const mid=add(sc(g1,i+0.5),sc(g2,j+0.5)); const dz=zS(mid.x,mid.y)-SEA; return clamp(dz/(AMP*0.9),0,1); };
  const centerBias=(x)=>{const t=(x+R()*0.25); return Math.max(0,1-Math.abs(t));};
  const wantCell=(i,j)=>{
    if(!cellAboveSea(i,j)) return false;
    const cb = centerBias( (i/(RADIUS)) ) * centerBias( (j/(RADIUS)) );
    const p  = 0.08 + 0.55*dryFactor(i,j) * (0.35+0.65*cb);
    return R()<p;
  };
  const candidates=[]; for(let j=jMin;j<=jMax;j++) for(let i=iMin;i<=iMax;i++) candidates.push({i,j});
  candidates.sort(()=>R()-0.5);
  let built=0, MAX_BUILD=5000;
  for(const {i,j} of candidates){
    if(built>=MAX_BUILD) break;
    if(used.has(kkey(i,j))||!wantCell(i,j)) continue;
    used.add(kkey(i,j)); used.add(kkey(i+1,j)); used.add(kkey(i,j+1)); used.add(kkey(i+1,j+1));
    const P00=Wstatic(add(sc(g1,i),   sc(g2,j)));
    const P10=Wstatic(add(sc(g1,i+1), sc(g2,j)));
    const P01=Wstatic(add(sc(g1,i),   sc(g2,j+1)));
    const P11=Wstatic(add(sc(g1,i+1), sc(g2,j+1)));
    const htBase=STEP*(0.9+R()*3.1), Ht= htBase*(0.5+0.8*dryFactor(i,j));
    const T00={x:P00.x,y:P00.y-Ht}, T10={x:P10.x,y:P10.y-Ht}, T01={x:P01.x,y:P01.y-Ht}, T11={x:P11.x,y:P11.y-Ht};
    const hue=(H0+(R()*24-12)|0), Ssat=62+((R()*12)|0);
    const fillL=col(hue,   Ssat,38), fillR=col(hue+8,Ssat,46),
          fillF=col(hue+4, Ssat,34), fillB=col(hue-6,Ssat,30), fillT=col(hue+2,Ssat,72);
    const depthKey=(P00.y+P01.y+P10.y+P11.y)/4;
    faces.push(
      {k:depthKey, pts:[T00,T01,P01,P00], fill:fillL},
      {k:depthKey, pts:[T10,T11,P11,P10], fill:fillR},
      {k:depthKey, pts:[T10,T00,P00,P10], fill:fillF},
      {k:depthKey, pts:[T11,T01,P01,P11], fill:fillB},
      {k:(T00.y+T01.y+T10.y+T11.y)/4, pts:[T10,T11,T01,T00], fill:fillT}
    );
    built++;
  }
  faces.sort((a,b)=>a.k-b.k);
  for(const f of faces) Gcity.appendChild(E('polygon',{points:polyPts(f.pts),fill:f.fill}));

  // ── animation: grid traverses the waveform & lattice slides by whole steps ─
  const t0=performance.now(), ω=2*Math.PI/LOOP_SECS;
  function drawGridAt(t){
    // lattice origin shift: exactly k whole steps over one loop → perfect tiling
    const u=t/LOOP_SECS;
    const O=add(sc(g1, FLOW_STEPS_G1*u), sc(g2, FLOW_STEPS_G2*u));

    for(const L of lines){
      const a=add(O,L.a), b=add(O,L.b);
      let d=`M `, x,y, u0, p;
      for(let k=0;k<=RES;k++){
        u0=k/RES; x=a.x+(b.x-a.x)*u0; y=a.y+(b.y-a.y)*u0;
        p=Wgrid({x,y}, t);
        d += (k?` L `:``)+p.x+` `+p.y;
      }
      L.el.setAttribute('d',d);
    }
  }
  function frame(){
    const t=((performance.now()-t0)/1000)%LOOP_SECS;
    drawGridAt(t);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // debug
  SVG.setAttribute('data-buildings',String(built));
  SVG.setAttribute('data-step',String(STEP));
  SVG.setAttribute('data-angles',`${A1.toFixed(1)},${A2.toFixed(1)}`);
})();
