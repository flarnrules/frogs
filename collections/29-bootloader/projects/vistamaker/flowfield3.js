(()=>{
  // ───────── minimal setup ─────────
  const M=Math, R=()=>BTLDR.rnd();
  const SV=BTLDR.svg, S=512;
  const E=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,String(a[k]));return e};
  const clamp=(x,a,b)=>M.max(a,M.min(b,x));
  SV.setAttribute('viewBox','0 0 512 512');
  SV.setAttribute('preserveAspectRatio','xMidYMid meet');
  SV.setAttribute('width','100%'); SV.setAttribute('height','100%'); SV.setAttribute('overflow','visible');

  // ───────── curve helpers (seed → interesting distributions) ─────────
  const u = ()=>R();
  const powCurve  =(x,p)=>M.pow(clamp(x,0,1),p);
  const smoothstep=(x)=>{x=clamp(x,0,1); return x*x*(3-2*x)};
  const expoCurve =(x,k)=>1-M.exp(-k*clamp(x,0,1));
  const map = (x,a,b)=>a+(b-a)*x;

  function sampleRange(a,b,shape='pow',k=2){
    let x=u();
    if(shape==='pow')        x = powCurve(x,k);
    else if(shape==='spow')  x = 1-powCurve(1-x,k);
    else if(shape==='smooth')x = smoothstep(x);
    else if(shape==='expo')  x = expoCurve(x,k);
    x = clamp(x + (u()-.5)*0.02, 0, 1);   // tiny jitter
    return map(x,a,b);
  }

  // ───────── tunable ranges ─────────
  const RANGES = {
    CURL:           {min:0.01, max:3, shape:'smooth', k:2.2},
    FIELD_RES:      {min:0.01,   max:6,   shape:'spow',  k:2.0},
    UNWIND_START:   {min:S*0.08, max:S*2.40, shape:'smooth', k:2.0},
    UNWIND_END:     {min:S*0.04, max:S*2.22, shape:'pow',   k:1.6},
    UNWIND_STRENGTH:{min:0.05, max:2.95, shape:'spow',    k:2.4},
    NOISE_W:        {min:0.01, max:3.28, shape:'pow',      k:2.2},
    STEP:           {min:35,    max:125,   shape:'smooth',   k:2.0},
    MAX_STEPS:      {min:35,  max:125,  shape:'spow',     k:2.0},
    SPEED_PPS:      {min:12,   max:50,   shape:'spow',     k:2.2},
    RAYS:           {min:50,  max:100,  shape:'spow',     k:2.5},
    SEG:            {min:10,   max:30,   shape:'pow',      k:1.8},
    GAP:            {min:5,   max:55,   shape:'pow',      k:1.8},
    PIX:            {min:5,    max:45,    shape:'pow',      k:2.0},
  };

  // bg (optional)
  const baseHue = (360*R())|0, baseHue2=(baseHue+18)%360;
  const D = E('defs',{}); SV.appendChild(D);
  const gBG=E('linearGradient',{id:'dbg',x1:'0',y1:'0',x2:'0',y2:'1'});
  gBG.appendChild(E('stop',{offset:'0%','stop-color':`hsl(${baseHue} 30% 86%)`}));
  gBG.appendChild(E('stop',{offset:'100%','stop-color':`hsl(${baseHue2} 30% 72%)`}));
  D.appendChild(gBG);
  SV.appendChild(E('rect',{x:0,y:0,width:'100%',height:'100%',fill:'url(#dbg)'}));

  // randomize parameters
  const CURL = sampleRange(RANGES.CURL.min, RANGES.CURL.max, RANGES.CURL.shape, RANGES.CURL.k);
  const FIELD_RES = (sampleRange(RANGES.FIELD_RES.min, RANGES.FIELD_RES.max, RANGES.FIELD_RES.shape, RANGES.FIELD_RES.k)|0);
  const UNWIND_START = sampleRange(RANGES.UNWIND_START.min, RANGES.UNWIND_START.max, RANGES.UNWIND_START.shape, RANGES.UNWIND_START.k);
  const UNWIND_END   = sampleRange(RANGES.UNWIND_END.min,   RANGES.UNWIND_END.max,   RANGES.UNWIND_END.shape,   RANGES.UNWIND_END.k);
  const UNWIND_STRENGTH = sampleRange(RANGES.UNWIND_STRENGTH.min, RANGES.UNWIND_STRENGTH.max, RANGES.UNWIND_STRENGTH.shape, RANGES.UNWIND_STRENGTH.k);
  const NOISE_W = sampleRange(RANGES.NOISE_W.min, RANGES.NOISE_W.max, RANGES.NOISE_W.shape, RANGES.NOISE_W.k);
  const STEP = (sampleRange(RANGES.STEP.min, RANGES.STEP.max, RANGES.STEP.shape, RANGES.STEP.k)|0);
  const MAX_STEPS = (sampleRange(RANGES.MAX_STEPS.min, RANGES.MAX_STEPS.max, RANGES.MAX_STEPS.shape, RANGES.MAX_STEPS.k)|0);
  const SPEED_PPS = sampleRange(RANGES.SPEED_PPS.min, RANGES.SPEED_PPS.max, RANGES.SPEED_PPS.shape, RANGES.SPEED_PPS.k);
  const RAYS = (sampleRange(RANGES.RAYS.min, RANGES.RAYS.max, RANGES.RAYS.shape, RANGES.RAYS.k)|0);
  const SEG = sampleRange(RANGES.SEG.min, RANGES.SEG.max, RANGES.SEG.shape, RANGES.SEG.k);
  const GAP = sampleRange(RANGES.GAP.min, RANGES.GAP.max, RANGES.GAP.shape, RANGES.GAP.k);
  const PIX = (sampleRange(RANGES.PIX.min, RANGES.PIX.max, RANGES.PIX.shape, RANGES.PIX.k)|0);

  // static noise axes
  const NAX = 0.0026 + R()*0.0009, NAY = 0.0029 + R()*0.0009, NPR = R()*1000;

  // sun (we’ll render flow first so it sits behind)
  const Cx = 256 + (R()-.5)*60, Cy = 256 + (R()-.5)*60;
  const sunR = 18 + R()*20;
  const sunGrad=E('radialGradient',{id:'sunField',gradientUnits:'userSpaceOnUse',cx:Cx,cy:Cy,r:260});
  sunGrad.appendChild(E('stop',{offset:'0%','stop-color':'#fff','stop-opacity':.97}));
  sunGrad.appendChild(E('stop',{offset:'55%','stop-color':`hsl(${(baseHue+58)%360} 92% 61%)`,'stop-opacity':.97}));
  sunGrad.appendChild(E('stop',{offset:'100%','stop-color':`hsl(${(baseHue+50)%360} 88% 50%)`,'stop-opacity':.96}));
  D.appendChild(sunGrad);

  // ───────── build static flow field ─────────
  const FX = M.ceil(S/FIELD_RES), FY = M.ceil(S/FIELD_RES);
  const field = new Float32Array(FX*FY);
  const idx=(x,y)=>y*FX+x;
  const sigmoid = u=>1/(1+M.exp(-6*(u-0.5)));
  const kCurlBase = 0.9 * sigmoid(CURL);
  const noisePot = (x,y)=> M.sin(x*NAX + NPR)*0.5 + M.sin(y*NAY + NPR*0.77)*0.5;

  for(let i=0, gy=0; gy<FY; gy++){
    const cy=(gy+0.5)*FIELD_RES;
    for(let gx=0; gx<FX; gx++, i++){
      const cx=(gx+0.5)*FIELD_RES;
      const dx=cx-Cx, dy=cy-Cy, r=M.hypot(dx,dy)+1e-6;
      const urx=dx/r,  ury=dy/r;              // radial unit
      const utx=-ury,  uty=urx;               // tangential unit
      const rf = clamp((r-UNWIND_START)/(UNWIND_START-UNWIND_END), 0, 1);
      const kCurl = kCurlBase*(1-UNWIND_STRENGTH*rf);

      // static spread from potential gradient (same for all rays)
      const eps=1.0, gxP=noisePot(cx+eps,cy)-noisePot(cx-eps,cy), gyP=noisePot(cx,cy+eps)-noisePot(cx,cy-eps);
      let gmx=-gxP, gmy=-gyP; const gm=M.hypot(gmx,gmy)||1; gmx/=gm; gmy/=gm;

      const vx=urx + utx*kCurl + gmx*NOISE_W;
      const vy=ury + uty*kCurl + gmy*NOISE_W;
      field[i]=M.atan2(vy,vx);
    }
  }

  // bilinear angle sampling (vector lerp on unit circle)
  const sampleAngle=(x,y)=>{
    const gx=x/FIELD_RES, gy=y/FIELD_RES;
    const x0=clamp(gx|0,0,FX-1), y0=clamp(gy|0,0,FY-1);
    const x1=M.min(FX-1,x0+1),  y1=M.min(FY-1,y0+1);
    const tx=clamp(gx-x0,0,1),  ty=clamp(gy-y0,0,1);
    const a00=field[idx(x0,y0)], a10=field[idx(x1,y0)], a01=field[idx(x0,y1)], a11=field[idx(x1,y1)];
    const v=(a)=>({x:M.cos(a),y:M.sin(a)});
    const v00=v(a00), v10=v(a10), v01=v(a01), v11=v(a11);
    const vx0=v00.x*(1-tx)+v10.x*tx, vy0=v00.y*(1-tx)+v10.y*tx;
    const vx1=v01.x*(1-tx)+v11.x*tx, vy1=v01.y*(1-tx)+v11.y*tx;
    const vx=vx0*(1-ty)+vx1*ty,     vy=vy0*(1-ty)+vy1*ty;
    return M.atan2(vy,vx);
  };

  // streamline integrator
  const snap=v=> PIX? M.round(v/PIX)*PIX : v;
  const integrate=(x0,y0)=>{
    let x=x0, y=y0, d=`M ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`;
    for(let i=0;i<MAX_STEPS;i++){
      const a1=sampleAngle(x,y);
      const mx=x+M.cos(a1)*(STEP*0.5), my=y+M.sin(a1)*(STEP*0.5);
      const a2=sampleAngle(mx,my);
      x+=M.cos(a2)*STEP; y+=M.sin(a2)*STEP;
      d+=` L ${snap(x).toFixed(2)} ${snap(y).toFixed(2)}`;
      if(x<-2||x>S+2||y<-2||y>S+2) break;
    }
    return d;
  };

  // flow group FIRST (renders behind the sun)
  const flux=E('g',{}); SV.appendChild(flux);

  // uniform dash + continuous motion (no pulse)
  const cyc = SEG + GAP;
  const DUR = (cyc / SPEED_PPS).toFixed(2) + 's';

  const draw=(path)=>{
    const phase0 = R()*cyc;
    const p=E('path',{
      d:path, fill:'none', stroke:'url(#sunField)',
      'stroke-width':1.25, 'stroke-linecap':'round', 'stroke-opacity':.94,
      'stroke-dasharray':`${SEG} ${GAP}`, 'stroke-dashoffset':phase0
    });
    p.appendChild(E('animate',{attributeName:'stroke-dashoffset',begin:'0s',dur:DUR,by:String(-cyc),repeatCount:'indefinite'}));
    flux.appendChild(p);
  };

  // seed rays on sun rim (even coverage)
  const GOLD = M.PI*(3-M.sqrt(5)), phase = R()*2*M.PI, r0=sunR+1.5;
  for(let i=0;i<RAYS;i++){
    const ang = phase + i*GOLD;
    const x0=Cx+M.cos(ang)*r0, y0=Cy+M.sin(ang)*r0;
    draw(integrate(x0,y0));
  }

  // SUN on top
  SV.appendChild(E('circle',{cx:Cx,cy:Cy,r:sunR,fill:'url(#sunField)'}));
})();
