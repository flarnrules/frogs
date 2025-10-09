(()=>{
  const SVG=BTLDR&&BTLDR.svg; if(!SVG) throw new Error('BTLDR.svg missing');
  const R=BTLDR.rnd, E=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,String(a[k]));return e};
  const S=900; SVG.setAttribute('viewBox',`0 0 ${S} ${S}`); SVG.setAttribute('preserveAspectRatio','xMidYMid meet');

  // ── knobs ───────────────────────────────────────────────────────────────────
  const LOOP_SECS=8;
  const STEP=Math.round(10+R()*50);
  const LINES=Math.ceil((S*2.4)/STEP);
  const FLOW_STEPS_G1=1, FLOW_STEPS_G2=1; // lattice slides by whole steps per loop
  const FLOW_M1=1, FLOW_M2=1;             // integer sine cycles per loop

  // frame/window (square); tweak these
  const WINDOW_SIZE=0.86*S;               // inner window side length
  const FRAME_THICK=28;                   // stroke width
  const FRAME_COLOR='#121212';

  // ── basis / helpers ─────────────────────────────────────────────────────────
  const rad=d=>d*Math.PI/180, add=(a,b)=>({x:a.x+b.x,y:a.y+b.y}), sc=(a,k)=>({x:a.x*k,y:a.y*k}), clamp=(x,a,b)=>x<a?a:x>b?b:x;
  const polyPts=pts=>pts.map(p=>`${p.x},${p.y}`).join(' ');
  const A1=5+R()*20, SEP=110+R()*30, A2=A1+SEP;
  const g1={x:Math.cos(rad(A1))*STEP, y:Math.sin(rad(A1))*STEP};
  const g2={x:Math.cos(rad(A2))*STEP, y:Math.sin(rad(A2))*STEP};

  // palette
  const H0=(R()*360|0), col=(h,s,l,a=1)=>`hsl(${(h%360+360)%360} ${s}% ${l}% / ${a})`;
  const grid1=col(H0,30,40,.6), grid2=col(H0+12,30,40,.6), waterCol=col(H0+190,45,55,.18);
  const coastCol=col(H0+180,55,52,.25); // shoreline plane tint
  const cityL=h=>col(h,62,38), cityR=h=>col(h+8,62,46), cityF=h=>col(h+4,62,34), cityB=h=>col(h-6,62,30), cityT=h=>col(h+2,62,72);

  // terrain (time-phased; drives everything)
  const AMP=STEP*(1.8+R()*2.4), f1=0.004+R()*0.004, f2=0.006+R()*0.004;
  const th1=rad(R()*360), th2=rad(R()*360), n1={x:Math.cos(th1),y:Math.sin(th1)}, n2={x:Math.cos(th2),y:Math.sin(th2)};
  const p1={x:-n1.y,y:n1.x}, p2={x:-n2.y,y:n2.x}, Kx=0.9, Ky=1.0;
  const ω1=2*Math.PI*FLOW_M1/LOOP_SECS, ω2=2*Math.PI*FLOW_M2/LOOP_SECS;
  const zT=(x,y,t)=>AMP*(0.6*Math.sin((x*n1.x+y*n1.y)*f1+ω1*t)+0.4*Math.sin((x*n2.x+y*n2.y)*f2+ω2*t));
  const dz1T=(x,y,t)=>AMP*0.6*f1*Math.cos((x*n1.x+y*n1.y)*f1+ω1*t);
  const dz2T=(x,y,t)=>AMP*0.4*f2*Math.cos((x*n2.x+y*n2.y)*f2+ω2*t);
  const Wt=(p,t)=>{const h=zT(p.x,p.y,t),sx=dz1T(p.x,p.y,t)*p1.x+dz2T(p.x,p.y,t)*p2.x;return {x:p.x+Kx*sx,y:p.y-Ky*h,h}};

  // sea level
  const SEA=-AMP*0.08;

  // ── frame + clip (square window) ────────────────────────────────────────────
  const Root=E('g',{}); SVG.appendChild(Root);
  const defs=E('defs',{}); SVG.appendChild(defs);
  const cx=S/2, cy=S/2, W2=WINDOW_SIZE/2;
  const clipId='cw_clip_'+Math.floor(R()*1e9);
  const clip=E('clipPath',{id:clipId}); defs.appendChild(clip);
  clip.appendChild(E('rect',{x:cx-W2,y:cy-W2,width:WINDOW_SIZE,height:WINDOW_SIZE,rx:6,ry:6}));
  Root.setAttribute('clip-path',`url(#${clipId})`);

  // draw frame on top
  const Frame=E('rect',{x:cx-W2,y:cy-W2,width:WINDOW_SIZE,height:WINDOW_SIZE,fill:'none',stroke:FRAME_COLOR,'stroke-width':FRAME_THICK,'vector-effect':'non-scaling-stroke','paint-order':'stroke'});
  // containers (inside clip)
  const Ggrid=E('g',{}), Gwater=E('g',{}), Gcoast=E('g',{}), Gcity=E('g',{}); Root.append(Ggrid,Gwater,Gcoast,Gcity);

  // ── grid (repath each frame) ────────────────────────────────────────────────
  const SPAN=LINES*2+6, RES=80, lines=[];
  const mkLine=(a,b,stroke)=>{const el=E('path',{fill:'none',stroke,'stroke-width':1.1,'stroke-linecap':'round','stroke-linejoin':'round'}); Ggrid.appendChild(el); lines.push({a,b,el});};
  for(let k=-LINES-2;k<=LINES+2;k++){ const off=sc(g2,k), a=add(off,sc(g1,-SPAN)), b=add(off,sc(g1,SPAN)); mkLine(a,b,grid1); }
  for(let k=-LINES-2;k<=LINES+2;k++){ const off=sc(g1,k), a=add(off,sc(g2,-SPAN)), b=add(off,sc(g2,SPAN)); mkLine(a,b,grid2); }
  const drawGrid=(t,off)=>{ for(const L of lines){ const a=add(off,L.a), b=add(off,L.b); let d='M '; for(let k=0;k<=RES;k++){ const u=k/RES, p=Wt({x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u},t); d+=(k?' L ':'')+p.x+' '+p.y; } L.el.setAttribute('d',d);}};

  // ── water fill (update quads each frame) ────────────────────────────────────
  const waterCells=[]; // each: {i,j,el}
  for(let j=-LINES+1;j<LINES-2;j+=2) for(let i=-LINES+1;i<LINES-2;i+=2){ const el=E('polygon',{fill:waterCol,points:''}); Gwater.appendChild(el); waterCells.push({i,j,el}); }
  const drawWater=(t,off)=>{
    for(const c of waterCells){
      const P0=Wt(add(off,add(sc(g1,c.i),   sc(g2,c.j   ))),t);
      const P1=Wt(add(off,add(sc(g1,c.i+1), sc(g2,c.j   ))),t);
      const P2=Wt(add(off,add(sc(g1,c.i+1), sc(g2,c.j+1))),t);
      const P3=Wt(add(off,add(sc(g1,c.i),   sc(g2,c.j+1))),t);
      const sub=(P0.h<SEA&&P1.h<SEA&&P2.h<SEA&&P3.h<SEA);
      if(!sub){ c.el.setAttribute('display','none'); }
      else{
        c.el.removeAttribute('display');
        c.el.setAttribute('points',`${P0.x},${P0.y} ${P1.x},${P1.y} ${P2.x},${P2.y} ${P3.x},${P3.y}`);
      }
    }
  };

  // ── shoreline barrier (marching squares) ────────────────────────────────────
  const coastPath=E('path',{fill:coastCol,stroke:'none'}); Gcoast.appendChild(coastPath);
  function drawCoast(t,off){
    // Build many small quads where the sea cuts a cell (edge cases) and emit short strips; cheap approx “flat plane”.
    let d='';
    for(let j=-LINES+1;j<LINES-1;j++){
      for(let i=-LINES+1;i<LINES-1;i++){
        const P=[ add(off,add(sc(g1,i),   sc(g2,j   ))),
                  add(off,add(sc(g1,i+1), sc(g2,j   ))),
                  add(off,add(sc(g1,i+1), sc(g2,j+1))),
                  add(off,add(sc(g1,i),   sc(g2,j+1))) ];
        const Sval=P.map(q=>zT(q.x,q.y,t)-SEA);
        const code=(Sval[0]>0?1:0)|(Sval[1]>0?2:0)|(Sval[2]>0?4:0)|(Sval[3]>0?8:0);
        if(code===0||code===15) continue; // no crossing
        // linear interp helper on edge (A->B)
        const lerp=(A,B,sa,sb)=>{const u=sa/(sa-sb); return {x:A.x+(B.x-A.x)*u,y:A.y+(B.y-A.y)*u};};
        // edges: 0:(0-1),1:(1-2),2:(2-3),3:(3-0)
        const E0=lerp(P[0],P[1],Sval[0],Sval[1]), E1=lerp(P[1],P[2],Sval[1],Sval[2]),
              E2=lerp(P[2],P[3],Sval[2],Sval[3]), E3=lerp(P[3],P[0],Sval[3],Sval[0]);
        // cases (resolve simple ones; for ambigs use a consistent choice)
        // we emit tiny quads covering the "sea-side" near the boundary for a soft plane feel.
        const pushStrip=(A,B)=>{
          const n={x:B.y-A.y,y:-(B.x-A.x)}; // perp
          const len=Math.hypot(n.x,n.y)||1, pad=STEP*0.15, nx=n.x/len*pad, ny=n.y/len*pad;
          d+=`M ${A.x} ${A.y} L ${B.x} ${B.y} L ${B.x+nx} ${B.y+ny} L ${A.x+nx} ${A.y+ny} Z `;
        };
        switch(code){
          case 1: case 14: pushStrip(E3,E0); break;
          case 2: case 13: pushStrip(E0,E1); break;
          case 3: case 12: pushStrip(E3,E1); break;
          case 4: case 11: pushStrip(E1,E2); break;
          case 5:          pushStrip(E0,E1); pushStrip(E3,E2); break;
          case 6: case 9:  pushStrip(E0,E2); break;
          case 7: case 8:  pushStrip(E2,E3); break;
          case 10:         pushStrip(E0,E3); pushStrip(E1,E2); break;
        }
      }
    }
    coastPath.setAttribute('d',d);
  }

  // ── buildings (sites fixed; geometry rebuilt each frame; correct depth order)
  const RADIUS=LINES-3, iMin=-RADIUS, iMax=RADIUS-1, jMin=-RADIUS, jMax=RADIUS-1;
  const used=new Set(), kkey=(i,j)=>i+'_'+j;
  const centerBias=x=>{const t=(x+R()*0.25); return Math.max(0,1-Math.abs(t));};
  const wantCell=(i,j)=>{
    // choose sites using t=0 dryness (stable density)
    const mid=add(sc(g1,i+0.5),sc(g2,j+0.5));
    const z0=zT(mid.x,mid.y,0)-SEA, dry=clamp(z0/(AMP*0.9),0,1);
    const cb=centerBias(i/RADIUS)*centerBias(j/RADIUS);
    const p=0.08+0.55*dry*(0.35+0.65*cb);
    return p>R();
  };
  const candidates=[]; for(let j=jMin;j<=jMax;j++) for(let i=iMin;i<=iMax;i++) candidates.push({i,j});
  candidates.sort(()=>R()-0.5);

  const MAX_BUILD=900;
  const sites=[]; // each: {i,j,hue,htBase,g:<group>,faces:{L,R,F,B,T}, depth:0, hidden:false}
  let built=0;
  for(const {i,j} of candidates){
    if(built>=MAX_BUILD) break;
    if(used.has(kkey(i,j))||!wantCell(i,j)) continue;
    used.add(kkey(i,j)); used.add(kkey(i+1,j)); used.add(kkey(i,j+1)); used.add(kkey(i+1,j+1));
    const hue=(H0+(R()*24-12)|0), htBase=STEP*(0.9+R()*3.1);
    const g=E('g',{}); // per-building group (lets us sort by depth cleanly)
    // create faces once; order within a building: back, left, right, front, top (stable self-occlusion)
    const fB=E('polygon',{fill:cityB(hue)}), fL=E('polygon',{fill:cityL(hue)}),
          fR=E('polygon',{fill:cityR(hue)}), fF=E('polygon',{fill:cityF(hue)}),
          fT=E('polygon',{fill:cityT(hue)});
    g.append(fB,fL,fR,fF,fT); Gcity.appendChild(g);
    sites.push({i,j,hue,htBase,g,faces:{B:fB,L:fL,R:fR,F:fF,T:fT},depth:0,hidden:false});
    built++;
  }

  function updateBuildings(t,off){
    // compute depth and geometry, hide in water, then sort groups by depth
    for(const s of sites){
      const P00=Wt(add(off,add(sc(g1,s.i),   sc(g2,s.j   ))),t);
      const P10=Wt(add(off,add(sc(g1,s.i+1), sc(g2,s.j   ))),t);
      const P01=Wt(add(off,add(sc(g1,s.i),   sc(g2,s.j+1))),t);
      const P11=Wt(add(off,add(sc(g1,s.i+1), sc(g2,s.j+1))),t);
      const mid=Wt(add(off,add(sc(g1,s.i+0.5),sc(g2,s.j+0.5))),t);
      // hard cull: no buildings in water
      if(mid.h<SEA){ if(!s.hidden){s.g.setAttribute('display','none'); s.hidden=true;} continue; }
      if(s.hidden){ s.g.removeAttribute('display'); s.hidden=false; }
      const dry=clamp((mid.h-SEA)/(AMP*0.9),0,1);
      const Ht=s.htBase*(0.5+0.8*dry);
      const T00={x:P00.x,y:P00.y-Ht}, T10={x:P10.x,y:P10.y-Ht}, T01={x:P01.x,y:P01.y-Ht}, T11={x:P11.x,y:P11.y-Ht};
      // consistent winding (counter-clockwise quads) — fixes the “front/right not drawing” issue
      // left:  P00→P01→T01→T00
      s.faces.L.setAttribute('points',`${P00.x},${P00.y} ${P01.x},${P01.y} ${T01.x},${T01.y} ${T00.x},${T00.y}`);
      // right: P10→P11→T11→T10
      s.faces.R.setAttribute('points',`${P10.x},${P10.y} ${P11.x},${P11.y} ${T11.x},${T11.y} ${T10.x},${T10.y}`);
      // front: P10→P00→T00→T10
      s.faces.F.setAttribute('points',`${P10.x},${P10.y} ${P00.x},${P00.y} ${T00.x},${T00.y} ${T10.x},${T10.y}`);
      // back:  P01→P11→T11→T01
      s.faces.B.setAttribute('points',`${P01.x},${P01.y} ${P11.x},${P11.y} ${T11.x},${T11.y} ${T01.x},${T01.y}`);
      // top:   T00→T01→T11→T10
      s.faces.T.setAttribute('points',`${T00.x},${T00.y} ${T01.x},${T01.y} ${T11.x},${T11.y} ${T10.x},${T10.y}`);
      // depth key (avg base y)
      s.depth=(P00.y+P01.y+P10.y+P11.y)/4;
    }
    // sort visible buildings back→front and re-append groups (cheap enough at this count)
    const vis=sites.filter(s=>!s.hidden).sort((a,b)=>a.depth-b.depth);
    for(const s of vis) Gcity.appendChild(s.g);
  }

  // ── driver ──────────────────────────────────────────────────────────────────
  const t0=performance.now();
  function frame(){
    const t=((performance.now()-t0)/1000)%LOOP_SECS, u=t/LOOP_SECS;
    const off=add(sc(g1,FLOW_STEPS_G1*u),sc(g2,FLOW_STEPS_G2*u)); // lattice slide for perfect tiling
    drawGrid(t,off);
    drawWater(t,off);
    drawCoast(t,off);
    updateBuildings(t,off);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ── overlay frame on top (outside clip) ─────────────────────────────────────
  SVG.appendChild(Frame);

  // debug
  SVG.setAttribute('data-buildings',String(sites.length));
  SVG.setAttribute('data-step',String(STEP));
  SVG.setAttribute('data-angles',`${A1.toFixed(1)},${A2.toFixed(1)}`);
})();
