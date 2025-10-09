(()=>{
  const SVG=BTLDR&&BTLDR.svg; if(!SVG) throw new Error('BTLDR.svg missing');
  const R=BTLDR.rnd, NS='http://www.w3.org/2000/svg';
  const E=(t,a)=>{const el=document.createElementNS(NS,t);for(const k in a)el.setAttribute(k,String(a[k]));return el};
  const S=900; SVG.setAttribute('viewBox',`0 0 ${S} ${S}`); SVG.setAttribute('preserveAspectRatio','xMidYMid meet');

  // ---------- basis / grid ----------
  const ORIGIN={x:0,y:0};
  const STEP=Math.round(10+R()*50);
  const LINES=Math.ceil((S*2.4)/STEP);
  const A1=5+R()*20, SEP=110+R()*30, A2=A1+SEP, rad=d=>d*Math.PI/180;
  const g1={x:Math.cos(rad(A1))*STEP, y:Math.sin(rad(A1))*STEP};
  const g2={x:Math.cos(rad(A2))*STEP, y:Math.sin(rad(A2))*STEP};
  const add=(a,b)=>({x:a.x+b.x,y:a.y+b.y}), sc=(a,k)=>({x:a.x*k,y:a.y*k});
  const poly=pts=>pts.map(p=>`${p.x},${p.y}`).join(' ');

  // ---------- palette ----------
  const H0=(R()*360|0), col=(h,s,l,a=1)=>`hsl(${(h%360+360)%360} ${s}% ${l}% / ${a})`;
  const grid1=col(H0,30,40,.6), grid2=col(H0+12,30,40,.6);
  const waterCol=col(H0+190,45,55,.18);

  // ---------- terrain (strong curves) ----------
  const AMP=STEP*(1.8+R()*2.4);
  const f1=0.004+R()*0.004, f2=0.006+R()*0.004;
  const th1=rad(R()*360),  th2=rad(R()*360);
  const n1={x:Math.cos(th1),y:Math.sin(th1)}, n2={x:Math.cos(th2),y:Math.sin(th2)};
  const p1={x:-n1.y,y:n1.x}, p2={x:-n2.y,y:n2.x};
  const z  =(x,y)=> AMP*(0.6*Math.sin((x*n1.x+y*n1.y)*f1)+0.4*Math.sin((x*n2.x+y*n2.y)*f2));
  const dz1=(x,y)=> AMP*0.6*f1*Math.cos((x*n1.x+y*n1.y)*f1);
  const dz2=(x,y)=> AMP*0.4*f2*Math.cos((x*n2.x+y*n2.y)*f2);
  const Kx=0.9, Ky=1.0;
  const W=(p)=>{ // warp point to terrain
    const h=z(p.x,p.y), sx=dz1(p.x,p.y)*p1.x+dz2(p.x,p.y)*p2.x, sy=dz1(p.x,p.y)*p1.y+dz2(p.x,p.y)*p2.y;
    return {x:p.x+Kx*sx, y:p.y-Ky*h}; // bend sideways & lift
  };

  // ---------- curved grid (paths) ----------
  const mkPath=(pts,stroke,w=1.2)=>SVG.appendChild(E('path',{d:`M ${pts[0].x} ${pts[0].y} `+pts.slice(1).map(p=>`L ${p.x} ${p.y}`).join(' '),fill:'none',stroke,'stroke-width':w}));
  const SPAN=LINES*2+6, RES=80;
  for(let k=-LINES-2;k<=LINES+2;k++){
    const off=add(ORIGIN,sc(g2,k)), a=add(off,sc(g1,-SPAN)), b=add(off,sc(g1,SPAN));
    const pts=[]; for(let t=0;t<=RES;t++){ const u=t/RES; pts.push(W({x:a.x+(b.x-a.x)*u, y:a.y+(b.y-a.y)*u})); }
    mkPath(pts,grid1,1.1);
  }
  for(let k=-LINES-2;k<=LINES+2;k++){
    const off=add(ORIGIN,sc(g1,k)), a=add(off,sc(g2,-SPAN)), b=add(off,sc(g2,SPAN));
    const pts=[]; for(let t=0;t<=RES;t++){ const u=t/RES; pts.push(W({x:a.x+(b.x-a.x)*u, y:a.y+(b.y-a.y)*u})); }
    mkPath(pts,grid2,1.1);
  }

  // ---------- sea level + water quads ----------
  const SEA=-AMP*0.08;
  const cellAboveSea=(i,j)=>{
    const P=[add(ORIGIN,add(sc(g1,i),   sc(g2,j))),
             add(ORIGIN,add(sc(g1,i+1), sc(g2,j))),
             add(ORIGIN,add(sc(g1,i),   sc(g2,j+1))),
             add(ORIGIN,add(sc(g1,i+1), sc(g2,j+1)))];
    return z(P[0].x,P[0].y)>SEA && z(P[1].x,P[1].y)>SEA && z(P[2].x,P[2].y)>SEA && z(P[3].x,P[3].y)>SEA;
  };
  for(let j=-LINES+1;j<LINES-2;j+=2){
    for(let i=-LINES+1;i<LINES-2;i+=2){
      if(!cellAboveSea(i,j)){
        const p0=W(add(ORIGIN,add(sc(g1,i),   sc(g2,j))));
        const p1=W(add(ORIGIN,add(sc(g1,i+1), sc(g2,j))));
        const p2=W(add(ORIGIN,add(sc(g1,i+1), sc(g2,j+1))));
        const p3=W(add(ORIGIN,add(sc(g1,i),   sc(g2,j+1))));
        SVG.appendChild(E('polygon',{points:poly([p0,p1,p2,p3]),fill:waterCol}));
      }
    }
  }

  // ---------- many buildings ----------
  // Selection strategy:
  //  - iterate a land window near center
  //  - probability increases with height above sea (drier → likelier)
  //  - optional spacing: skip immediate neighbors once chosen
  const faces=[]; // global face list for back-to-front paint

  const centerBias=(x)=>{const t=(x+R()*0.25); return Math.max(0,1-Math.abs(t));}; // mild center weight
  const clamp=(x,a,b)=>x<a?a:x>b?b:x;
  const RADIUS=LINES-3;
  const iMin=-RADIUS, iMax=RADIUS-1, jMin=-RADIUS, jMax=RADIUS-1;

  // tiny occupancy to reduce clumping
  const used=new Set(), kkey=(i,j)=>i+'_'+j;

  const dryFactor=(i,j)=>{ // 0..1 based on how far above sea
    const mid=add(ORIGIN,add(sc(g1,i+0.5),sc(g2,j+0.5)));
    const dz= z(mid.x,mid.y)-SEA; return clamp(dz/(AMP*0.9),0,1);
  };

  const wantCell=(i,j)=>{
    if(!cellAboveSea(i,j)) return false;
    const cb = centerBias( (i/(RADIUS)) ) * centerBias( (j/(RADIUS)) );
    const p  = 0.08 + 0.55*dryFactor(i,j) * (0.35+0.65*cb); // base density × dryness × center bias
    return R()<p;
  };

  // iterate in a shuffled ring order so coverage is nice
  const candidates=[];
  for(let j=jMin;j<=jMax;j++) for(let i=iMin;i<=iMax;i++) candidates.push({i,j, w:Math.hypot(i*0.7,j*0.7)});
  candidates.sort(()=>R()-0.5);

  let built=0, MAX_BUILD=140;
  for(const c of candidates){
    if(built>=MAX_BUILD) break;
    const {i,j}=c;
    if(used.has(kkey(i,j))) continue;
    if(!wantCell(i,j)) continue;

    // mark a small neighborhood to avoid immediate touching
    used.add(kkey(i,j)); used.add(kkey(i+1,j)); used.add(kkey(i,j+1)); used.add(kkey(i+1,j+1));

    // lattice nodes -> warp to terrain surface
    const P00=W(add(ORIGIN,add(sc(g1,i),   sc(g2,j))));
    const P10=W(add(ORIGIN,add(sc(g1,i+1), sc(g2,j))));
    const P01=W(add(ORIGIN,add(sc(g1,i),   sc(g2,j+1))));
    const P11=W(add(ORIGIN,add(sc(g1,i+1), sc(g2,j+1))));

    // height scaled by dryness so coastal areas build lower
    const htBase=STEP*(0.9+R()*3.1), Ht= htBase*(0.5+0.8*dryFactor(i,j));
    const up={x:0,y:-1};
    const T00={x:P00.x,y:P00.y+up.y*Ht}, T10={x:P10.x,y:P10.y+up.y*Ht},
              T01={x:P01.x,y:P01.y+up.y*Ht}, T11={x:P11.x,y:P11.y+up.y*Ht};

    // per-building hue nudge for variety
    const hue=(H0+(R()*24-12)|0), Ssat=62+((R()*12)|0);
    const fillL=col(hue,   Ssat,38), fillR=col(hue+8,Ssat,46),
          fillF=col(hue+4, Ssat,34), fillB=col(hue-6,Ssat,30), fillT=col(hue+2,Ssat,72);

    // push all faces into a global list with depth keys (avg bottom y)
    faces.push(
      {k:(P00.y+P01.y)/2, el:['poly',[T00,T01,P01,P00], fillL]}, // left
      {k:(P10.y+P11.y)/2, el:['poly',[T10,T11,P11,P10], fillR]}, // right
      {k:(P00.y+P10.y)/2, el:['poly',[T10,T00,P00,P10], fillF]}, // front
      {k:(P01.y+P11.y)/2, el:['poly',[T11,T01,P01,P11], fillB]}, // back
      {k:(T00.y+T01.y+T10.y+T11.y)/4, el:['poly',[T10,T11,T01,T00], fillT]} // top
    );

    built++;
  }

  // global back-to-front paint
  faces.sort((a,b)=>a.k-b.k);
  for(const f of faces){
    const [kind, pts, fill]=f.el;
    if(kind==='poly') SVG.appendChild(E('polygon',{points:poly(pts),fill}));
  }

  // debug
  SVG.setAttribute('data-buildings',String(built));
  SVG.setAttribute('data-step',String(STEP));
  SVG.setAttribute('data-angles',`${A1.toFixed(1)},${A2.toFixed(1)}`);
})();
