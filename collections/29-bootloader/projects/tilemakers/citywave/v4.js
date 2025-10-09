(()=>{
  const SVG=BTLDR&&BTLDR.svg; if(!SVG) throw new Error('BTLDR.svg missing');
  const R=BTLDR.rnd, E=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,String(a[k]));return e};
  const S=900; SVG.setAttribute('viewBox',`0 0 ${S} ${S}`); SVG.setAttribute('preserveAspectRatio','xMidYMid meet');

  // ── loop + lattice ──────────────────────────────────────────────────────────
  const LOOP_SECS=8, STEP=Math.round(10+R()*50), LINES=Math.ceil((S*2.4)/STEP);
  const FLOW_STEPS_G1=1, FLOW_STEPS_G2=1, FLOW_M1=1, FLOW_M2=1; // integers ⇒ perfect loop

  const rad=d=>d*Math.PI/180, add=(a,b)=>({x:a.x+b.x,y:a.y+b.y}), sc=(a,k)=>({x:a.x*k,y:a.y*k}), clamp=(x,a,b)=>x<a?a:x>b?b:x;
  const A1=5+R()*20, SEP=110+R()*30, A2=A1+SEP;
  const g1={x:Math.cos(rad(A1))*STEP, y:Math.sin(rad(A1))*STEP};
  const g2={x:Math.cos(rad(A2))*STEP, y:Math.sin(rad(A2))*STEP};

  // ── palette ─────────────────────────────────────────────────────────────────
  const H0=(R()*360|0), col=(h,s,l,a=1)=>`hsl(${(h%360+360)%360} ${s}% ${l}% / ${a})`;
  const grid1=col(H0,30,40,.6), grid2=col(H0+12,30,40,.6), waterCol=col(H0+190,45,55,.18);
  const cityL=(h)=>col(h,62,38), cityR=(h)=>col(h+8,62,46), cityF=(h)=>col(h+4,62,34), cityB=(h)=>col(h-6,62,30), cityT=(h)=>col(h+2,62,72);

  // ── terrain (time-phased) ───────────────────────────────────────────────────
  const AMP=STEP*(1.8+R()*2.4), f1=0.004+R()*0.004, f2=0.006+R()*0.004;
  const th1=rad(R()*360), th2=rad(R()*360), n1={x:Math.cos(th1),y:Math.sin(th1)}, n2={x:Math.cos(th2),y:Math.sin(th2)};
  const p1={x:-n1.y,y:n1.x}, p2={x:-n2.y,y:n2.x}, Kx=0.9, Ky=1.0;
  const ω1=2*Math.PI*FLOW_M1/LOOP_SECS, ω2=2*Math.PI*FLOW_M2/LOOP_SECS;
  const zT=(x,y,t)=>AMP*(0.6*Math.sin((x*n1.x+y*n1.y)*f1+ω1*t)+0.4*Math.sin((x*n2.x+y*n2.y)*f2+ω2*t));
  const dz1T=(x,y,t)=>AMP*0.6*f1*Math.cos((x*n1.x+y*n1.y)*f1+ω1*t);
  const dz2T=(x,y,t)=>AMP*0.4*f2*Math.cos((x*n2.x+y*n2.y)*f2+ω2*t);
  const Wt=(p,t)=>{const h=zT(p.x,p.y,t),sx=dz1T(p.x,p.y,t)*p1.x+dz2T(p.x,p.y,t)*p2.x;return {x:p.x+Kx*sx,y:p.y-Ky*h,h}};

  // ── containers & bands (for painter's order with minimal churn) ─────────────
  const Root=E('g',{}), Ggrid=E('g',{}), Gwater=E('g',{}), Gcity=E('g',{}); Root.append(Ggrid,Gwater,Gcity); SVG.appendChild(Root);
  const NBANDS=9, WBANDS=4; const cityBands=[...Array(NBANDS)].map(()=>E('g',{})), waterBands=[...Array(WBANDS)].map(()=>E('g',{}));
  cityBands.forEach(g=>Gcity.appendChild(g)); waterBands.forEach(g=>Gwater.appendChild(g));

  // ── curved grid (repath each frame) ─────────────────────────────────────────
  const SPAN=LINES*2+6, RES=80, lines=[];
  const mkLine=(a,b,stroke)=>{const el=E('path',{fill:'none',stroke,'stroke-width':1.1,'stroke-linecap':'round','stroke-linejoin':'round'}); Ggrid.appendChild(el); lines.push({a,b,el});};
  for(let k=-LINES-2;k<=LINES+2;k++){ const off=sc(g2,k), a=add(off,sc(g1,-SPAN)), b=add(off,sc(g1,SPAN)); mkLine(a,b,grid1); }
  for(let k=-LINES-2;k<=LINES+2;k++){ const off=sc(g1,k), a=add(off,sc(g2,-SPAN)), b=add(off,sc(g2,SPAN)); mkLine(a,b,grid2); }
  const drawGrid=(t,off)=>{ for(const L of lines){ const a=add(off,L.a), b=add(off,L.b); let d='M '; for(let k=0;k<=RES;k++){ const u=k/RES, p=Wt({x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u},t); d+=(k?' L ':'')+p.x+' '+p.y; } L.el.setAttribute('d',d); }};

  // ── water quads (re-eval each frame, reuse elements) ────────────────────────
  const SEA=-AMP*0.08;
  const waterCells=[]; // each: {i,j,el,band}
  const waterBandOfY=y=>clamp((y/S*WBANDS)|0,0,WBANDS-1);
  for(let j=-LINES+1;j<LINES-2;j+=2){
    for(let i=-LINES+1;i<LINES-2;i+=2){
      const el=E('polygon',{fill:waterCol,points:''}); waterBands[0].appendChild(el);
      waterCells.push({i,j,el,band:0});
    }
  }
  const drawWater=(t,off)=>{
    for(const c of waterCells){
      const P0=Wt(add(off,add(sc(g1,c.i),   sc(g2,c.j   ))),t);
      const P1=Wt(add(off,add(sc(g1,c.i+1), sc(g2,c.j   ))),t);
      const P2=Wt(add(off,add(sc(g1,c.i+1), sc(g2,c.j+1))),t);
      const P3=Wt(add(off,add(sc(g1,c.i),   sc(g2,c.j+1))),t);
      // below sea if *all* corners under SEA (simple fill; optionally edge-clipping could be added)
      const sub = (P0.h<SEA&&P1.h<SEA&&P2.h<SEA&&P3.h<SEA);
      if(!sub){ c.el.setAttribute('display','none'); continue; } else c.el.removeAttribute('display');
      const yAvg=(P0.y+P1.y+P2.y+P3.y)*0.25, bNew=waterBandOfY(yAvg);
      if(bNew!==c.band){ waterBands[bNew].appendChild(c.el); c.band=bNew; }
      c.el.setAttribute('points',`${P0.x},${P0.y} ${P1.x},${P1.y} ${P2.x},${P2.y} ${P3.x},${P3.y}`);
    }
  };

  // ── buildings (sites fixed; geometry & height recomputed each frame) ────────
  const RADIUS=LINES-3, iMin=-RADIUS, iMax=RADIUS-1, jMin=-RADIUS, jMax=RADIUS-1;
  const used=new Set(), kkey=(i,j)=>i+'_'+j;
  const centerBias=x=>{const t=(x+R()*0.25); return Math.max(0,1-Math.abs(t));};
  const wantCell=(i,j)=>{
    // use static check at t=0 only for site selection (stability); geometry updates use zT
    const mid=add(sc(g1,i+0.5),sc(g2,j+0.5));
    const z0=zT(mid.x,mid.y,0)-SEA, dry=clamp(z0/(AMP*0.9),0,1);
    const cb=centerBias(i/RADIUS)*centerBias(j/RADIUS);
    const p=0.08+0.55*dry*(0.35+0.65*cb);
    return p>R();
  };
  const candidates=[]; for(let j=jMin;j<=jMax;j++) for(let i=iMin;i<=iMax;i++) candidates.push({i,j});
  candidates.sort(()=>R()-0.5);

  const MAX_BUILD=900, NBH=E('g',{}); // optional extra group for city faces (keeps DOM neat)
  Gcity.appendChild(NBH);

  const bandOfY=(y,minY,maxY)=>clamp(Math.floor(((y-minY)/Math.max(1,maxY-minY))*NBANDS),0,NBANDS-1);
  const sites=[], faces=[]; // sites: per building constants; faces: per face SVG elems
  let built=0;
  for(const {i,j} of candidates){
    if(built>=MAX_BUILD) break;
    if(used.has(kkey(i,j))) continue;
    if(!wantCell(i,j)) continue;
    used.add(kkey(i,j)); used.add(kkey(i+1,j)); used.add(kkey(i,j+1)); used.add(kkey(i+1,j+1));
    const hue=(H0+(R()*24-12)|0), htBase=STEP*(0.9+R()*3.1);
    const poly=(fill)=>{const el=E('polygon',{fill,points:''}); cityBands[0].appendChild(el); return el;};
    const fL=poly(cityL(hue)), fR=poly(cityR(hue)), fF=poly(cityF(hue)), fB=poly(cityB(hue)), fT=poly(cityT(hue));
    sites.push({i,j,hue,htBase,fL,fR,fF,fB,fT,band:0,depthY:0});
    built++;
  }

  // track min/max y to map into bands each frame
  function updateBuildings(t,off){
    let minY=1e9, maxY=-1e9;
    // first pass compute depths
    for(const s of sites){
      const P00=Wt(add(off,add(sc(g1,s.i),   sc(g2,s.j   ))),t);
      const P10=Wt(add(off,add(sc(g1,s.i+1), sc(g2,s.j   ))),t);
      const P01=Wt(add(off,add(sc(g1,s.i),   sc(g2,s.j+1))),t);
      const P11=Wt(add(off,add(sc(g1,s.i+1), sc(g2,s.j+1))),t);
      const mid=Wt(add(off,add(sc(g1,s.i+0.5),sc(g2,s.j+0.5))),t);
      const dry=clamp((mid.h-SEA)/(AMP*0.9),0,1);
      const Ht=s.htBase*(0.5+0.8*dry);
      const T00={x:P00.x,y:P00.y-Ht}, T10={x:P10.x,y:P10.y-Ht}, T01={x:P01.x,y:P01.y-Ht}, T11={x:P11.x,y:P11.y-Ht};
      s.geom={P00,P10,P01,P11,T00,T10,T01,T11};
      const dy=(P00.y+P01.y+P10.y+P11.y)/4; s.depthY=dy;
      if(dy<minY)minY=dy; if(dy>maxY)maxY=dy;
    }
    // second pass: assign bands & update polygons
    for(const s of sites){
      const bNew=bandOfY(s.depthY,minY,maxY);
      if(bNew!==s.band){ cityBands[bNew].appendChild(s.fL); cityBands[bNew].appendChild(s.fR); cityBands[bNew].appendChild(s.fF); cityBands[bNew].appendChild(s.fB); cityBands[bNew].appendChild(s.fT); s.band=bNew; }
      const {P00,P10,P01,P11,T00,T10,T01,T11}=s.geom;
      s.fL.setAttribute('points',`${T00.x},${T00.y} ${T01.x},${T01.y} ${P01.x},${P01.y} ${P00.x},${P00.y}`);
      s.fR.setAttribute('points',`${T10.x},${T10.y} ${T11.x},${T11.y} ${P11.x},${P11.y} ${P10.x},${P10.y}`);
      s.fF.setAttribute('points',`${T10.x},${T10.y} ${T00.x},${T00.y} ${P00.x},${P00.y} ${P10.x},${P10.y}`);
      s.fB.setAttribute('points',`${T11.x},${T11.y} ${T01.x},${T01.y} ${P01.x},${P01.y} ${P11.x},${P11.y}`);
      s.fT.setAttribute('points',`${T10.x},${T10.y} ${T11.x},${T11.y} ${T01.x},${T01.y} ${T00.x},${T00.y}`);
    }
  }

  // ── animation driver ────────────────────────────────────────────────────────
  const t0=performance.now();
  function frame(){
    const t=((performance.now()-t0)/1000)%LOOP_SECS;
    const u=t/LOOP_SECS, off=add(sc(g1,FLOW_STEPS_G1*u),sc(g2,FLOW_STEPS_G2*u)); // slide lattice by whole steps over one loop
    drawGrid(t,off);
    drawWater(t,off);
    updateBuildings(t,off);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // debug
  SVG.setAttribute('data-buildings',String(sites.length));
  SVG.setAttribute('data-step',String(STEP));
  SVG.setAttribute('data-angles',`${A1.toFixed(1)},${A2.toFixed(1)}`);
})();
