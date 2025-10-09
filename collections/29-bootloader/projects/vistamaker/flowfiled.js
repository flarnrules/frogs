(()=>{
  // ───────── setup ─────────
  const M=Math, R=()=>BTLDR.rnd();
  const SV=BTLDR.svg, S=512;
  const E=(t,a,h)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,String(a[k]));h!=null&&(e.textContent=h);return e};
  const A=(el,begin=0,dur='0.45s')=>{el.setAttribute('opacity','0');el.appendChild(E('animate',{attributeName:'opacity',begin:begin+'s',dur,to:1,fill:'freeze'}))};
  const clamp=(x,a,b)=>M.max(a,M.min(b,x));
  const hue=h=>((h%360)+360)%360;

  // ───────── knobs ─────────
  const SHOW_UP_TO = 6;          // 1..6: reveal up to this stage
  const BUILD_PAUSE = 0.25;      // delay between stage reveals (s)

  // flow controls
  const CURL = 0.6;              // 0..1: straight → curly
  const INTENSITY = 1.0;         // >1 exaggerates curl
  const FIELD_RES = 32;          // px per vector cell (field fidelity)
  const STEP = 1;                // streamline step in px
  const MAX_STEPS = 1000;         // segment cap per ray

  // ray controls
  const DENS_RES = 1;           // px per density cell (bigger → fewer overlaps)
  const DENS_MAX = 64;            // stop when local density reaches this
  const RAYS = 100;              // number of sun-origin rays
  const EDGE_RAYS = 0;           // optional extra rays from edges (0 to disable)

  // animation speed (pixels per second effectively = (dash distance)/duration)
  const FLOW_SPEED = 50.0;        // 0.5=half speed, 1=normal, 2=2× speed

  // pixelation (reduces unique points & cost)
  const PIX = 8;                 // 1=off-ish, 2–3=crisp & cheaper

  // vector field visualization (L-shaped markers)
  const ARROW_SKIP  = 2;                         // show every Nth cell
  const ARROW_LEN   = FIELD_RES * 0.42;          // shaft length
  const L_SIZE      = Math.max(4, FIELD_RES*0.22); // size of the "L" at the tip
  const ARROW_THICK = 1.5;

  // ───────── SVG base ─────────
  SV.setAttribute('viewBox','0 0 512 512');
  SV.setAttribute('preserveAspectRatio','xMidYMid meet');
  SV.setAttribute('width','100%'); SV.setAttribute('height','100%'); SV.setAttribute('overflow','visible');

  const D=E('defs',{}); SV.appendChild(D);

  // bg gradient
  const h0=hue(R()*360);
  const bg1=`hsl(${h0} 30% 86%)`, bg2=`hsl(${hue(h0+18)} 30% 72%)`;
  const gBG=E('linearGradient',{id:'dbg',x1:'0',y1:'0',x2:'0',y2:'1'});
  gBG.appendChild(E('stop',{offset:'0%','stop-color':bg1}));
  gBG.appendChild(E('stop',{offset:'100%','stop-color':bg2}));
  D.appendChild(gBG);
  SV.appendChild(E('rect',{x:0,y:0,width:'100%',height:'100%',fill:'url(#dbg)'}));

  // layers per stage
  const G1=E('g',{}), G2=E('g',{}), G3=E('g',{}), G4=E('g',{}), G5=E('g',{}), G6=E('g',{});
  const Ls=[null,G1,G2,G3,G4,G5,G6]; for(let s=1;s<=6;s++) SV.appendChild(Ls[s]);
  let t=0; const reveal=s=>{ if(SHOW_UP_TO>=s) A(Ls[s], t, '0.35s'); t+=BUILD_PAUSE; };

  // ───────── 1) grid ─────────
  const grid=E('g',{'shape-rendering':'crispEdges'});
  const gStep=32;
  for(let x=0;x<=S;x+=gStep) grid.appendChild(E('path',{d:`M ${x} 0 L ${x} ${S}`,stroke:'rgba(0,0,0,.06)','stroke-width':(x%128?1:1.2)}));
  for(let y=0;y<=S;y+=gStep) grid.appendChild(E('path',{d:`M 0 ${y} L ${S} ${y}`,stroke:'rgba(0,0,0,.06)','stroke-width':(y%128?1:1.2)}));
  G1.appendChild(grid); reveal(1);

  // ───────── 2) sun (origin) ─────────
  const Cx = 256 + (R()-.5)*80, Cy = 256 + (R()-.5)*80;
  const sunR = 18 + R()*14;
  const sun1='#fff', sun2=`hsl(${hue(h0+58)} 92% 61%)`, sun3=`hsl(${hue(h0+50)} 88% 50%)`;
  const rayColorId='sunField';
  const gSun=E('radialGradient',{id:rayColorId,gradientUnits:'userSpaceOnUse',cx:Cx,cy:Cy,r:260});
  gSun.appendChild(E('stop',{offset:'0%','stop-color':sun1,'stop-opacity':.97}));
  gSun.appendChild(E('stop',{offset:'55%','stop-color':sun2,'stop-opacity':.97}));
  gSun.appendChild(E('stop',{offset:'100%','stop-color':sun3,'stop-opacity':.96}));
  D.appendChild(gSun);
  G2.appendChild(E('circle',{cx:Cx,cy:Cy,r:sunR,fill:'url(#'+rayColorId+')'}));
  reveal(2);

  // ───────── 3) eddies (vortices) ─────────
  const K = 2.6, curve=u=>(1-M.exp(-K*u))/(1-M.exp(-K)), GAIN=INTENSITY*curve(CURL);
  const VORT_CNT = 2 + (R()<.5?1:0) + (CURL>.65 && R()<.5 ? 1:0);
  const vort = new Array(VORT_CNT);
  for(let i=0;i<VORT_CNT;i++){
    const vx=S*R(), vy=S*R(), spin=(R()<.5?-1:1)*(0.8+1.2*R()), r2=(S/7 + S*R()/7);
    vort[i]={vx,vy,spin,r2};
    const mark=E('g',{}); // simple visual markers
    mark.appendChild(E('circle',{cx:vx,cy:vy,r:3,fill:'none',stroke:'#000','stroke-opacity':.25}));
    mark.appendChild(E('circle',{cx:vx,cy:vy,r:r2*0.55,fill:'none',stroke:'#000','stroke-opacity':.06}));
    G3.appendChild(mark);
  }
  reveal(3);

  // ───────── 4) vector field (build + L-markers) ─────────
  const FX = Math.ceil(S / FIELD_RES), FY = Math.ceil(S / FIELD_RES);
  const field = new Float32Array(FX*FY);
  const vecColor=`hsl(${hue(h0-30)} 70% 35%)`;
  const idx=(x,y)=>y*FX+x;

  // build angles (single pass; small inner loop over vortices)
  for(let i=0, gy=0; gy<FY; gy++){
    const cy=(gy+0.5)*FIELD_RES;
    for(let gx=0; gx<FX; gx++, i++){
      const cx=(gx+0.5)*FIELD_RES;
      // radial base
      const rx=cx-Cx, ry=cy-Cy, aRad=M.atan2(ry,rx);
      // eddy contribution (localized swirl)
      let dvx=0, dvy=0;
      for(let v=0; v<VORT_CNT; v++){
        const o=vort[v], dx=cx-o.vx, dy=cy-o.vy, d2=dx*dx+dy*dy+1e-4;
        const k=o.spin * M.exp(-d2/(o.r2*o.r2)) / M.sqrt(d2);
        dvx += -dy * k; dvy += dx * k; // perpendicular swirl
      }
      // gentle noise curl
      const curl = (M.sin(cx*0.0035 + Cy*0.0021) * .5 + M.sin(cy*0.0032 + Cx*0.0017) * .5);
      dvx += M.cos(aRad+M.PI/2)*curl; dvy += M.sin(aRad+M.PI/2)*curl;

      const vx=M.cos(aRad) + GAIN*0.45*dvx;
      const vy=Math.sin(aRad) + GAIN*0.45*dvy;
      field[i]=M.atan2(vy,vx);
    }
  }

  // draw L-shaped vectors in ONE path for perf
  const FIELDG=E('g',{'shape-rendering':'crispEdges'});
  let arrowsD='';
  for(let gy=0; gy<FY; gy+=ARROW_SKIP){
    const cy=(gy+0.5)*FIELD_RES;
    for(let gx=0; gx<FX; gx+=ARROW_SKIP){
      const cx=(gx+0.5)*FIELD_RES;
      const a = field[idx(gx,gy)];
      const dx=M.cos(a), dy=M.sin(a);
      const x0=cx, y0=cy;
      const x1=cx+dx*ARROW_LEN, y1=cy+dy*ARROW_LEN;
      const px=-dy, py=dx;
      const lx=x1+px*L_SIZE, ly=y1+py*L_SIZE;
      const bx=x1-dx*L_SIZE, by=y1-dy*L_SIZE;
      arrowsD += `M ${x0} ${y0} L ${x1} ${y1} M ${x1} ${y1} L ${lx} ${ly} M ${x1} ${y1} L ${bx} ${by}`;
    }
  }
  FIELDG.appendChild(E('path',{d:arrowsD,fill:'none',stroke:vecColor,'stroke-opacity':.55,'stroke-width':ARROW_THICK,'stroke-linecap':'round'}));
  G4.appendChild(FIELDG);
  reveal(4);

  // angle sampling (bilinear on unit circle)
  const sampleAngle=(x,y)=>{
    const gx=x/FIELD_RES, gy=y/FIELD_RES;
    const x0=clamp(gx|0,0,FX-1), y0=clamp(gy|0,0,FY-1);
    const x1=M.min(FX-1,x0+1), y1=M.min(FY-1,y0+1);
    const tx=clamp(gx-x0,0,1), ty=clamp(gy-y0,0,1);
    const a00=field[idx(x0,y0)], a10=field[idx(x1,y0)], a01=field[idx(x0,y1)], a11=field[idx(x1,y1)];
    const v=a=>({x:M.cos(a),y:M.sin(a)});
    const v00=v(a00), v10=v(a10), v01=v(a01), v11=v(a11);
    const vx0=v00.x*(1-tx)+v10.x*tx, vy0=v00.y*(1-tx)+v10.y*tx;
    const vx1=v01.x*(1-tx)+v11.x*tx, vy1=v01.y*(1-tx)+v11.y*tx;
    const vx=vx0*(1-ty)+vx1*ty, vy=vy0*(1-ty)+vy1*ty;
    return M.atan2(vy,vx);
  };

  // ───────── 5) density grid (visual) ─────────
  const DX=M.ceil(S/DENS_RES), DY=M.ceil(S/DENS_RES);
  const dens=new Uint8Array(DX*DY);
  const dIdx=(x,y)=>{const ix=(x/DENS_RES)|0, iy=(y/DENS_RES)|0; return (ix<0||iy<0||ix>=DX||iy>=DY)?-1: iy*DX+ix;};
  const getD=(x,y)=>{const id=dIdx(x,y); return id<0?0:dens[id];};
  const addD=(x,y)=>{const id=dIdx(x,y); if(id>=0 && dens[id]<255) { ++dens[id]; if(dens[id]===1){ // first visit: paint cell
      const cx=(id%DX)*DENS_RES, cy=((id/DX)|0)*DENS_RES;
      densG.appendChild(E('rect',{x:cx,y:cy,width:DENS_RES,height:DENS_RES,fill:'#000','fill-opacity':.03}));
  }}};

  const densG=E('g',{'shape-rendering':'crispEdges'});
  G5.appendChild(densG);
  reveal(5);

  // ───────── 6) streamlines (animated rays) ─────────
  const snap=v=> PIX? M.round(v/PIX)*PIX : v;
  const GOLD=M.PI*(3-M.sqrt(5)), phase=R()*2*M.PI;

  const startFromSun=(theta)=>{
    const r0 = sunR + 1.5; // start just outside rim
    let x = Cx + M.cos(theta)*r0;
    let y = Cy + M.sin(theta)*r0;
    if(getD(x,y)>=DENS_MAX) return null;

    let d=`M ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`;
    addD(x,y);

    for(let i=0;i<MAX_STEPS;i++){
      // RK2 (midpoint) integration
      const a1 = sampleAngle(x,y);
      const mx = x + M.cos(a1)*(STEP*0.5);
      const my = y + M.sin(a1)*(STEP*0.5);
      const a2 = sampleAngle(mx,my);

      x += M.cos(a2)*STEP;
      y += M.sin(a2)*STEP;

      if(x<-2||x>S+2||y<-2||y>S+2){ d+=` L ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`; break; }
      if(getD(x,y)>=DENS_MAX)      { d+=` L ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`; break; }

      d+=` L ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`;
      addD(x,y);
    }
    return d;
  };

  const flux=E('g',{'shape-rendering':'crispEdges'}); G6.appendChild(flux);

  // single helper to draw & animate, with FLOW_SPEED wired in
  const drawRay=(path,delay)=>{
    if(!path) return;
    const seg = 8 + R()*14;
    const gap = 12 + R()*20;
    const cyc = seg + gap;

    // scale duration by 1 / FLOW_SPEED (distance fixed)
    const baseDur = 8 + R()*5;
    const DUR = (baseDur / FLOW_SPEED).toFixed(2) + 's';

    const p=E('path',{
      d:path, fill:'none', stroke:'url(#'+rayColorId+')',
      'stroke-width':1.1+(R()*1.2),
      'stroke-linecap':'round','stroke-opacity':.92,
      'stroke-dasharray':`${seg} ${gap}`,'stroke-dashoffset':0, opacity:0
    });
    A(p,delay,(8+R()*5).toFixed(2)+'s');
    p.appendChild(E('animate',{attributeName:'stroke-dashoffset',begin:delay.toFixed(2)+'s',dur:DUR,values:`0;${-cyc}`,repeatCount:'indefinite'}));
    flux.appendChild(p);
  };

  // main rays (uniform angular coverage)
  for(let i=0;i<RAYS;i++){
    const ang = phase + i*GOLD + (R()-.5)*0.04;
    drawRay(startFromSun(ang), t + 0.02);
  }

  // optional edge infill (set EDGE_RAYS>0 to enable)
  if (EDGE_RAYS>0){
    const edgePts=[]; for(let i=0;i<=10;i++){const u=i/10; edgePts.push([u*S,0],[u*S,S],[0,u*S],[S,u*S])}
    let added=0;
    for(let k=0;k<edgePts.length && added<EDGE_RAYS;k++){
      const ex=edgePts[k][0], ey=edgePts[k][1];
      if(getD(ex,ey)>1) continue;
      let a=sampleAngle(ex,ey);
      const cx=ex-Cx, cy=ey-Cy; // if pointing outward, flip inward
      if(M.cos(a)*cx + M.sin(a)*cy > 0) a += M.PI;
      const path=startFromSun(a + (R()-.5)*0.1);
      if(!path) continue;
      drawRay(path, t + 0.06);
      added++;
    }
  }

  reveal(6);

  // labels
  const label=(row,txt)=>{G6.appendChild(E('text',{x:12,y:22+row*16,'font-family':'monospace','font-size':12,fill:'#333','fill-opacity':.6},txt))};
  label(0,'Flow Explainer (grid, sun, eddies, field, density, rays)');
  label(1,`CURL=${CURL.toFixed(2)} INTENS=${INTENSITY.toFixed(2)} FIELD_RES=${FIELD_RES} DENS_RES=${DENS_RES} STEP=${STEP} PIX=${PIX} SPEED=${FLOW_SPEED}`);
})();
