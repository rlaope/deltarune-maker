import {BOSS_BURST_AT,visibleLine} from './engine.mjs';
const INK='#080a16', WHITE='#f3f6ef', CYAN='#71e5ed', PINK='#ff7dc7', AMBER='#ffe779';
const I={}, GL={}; let glyphs={}, manorPlate, heartMatte;
export const assetURL=path=>globalThis.QUEEN_ASSETS?.[path]??('./assets/'+path);
const clamp=(v,l=0,h=1)=>Math.max(l,Math.min(h,v));
const px=Math.round;

export async function loadAssets() {
  const root='dr/';
  const names=await (await fetch(assetURL(root+'images.json'))).json();
  glyphs=(await (await fetch(assetURL(root+'font.json'))).json()).glyphs;
  const bis=await (await fetch(assetURL('bis/ui/images.json'))).json();
  const sheets=[...names.filter(n=>n.endsWith('.png')).map(n=>[n.slice(0,-4),root+n]),
                ...bis.filter(n=>n.endsWith('.png')).map(n=>['bis-'+n.slice(0,-4),'bis/ui/'+n])];
  await Promise.all(sheets.map(([key,path])=>new Promise((ok,fail)=>{
    const im=new Image();im.onload=()=>{I[key]=im;ok()};im.onerror=fail;im.src=assetURL(path);
  })));
  manorPlate=buildManorPlate(I.map);
  heartMatte=document.createElement('canvas');
  heartMatte.width=400;heartMatte.height=270;
  const atlas=I.font;
  for(const c of [WHITE,CYAN,PINK,AMBER,'#92a9bb','#182735','#aaffbc','#fc6c82','#060813']){
    const t=document.createElement('canvas');t.width=atlas.width;t.height=atlas.height;
    const q=t.getContext('2d');q.drawImage(atlas,0,0);q.globalCompositeOperation='source-in';q.fillStyle=c;q.fillRect(0,0,t.width,t.height);GL[c]=t;
  }
}
function box(c,x,y,w,h,color){c.fillStyle=color;c.fillRect(px(x),px(y),px(w),px(h));}
function poly(c,pts,color){c.fillStyle=color;c.beginPath();for(let i=0;i<pts.length;i++)c[i?'lineTo':'moveTo'](...pts[i]);c.closePath();c.fill();}
function line(c,x,y,xx,yy,color){c.strokeStyle=color;c.lineWidth=1;c.beginPath();c.moveTo(px(x)+.5,px(y)+.5);c.lineTo(px(xx)+.5,px(yy)+.5);c.stroke();}
function sprite(c,k,x,y,s=1,opts={}){
  const im=I[k];if(!im)return;
  const w=px(im.width*s),h=px(im.height*s);
  c.save();c.globalAlpha=opts.alpha??1;c.translate(px(x),px(y));if(opts.flip)c.scale(-1,1);
  const [ox,oy]=opts.origin??[im.width/2,im.height];
  c.drawImage(im,opts.top?0:-px(ox*s),opts.top?0:-px(oy*s),w,h);c.restore();
}
function frame(k,t,rate=8){
  let len=0;while(I[k+'-'+len])len++;return k+'-'+(len?Math.floor(Math.max(0,t)*rate)%len:0);
}
function width(s,z=1){return [...String(s)].reduce((w,ch)=>w+(glyphs[ch.charCodeAt(0)]?.shift??6)*z,0);}
function text(c,s,x,y,z=1,color=WHITE,align='left'){
  s=String(s);if(align==='center')x-=width(s,z)/2;if(align==='right')x-=width(s,z);
  for(const ch of s){
    const g=glyphs[ch.charCodeAt(0)]??glyphs[63];if(g&&ch!==' ')c.drawImage(GL[color]||I.font,g.x,g.y,g.w,g.h,px(x+g.offset*z),px(y),px(g.w*z),px(g.h*z));x+=(g?.shift??6)*z;
  }
}
function wrapped(s,limit,z){
  const out=[];let row='';
  for(const w of s.split(' ')){const next=row?row+' '+w:w;if(row&&width(next,z)>limit){out.push(row);row=w;}else row=next;}
  if(row)out.push(row);return out;
}
function pixelBox(c,x,y,w,h,fill,border){
  box(c,x+2,y,w-4,h,border);box(c,x,y+2,w,h-4,border);
  box(c,x+2,y+2,w-4,h-4,fill);
}
function shadow(c,x,y,w=24){poly(c,[[x-w/2,y],[x-w*.33,y-3],[x+w*.33,y-3],[x+w/2,y],[x+w*.33,y+3],[x-w*.33,y+3]],'#101025');}
function button(c,id,x,y,pressed=false,z=1){
  const main=id==='A'?CYAN:PINK, deep=id==='A'?'#246b86':'#9e386d';
  const n=24*z,dy=pressed?3*z:0;
  pixelBox(c,x,y+3*z,n,n,deep,'#101020');pixelBox(c,x,y+dy,n,n,pressed?main:'#161e31',main);
  text(c,id,x+n/2,y+4*z+dy,1.2*z,pressed?'#182735':WHITE,'center');
}
function dialogue(c,l,x,y,w,scale=1.25){
  const portraitKey=(l.speaker??'queen')+'-face',portrait=I[portraitKey];
  const body=l.text.replace(/[’‘]/g,"'").replace(/[“”]/g,'"');
  const large=scale>=1.5, textX=large?83:62, pitch=large?24:18;
  const lines=wrapped(body,w-textX-24,scale);
  const h=Math.max(large?88:62,22+lines.length*pitch);
  const border=large?4:3;
  box(c,x,y,w,h,WHITE);
  box(c,x+border,y+border,w-2*border,h-2*border,'#000000');
  if(portrait){
    const max=large?64:48;
    const z=Math.min(large?2.15:1.7,max/portrait.width,max/portrait.height);
    sprite(c,portraitKey,x+(large?41:35),y+h/2+portrait.height*z/2,z);
  }
  let remaining=l.reveal?body.length+lines.length+1
    :l.speaker==='queen'?visibleLine(l).length:Math.floor((l.age??2)*32)+1;
  for(let i=0;i<lines.length;i++){
    const row=lines[i],take=row.slice(0,Math.max(0,remaining));remaining-=row.length+1;
    if(take)text(c,(i===0?'* ':'  ')+take,x+textX,y+(large?12:9)+i*pitch,scale);
  }
  if(remaining>0&&Math.floor((l.age??0)*4)%2===0){
    poly(c,[[x+w-17,y+h-13],[x+w-9,y+h-13],[x+w-13,y+h-8]],WHITE);
  }
}
function buildManorPlate(image){
  const plate=document.createElement('canvas');
  plate.width=640;plate.height=270;
  const c=plate.getContext('2d',{willReadFrequently:true});
  c.drawImage(image,0,0);
  const pxData=c.getImageData(0,0,640,270),rgba=pxData.data;
  for(let y=80;y<257;y++)for(let x=0;x<640;x++){
    const i=(y*640+x)*4,r=rgba[i],g=rgba[i+1],b=rgba[i+2];
    if(r>g*1.55&&r>b*1.3){
      rgba[i]=57+(r-175)*.33;
      rgba[i+1]=41+(g-41)*.47;
      rgba[i+2]=75+(b-80)*.53;
    }
  }
  c.putImageData(pxData,0,0);
  for(let y=83;y<254;y+=25){
    line(c,0,y,640,y,'#31263f');
    for(let x=(y%2)*24;x<640;x+=48)line(c,x,y,x,y+24,'#342741');
  }
  // Continuous runner follows the turn in the actual playable route.
  const runner=[[0,181],[199,181],[199,119],[423,119],[423,163],[242,163],[242,225],[0,225]];
  poly(c,runner,'#62466a');
  poly(c,[[0,185],[203,185],[203,123],[419,123],[419,159],[238,159],[238,221],[0,221]],'#4b3559');
  for(let x=14;x<195;x+=18){
    line(c,x,188,x+9,188,'#78628c');line(c,x,218,x+9,218,'#78628c');
  }
  for(let x=218;x<415;x+=17){
    line(c,x,127,x+8,127,'#6e658f');line(c,x,155,x+8,155,'#6e658f');
  }
  for(const [x,y] of [[32,202],[95,202],[190,202],[222,184],[222,145],[280,141],[344,141],[400,141]]){
    poly(c,[[x-7,y],[x,y-4],[x+7,y],[x,y+4]],'#625581');
    line(c,x-3,y,x+3,y,'#8a75a0');
  }
  c.imageSmoothingEnabled=false;
  return plate;
}
function manorDecor(c,s){
  const m=s.map;
  for(const [x,y] of [[112,114],[311,224],[578,223]]){
    shadow(c,x,y+2,61);
    box(c,x-27,y-9,55,10,'#1a172d');box(c,x-23,y-13,47,4,'#745b87');
    box(c,x-21,y-6,3,9,'#22182c');box(c,x+19,y-6,3,9,'#22182c');
    sprite(c,'mansion-platter-0',x-6,y-12,.67);
    sprite(c,frame('mansion-candle',s.t,3),x+17,y-12,.66);
  }
  for(const x of [208,423,581]){
    sprite(c,'mansion-bookcase-0',x,108,.68);
  }
  for(const x of [92,380,550]){
    c.save();c.globalAlpha=.23;
    poly(c,[[x-13,63],[x+13,63],[x+52,124],[x+22,139],[x-25,139],[x-52,124]],x===380?'#567f9d':'#8f6e9d');
    c.restore();
    sprite(c,'mansion-chandelier-0',x,75,.40);
  }
  box(c,306,99,68,14,'#212139');box(c,307,99,67,2,'#645e83');
  sprite(c,'mansion-computer-0',340,101,.42);
  if(m.switch){
    const {x,y,on}=m.switch;
    box(c,x-14,y-8,28,12,'#211a31');box(c,x-12,y-6,24,8,on?'#4b9ea2':'#4e3667');
    line(c,x-8,y-1,x+8,y-1,on?CYAN:'#9174a5');
    if(on){
      for(let n=0;n<7;n++)box(c,x+18+n*15,y-6,5,2,n<=Math.floor((s.t*9)%9)?CYAN:'#586481');
    }
  }
}
function fieldReward(c,s){
  const {block,pickup}=s.map;
  if(!block)return;
  const y=block.y-43;
  const kick=block.bump>0?Math.sin(Math.PI*clamp(block.bump/.25))*10:0;
  shadow(c,block.x,block.y-2,18);
  const bob=block.used?0:Math.sin(s.t*7)*1.4;
  sprite(c,block.used&&block.bump===0?'bis-field-spent':'bis-field-question',block.x,y-kick-bob,1.09);
  if(pickup){
    const rise=1-(1-clamp(pickup.age/.24))**2;
    sprite(c,'bis-item-mushroom',block.x,y-22-rise*14,1.08,{alpha:clamp((.72-pickup.age)/.18)});
  }
}
function mapCamera(m,left){return px(clamp(m.x-164,-Math.min(9,left),240));}
function room(c,s,left){
  const m=s.map,cam=mapCamera(m,left);
  c.save();c.translate(-cam,0);
  c.drawImage(manorPlate,0,0);
  manorDecor(c,s);
  // Battery socket and light strips are added to the original mansion plate.
  const qx=m.queenX,qy=m.queenY;
  box(c,qx-22,qy-62,44,44,'#101526');box(c,qx-18,qy-58,36,39,'#276080');
  box(c,qx-14,qy-55,28,36,'#101e39');box(c,qx-13,qy-55,26,2,'#4d9bb6');
  const active=s.scene!=='map'&&s.scene!=='end';
  const powered=m.switch?.on||active;
  box(c,qx-15,qy-61,30,2,active?'#ff92bc':powered?'#83e6e4':'#504164');
  for(let i=0;i<4;i++)box(c,qx-12+7*i,qy-36,4,5+2*i,active?'#d15c83':powered?'#75d3ab':'#453c60');
  const actors=[
    {k:'queen',x:qx,y:qy,face:'left',move:false,lift:0},
    {k:'kris',x:m.x,y:m.y,face:m.face,move:m.moving,lift:m.jumps?.[0]??0,age:m.jumpTime?.[0]??0},
    {k:'susie',x:m.susieX??m.x-30,y:m.susieY??m.y,face:m.susieFace??m.face,move:m.susieMoving??m.moving,lift:m.jumps?.[1]??0,age:m.jumpTime?.[1]??0},
  ].sort((a,b)=>a.y-b.y);
  for(const a of actors){
    shadow(c,a.x,a.y,a.k==='queen'?34:23);
    const base=a.k+'-'+(a.face??'right');
    let k=a.k==='queen'?'queen-map-0':a.move?frame(base,s.t,9):base+'-0';
    if(a.lift>0&&a.k==='kris')k=frame('kris-field-jump',a.age,8);
    if(a.lift>0&&a.k==='susie'){
      const jumpDirection=a.face==='up'||a.face==='down'?a.face:'jump';
      k='susie-field-'+jumpDirection+'-0';
    }
    sprite(c,k,a.x,a.y-a.lift,1.14,{flip:k.includes('field-jump')&&a.face==='left'});
  }
  fieldReward(c,s);
  if(s.scene==='map'&&Math.hypot(m.x-qx,m.y-qy)<86){
    const y=qy-68+Math.floor(Math.sin(s.t*7)*2);dsButton(c,0,qx,y,false,1.1);
  }
  c.restore();
}
function battleBack(c,t,hot){
  box(c,0,0,400,270,'#081323');
  // The floor is shared by both lanes. Horizontal lines and converging tiles establish depth.
  box(c,0,0,400,110,'#15233c');
  box(c,0,0,400,22,'#0b1527');
  box(c,0,21,400,2,'#35435a');
  box(c,0,24,400,1,'#1c2a40');
  for(let x=-12;x<412;x+=42){
    box(c,x,25,2,87,'#314764');box(c,x+3,28,35,70,'#10203a');
    box(c,x+10,37,21,47,'#192f4b');box(c,x+12,39,17,38,'#132541');
    box(c,x+12,72,17,2,hot?'#b34672':'#417e9e');
  }
  sprite(c,'mansion-seal-0',200,99,.62,{alpha:.27});
  for(const x of [56,344]){
    sprite(c,frame('mansion-candle',t,5),x,96,1,{alpha:.66});
  }
  box(c,0,98,400,16,'#181729');box(c,0,98,400,2,hot?'#ad477e':'#367e9f');
  box(c,0,111,400,2,'#48435c');box(c,0,113,400,157,'#25283f');
  for(let j=0;j<7;j++){
    const u=j/7,v=(j+1)/7,y=113+u*u*157,yy=113+v*v*157,span=147+u*105,next=147+v*105;
    for(let k=-1;k<9;k++){
      const a=(k-4)/4,b=(k-3)/4;
      poly(c,[[200+a*span,y],[200+b*span,y],[200+b*next,yy],[200+a*next,yy]],(j+k)%2?'#2d3850':'#263047');
    }
    box(c,0,y,400,1,'#19263c');
  }
  for(let j=0;j<2;j++){
    const y=j===0?153:213;
    box(c,34,y+6,315,2,hot?'#7a3c65':'#395970');
    for(let x=42;x<351;x+=16)box(c,x,y+6,5,2,hot?'#b25088':'#5c86a0');
  }
  for(let k=0;k<9;k++){
    const x=18+k*46,y=103;if(((Math.floor(t*9)+k)%9)<3)box(c,x,y,16,2,hot?'#f272ab':'#79cfda');
  }
  poly(c,[[275,151],[302,141],[345,141],[367,150],[359,162],[299,163]],'#313e56');
  box(c,297,163,62,2,hot?'#b2548a':'#598da9');
}
const heroes=['kris','susie'];
function goldDigits(c,value,x,y,z=1.15,kind='hp'){
  const keys=String(value).split('').map(d=>'bis-'+kind+'-'+d);
  if(keys.every(k=>I[k])){
    const widths=keys.map(k=>Math.round(I[k].width*z)),w=widths.reduce((a,b)=>a+b,0);
    let xx=x-w/2;
    keys.forEach((k,i)=>{sprite(c,k,xx,y,z,{top:true});xx+=widths[i]-1;});
  }else{
    text(c,value,x+1,y+2,z*1.48,'#060813','center');
    text(c,value,x,y,z*1.48,AMBER,'center');
  }
}
function dsButton(c,i,x,y,on=false,z=1){
  const k='bis-'+(i?'b':'a');
  if(I[k])sprite(c,k,x,y+(on?2:0),z);
  else button(c,i?'B':'A',x-11*z,y-22*z,on,z);
}
function cap(c,x,y,i,value,hurt){
  const w=91,h=31,rim='#231929';
  const shade=i?['#981d73','#c33d98','#e761b3']:['#1f6f9b','#238fba','#3bb9d0'];
  for(let row=0;row<h;row++){
    const ry=1-row/(h-1),wing=Math.sqrt(1-ry*ry);
    const l=x+Math.round((w/2)*(1-wing)),ww=w-2*(l-x);
    if(ww<1)continue;
    box(c,l,y+row,ww,1,rim);
    if(row>=3){
      const ro=1-(row-3)/(h-3),w2=Math.sqrt(1-ro*ro),l2=x+3+Math.round((w/2-3)*(1-w2)),n=w-2*(l2-x);
      if(n>0)box(c,l2,y+row,n,1,hurt&&row<13?'#f78994':shade[row<9?0:1]);
      if(row>8&&row%5<2)for(let dx=l2+3+(Math.floor(row/5)%2)*3;dx<l2+n-4;dx+=6)box(c,dx,y+row,2,1,shade[2]);
    }
  }
  if(I['bis-heart'])sprite(c,'bis-heart',x+28,y+25,1.04);
  else poly(c,[[x+20,y+14],[x+24,y+12],[x+28,y+15],[x+32,y+12],[x+36,y+15],[x+35,y+20],[x+28,y+26],[x+21,y+20]],'#f70065');
  goldDigits(c,value,x+51,y+6,1.24);
}
function dsOutline(c,s,x,y,z=1.05){
  for(const [dx,dy] of [[-1,0],[1,0],[0,-1],[0,1],[0,2]])text(c,s,x+dx,y+dy,z,'#060813','center');
  text(c,s,x,y,z,WHITE,'center');
}
function block(c,name,x,y,z,alpha=1){
  const k='bis-'+name;
  if(I[k])sprite(c,k,x,y,z,{alpha});
  else {
    c.save();c.globalAlpha=alpha;
    pixelBox(c,x-14*z,y-23*z,28*z,23*z,'#b36c1e',AMBER);
    text(c,name==='jump'?'J':'H',x,y-19*z,1.1*z,WHITE,'center');
    c.restore();
  }
}
const COMMAND_ORDER=['jump','hammer','item','flee'];
const COMMAND_LABEL={jump:'Jump',hammer:'Hammer',item:'Item',flee:'Flee'};
function actionCorner(c,pressed,armed=[],offset=0){
  for(const i of [1,0]){
    const id=i?'b':'a',down=pressed[i]>0;
    const x=offset+(i?25:52),y=i?59:44;
    const alpha=armed.length&&!armed.includes(i)?.65:1;
    sprite(c,'bis-action-arrow',x,y-17+(down?2:0),.59,{alpha});
    const key='bis-'+id+(down?'-press':'');
    sprite(c,key,x,y+(down?2:0),1,{alpha});
  }
}
function commandPlaque(c,label,right,left){
  const w=112,x=right?288-left:left;
  pixelBox(c,x,-3,w,24,'#ffdf72','#4c282e');
  box(c,x+5,17,w-10,2,'#e4a744');
  text(c,label,x+w/2,3,1.04,'#182735','center');
}
function menu(c,b,s,left){
  const turn=b.turn,p=b.players[turn],cmd=b.command,t=b.phaseClock;
  const baseX=Math.max(p.x+2,left+58);
  const baseY=p.y-48+Math.round(Math.sin(s.t*6)*2);
  if(b.phase==='command'){
    const index=COMMAND_ORDER.indexOf(cmd);
    const last=s.events.findLast(e=>e.type==='select'&&e.turn===turn&&e.direction);
    const age=last&&last.t>=s.t-t-.02?clamp((s.t-last.t)/.25):1;
    const scroll=age===1?0:last.direction*(1-(age*age*(3-2*age)));
    const slots=COMMAND_ORDER.map((command,i)=>{
      const angle=(i-index+scroll)*Math.PI/2;
      const depth=(1-Math.cos(angle))/2;
      return {command,depth,x:baseX+43*Math.sin(angle)+8*depth,y:baseY-42*depth};
    }).sort((a,b)=>b.depth-a.depth);
    for(const slot of slots){
      block(c,slot.command,slot.x,slot.y,1.27-.53*slot.depth,1-.39*slot.depth);
    }
    commandPlaque(c,COMMAND_LABEL[cmd],true,left);
    dsButton(c,turn,baseX-23,baseY+16,b.press[turn]>0,.89);
    return;
  }
  if(b.phase==='bump'){
    const hop=b.bump.elapsed/b.bump.duration;
    block(c,cmd,baseX,baseY-(hop>.5?Math.sin((hop-.5)*Math.PI)*25:0),1.25,hop>.68?clamp((1-hop)/.32):1);
    return;
  }
  if(b.phase==='target'){
    const q=b.queen,j=3*Math.sin(t*12);
    sprite(c,'bis-cursor',q.x,q.y-80+j,1.13);
    commandPlaque(c,'Queen',false,left);
    commandPlaque(c,COMMAND_LABEL[cmd],true,left);
    pixelBox(c,left,22,76,15,'#30232e','#130e1c');
    text(c,'L  CANCEL',left+10,21,.81);
    dsButton(c,turn,q.x+23,q.y-59,b.press[turn]>0,.88);
  }
}
function choicePanel(c,b,left){
  const x=199-left,y=178,w=184,h=56;
  const item=b.phase==='item';
  pixelBox(c,x,y,w,h,item?'#3e2b64':'#fbebbd','#5a3041');
  box(c,x+3,y+4,w-6,17,'#e4af60');
  const title=b.phase==='item'?'Item':b.phase==='flee'?'Flee':'Queen';
  text(c,title,x+12,y+6,1,'#182735');
  if(b.phase==='item'){
    sprite(c,'bis-item-mushroom',x+20,y+45,1.12);
    text(c,b.items?'Mushroom':'No items left',x+35,y+24,.98,WHITE);
    if(b.items){
      goldDigits(c,b.items,x+w-22,y+27,.75);
      text(c,'Use on '+(b.itemTarget?'Susie':'Kris'),x+35,y+39,.88,WHITE);
    }
  }else{
    const body=b.phase==='flee'?'Run from this fight?':b.notice;
    wrapped(body,w-18,.91).slice(0,2).forEach((row,i)=>text(c,row,x+9,y+24+i*12,.91,'#182735'));
  }
  if(b.phase!=='notice')dsButton(c,b.turn,x+w-14,y+17,b.press[b.turn]>0,.87);
}
function axePose(action){
  const ready={name:'susie-axe-ready-0',origin:[39,68]};
  if(action.pose==='approach'){
    if(action.elapsed>.60)return ready;
    return {name:frame('susie-right',action.elapsed,12)};
  }
  if(action.pose==='charge'){
    const held=action.elapsed-action.chargeStart;
    if(held<.065)return ready;
    const index=action.charged?3:4;
    return {name:'susie-axe-up-'+index,origin:[36,73]};
  }
  if(action.pose==='swing'){
    const progress=clamp((action.elapsed-action.swingStart)/(action.duration-action.swingStart));
    if(progress<.23)return {name:'susie-axe-up-4',origin:[36,73]};
    return {name:progress<.70?'susie-axe-0':'susie-axe-1',origin:[42,68]};
  }
  if(action.pose==='follow'){
    return {name:action.elapsed<.067?'susie-axe-1':'susie-axe-2',origin:[42,68]};
  }
  return {name:frame('susie-right',action.elapsed,12)};
}
function weaponPose(b,i){
  const action=b.stomp;
  if(action?.target===i&&action.weapon==='axe'&&action.kind==='hammer')return axePose(action);
  const strike=b.fx.findLast(f=>f.target===i&&f.weapon&&f.age<.24&&['impact','excellent'].includes(f.type));
  if(strike){
    const name=strike.weapon==='axe'?'susie-axe':'kris-sword';
    const frameNumber=Math.min(2,Math.floor(strike.age*15));
    return {name:name+'-'+frameNumber,origin:strike.weapon==='axe'?[42,68]:[12,42]};
  }
  if(action?.target!==i||action.stage==='return')return;
  if(action.weapon==='sword'&&(action.pose==='strike'||action.stage==='first'&&action.elapsed>.44)){
    return {name:'kris-sword-ready-0',origin:[12,42]};
  }
}
function weaponImpact(c,f){
  if(!f.weapon||f.age>=.17)return;
  const index=Math.min(4,Math.floor(f.age*30));
  sprite(c,'queen-defeat-impact-'+index,f.x,f.y,f.weapon==='axe'?1.35:1.12,
    {origin:[12,12]});
}
function impactGrade(c,b){
  const f=[...b.fx].reverse().find(f=>f.type==='impact'||f.type==='excellent');
  if(!f)return;
  const t=f.age;
  if(t<.56){
    const x=f.x+19+Math.round(t*10),y=f.y-19-Math.round(t*18);
    c.save();c.globalAlpha=clamp((.56-t)*6);
    goldDigits(c,f.damage,x,y,1.08,'damage');c.restore();
  }
  const grade=f.grade?.replace('!','').toLowerCase();
  if(grade&&t<.63){
    const x=f.x-36,y=Math.max(31,f.y-37-Math.round(t*16));
    const z=1.28+Math.sin(Math.min(1,t/.19)*Math.PI)*.23;
    c.save();c.globalAlpha=clamp((.64-t)*7);
    if(I['bis-'+grade])sprite(c,'bis-'+grade,x,y,z,{alpha:c.globalAlpha});
    else dsOutline(c,f.grade,x,y-10,1.44);
    c.restore();
  }
}
function particle(c,f){
  const time=f.time??.5, kind=f.type;
  if(!['hit','impact','graze','excellent','muzzle','dust'].includes(kind))return;
  const a=clamp(time*2,0,1),radius=4+(f.age??.1)*37;
  c.save();c.globalAlpha=a;
  for(let i=0;i<(['graze','dust'].includes(kind)?5:11);i++){
    const angle=i*2.4, x=f.x+Math.cos(angle)*radius,y=f.y-8+Math.sin(angle)*radius*.66;
    box(c,x,y,2+(i%3===0?2:0),2,i%2===0?WHITE:(kind==='hit'?'#fc6c82':AMBER));
  }
  c.restore();
}
function victoryEffect(c,queen,elapsed){
  const frame=Math.floor(elapsed*30+1e-5)+2;
  const sheet=I['bis-boss-defeat-'+Math.floor(frame/16)];
  if(!sheet)return;
  const w=256,h=192,scale=1.84;
  const col=frame%4,row=Math.floor(frame%16/4);
  c.drawImage(sheet,col*w,row*h,w,h,px(queen.x-187*scale),px(queen.y-48-104*scale),px(w*scale),px(h*scale));
}
function combat(c,s,left=0){
  const b=s.battle, hot=b.wave>=1;
  battleBack(c,s.t,hot);
  const tel=Array.isArray(b.telegraphs)?b.telegraphs:b.telegraph?[b.telegraph]:[];
  const phase=b.phase, won=phase==='victory';
  const queen=b.queen, qhurt=(queen.hurt??0)>0, muzzle=(b.fx??[]).some(f=>f.type==='muzzle'&&f.age<.16);
  let qk=qhurt?'queen-hurt-1':tel.length?'queen-tell-0':muzzle?'queen-chair-2':frame('queen-idle',s.t,7);
  if(!I[qk])qk='queen-map-0';
  if(won){
    const clock=b.phaseClock,burst=clock-BOSS_BURST_AT;
    if(burst<.12){
      shadow(c,queen.x,queen.y,58);
      sprite(c,frame('queen-idle',s.t,7),queen.x,queen.y+3,1.02);
    }
    if(burst>1.32){
      const slide=clamp((burst-1.32)/.24);
      const doorScale=.46,door=I['mansion-door-0'];
      const x=Math.min(queen.x+35,396-left-door.width*doorScale/2),foot=queen.y-35;
      sprite(c,'mansion-door-0',x,foot,doorScale,{alpha:slide});
      const lintel=foot-35;
      box(c,x-7*slide,lintel,14*slide,35,'#090d1d');
      box(c,x-9,lintel-3,18,2,'#aaffbc');
      sprite(c,'queen-map-0',queen.x-22*slide,queen.y+2,1.1,{alpha:slide});
    }
  }else{
    shadow(c,queen.x,queen.y,58);
    const shake=qhurt?Math.round(Math.sin(s.t*83)*5):0;
    sprite(c,qk,queen.x+shake,queen.y+3+Math.round(Math.sin(s.t*8)*1.8),1.02);
  }
  for(const aim of tel){
    const p=b.players[aim.target];if(!p)continue;
    const t=aim.remaining;
    for(let x=px(p.x)-14;x<queen.x-17;x+=13)box(c,x,p.y+4,3,1,t<.18?'#f3c874':'#617788');
  }
  const order=[0,1].sort((i,j)=>b.players[i].y-b.players[j].y);
  for(const i of order){
    const p=b.players[i];
    const z=b.jumps[i],k=heroes[i],hurt=p.hurt>0;
    shadow(c,p.x,p.y,28-Math.min(z/6,12));
    const airtime=b.stomp?.target===i?b.stomp.elapsed:b.jumpTime?.[i]??0;
    const weapon=weaponPose(b,i);
    const gait=p.step?frame(k+'-right',p.step.age+.09,12):frame(k+'-idle',s.t,9);
    const name=weapon&&I[weapon.name]?weapon.name:won&&b.phaseClock>BOSS_BURST_AT+.16?frame(k+'-win',b.phaseClock-BOSS_BURST_AT-.16,10):hurt&&I[k+'-hurt-0']?k+'-hurt-0':z>2?frame(k+'-jump',airtime,8):gait;
    const lift=z-Math.max(0,z-60)*.48;
    const shake=hurt?Math.floor(p.hurt*13):0;
    const castX=p.x-shake;
    sprite(c,name,castX,p.y-lift,1.22,{flip:p.face==='left',origin:weapon?.name===name?weapon.origin:undefined});
    if(b.stomp?.target===i&&b.stomp.pose==='charge'&&b.stomp.charged){
      const x=castX+7,y=p.y-63;
      poly(c,[[x-6,y],[x-1,y-2],[x,y-8],[x+1,y-2],[x+7,y],[x+1,y+2],[x,y+7],[x-1,y+2]],AMBER);
    }
  }
  for(const f of b.shots??[]){
    const y=f.y-(f.z??0);
    shadow(c,f.x,f.y+3,17);
    if(f.kind==='laser'){
      const x=f.x,h=hot?'#fa6fa9':'#64e8ff',dark=hot?'#ae396d':'#217fbb';
      poly(c,[[x-12,y-5],[x-3,y-11],[x+23,y-11],[x+15,y-6],[x+32,y-6],[x+21,y],[x-3,y]],dark);
      poly(c,[[x-12,y-5],[x-3,y-9],[x+16,y-9],[x+11,y-6],[x+24,y-6],[x+17,y-3],[x-3,y-3]],h);
      box(c,x-6,y-6,19,2,WHITE);
    }else{
      const wobble=Math.round(Math.sin(s.t*39)*2);
      box(c,f.x-8,y-16+wobble,17,13,'#14162c');box(c,f.x-7,y-15+wobble,15,11,'#aaffbc');box(c,f.x-4,y-13+wobble,8,7,'#366450');
      box(c,f.x-1,y-11+wobble,4,3,WHITE);box(c,f.x+7,y-12+wobble,4,6,AMBER);
    }
  }
  for(const f of b.fx){
    if(f.type==='impact'||f.type==='excellent')weaponImpact(c,f);
    else particle(c,f);
  }
  if(['command','bump','target'].includes(phase))menu(c,b,s,left);
  if(['item','flee','notice'].includes(phase))choicePanel(c,b,left);
  if(phase==='dodge')actionCorner(c,b.press,tel.map(aim=>aim.target),left);
  if(phase==='stomp'){
    const e=b.stomp;
    const p=b.players[e.target];
    if(e.kind==='hammer'&&e.pose==='charge'){
      dsButton(c,e.target,p.x-24,p.y-55,b.held[e.target],1.0);
    }else if(e.kind==='jump'&&e.stage!=='return'&&e.elapsed>e.duration-.18){
      dsButton(c,e.target,p.x+26,Math.max(38,p.y-b.jumps[e.target]-12),b.press[e.target]>0,1.05);
    }
  }
  if(won&&s.scene==='battle')victoryEffect(c,queen,b.phaseClock);
  impactGrade(c,b);
  for(const f of b.fx.filter(f=>f.type==='hit')){
    if(f.age>.6)continue;
    c.save();c.globalAlpha=clamp((.64-f.age)*6);goldDigits(c,f.damage,f.x+6,f.y-51-f.age*28,1.06,'damage');c.restore();
  }
  cap(c,left-7,240,1,b.hp[1],b.players[1].hurt>0);
  cap(c,left+65,240,0,b.hp[0],b.players[0].hurt>0);
}
function heartEntry(c,s,left){
  const p=clamp(s.clock/2.13),into=p>=.54,cx=200,cy=135;
  if(into)combat(c,s,left);
  const fall=clamp(p/.48),rise=clamp((p-.59)/.41);
  const aperture=into?5+1050*rise*rise:5+1045*(1-fall)**2;
  const matte=heartMatte.getContext('2d'),heart=I['soul-0'];
  matte.imageSmoothingEnabled=false;
  matte.fillStyle='#000000';
  matte.fillRect(0,0,400,270);
  matte.globalCompositeOperation='destination-out';
  matte.drawImage(heart,cx-aperture/2,cy-aperture/2,aperture,aperture);
  matte.globalCompositeOperation='source-over';
  c.drawImage(heartMatte,0,0);
  if(p<.58){
    const q=clamp(p/.48);
    const cam=mapCamera(s.map,left),fromX=s.map.x-cam,fromY=s.map.y-21;
    const speed=q*q, size=20*(1-speed)+4;
    for(let j=3;j>=0;j--){
      const u=Math.max(0,speed-j*.105),x=fromX+(cx-fromX)*u,y=fromY+(cy-fromY)*u;
      sprite(c,'soul-0',x,y,(size+2*j)/heart.width,{origin:[7.5,7.5],alpha:j?.19-j*.03:1});
    }
  }
}
function stage(c,s,dialog=true,left=0){
  c.save();c.beginPath();c.rect(left,0,400-2*left,270);c.clip();
  if(s.scene==='map'||s.scene==='dialogue'||s.scene==='transition'){
    room(c,s,left);
    if(s.scene==='map'){
      actionCorner(c,s.map.press,[],322-left);
      box(c,left+11,8,128,23,'#0c1727');box(c,left+11,30,128,1,'#5687a2');
      text(c,'QUEEN\'S MANSION',left+17,12,1,'#92a9bb');
      if(s.map.pickup){
        c.save();c.globalAlpha=clamp((.72-s.map.pickup.age)/.18);
        pixelBox(c,150,230,100,24,'#302d48','#66627b');
        dsOutline(c,'Mushroom',200,236,1.12);
        c.restore();
      }
    }
    if(s.scene==='transition')heartEntry(c,s,left);
    if(dialog&&s.line)dialogue(c,s.line,12,190,376,1.18);
  }else{
    combat(c,s,left);
    if(s.scene==='end'&&s.line&&dialog)dialogue(c,s.line,12,166,376,1.18);
  }
  c.restore();
}
function shortShell(c,s){
  box(c,0,0,400,712,'#000000');
  if(I['collab-deltarune']&&I['collab-bis']){
    const dr=I['collab-deltarune'],bis=I['collab-bis'];
    const drScale=Math.min(151/dr.width,50/dr.height),bisScale=Math.min(156/bis.width,57/bis.height);
    const center=105;
    sprite(c,'collab-deltarune',104,center+dr.height*drScale/2,drScale);
    sprite(c,'collab-bis',296,center+bis.height*bisScale/2,bisScale);
    line(c,191,96,209,114,WHITE);line(c,209,96,191,114,WHITE);
    line(c,192,96,210,114,WHITE);line(c,208,96,190,114,WHITE);
  }
  const y=154,zoom=1.2, left=(400-400/zoom)/2;
  box(c,0,y-2,400,2,'#303047');box(c,0,y+270*zoom,400,2,'#303047');
  c.save();c.translate(-left*zoom,y);c.scale(zoom,zoom);stage(c,s,false,left);c.restore();
  if(s.line)dialogue(c,s.line,4,498,392,1.64);
}
export function render(canvas,state,format='wide'){
  const c=canvas.getContext('2d');c.imageSmoothingEnabled=false;
  if(format==='short')shortShell(c,state);
  else{
    box(c,0,0,480,270,'#090e19');
    box(c,37,0,2,270,'#2b455d');box(c,441,0,2,270,'#2b455d');
    c.save();c.translate(40,0);stage(c,state);c.restore();
  }
}
