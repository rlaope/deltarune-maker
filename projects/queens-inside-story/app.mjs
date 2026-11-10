import {createGame,step,FPS,DURATION} from './engine.mjs';
import { replayInput } from './replay.mjs';
import {render,loadAssets,assetURL} from './render.mjs';
import {music,cues} from './audio.mjs';

const canvas=document.querySelector('canvas');
const fmt=new URLSearchParams(location.search).get('format')??'wide';
const capture=new URLSearchParams(location.search).has('capture');
const dimensions={wide:[480,270],short:[400,712]};
function size(c,f){[c.width,c.height]=dimensions[f]}
size(canvas,fmt);
await loadAssets();
let state=createGame(), play=false, autoplay=false, muted=false, prior=0, budget=0, score, at=0;
const liveAudio=new Set();
let queenVoice=null;
const held={}, tap={};
const keys={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down',KeyA:'a',KeyB:'b',KeyL:'cancel',Escape:'cancel'};
const loop=()=>requestAnimationFrame(update);
function tick(input,s=state){return step(s,1/FPS,input)}
function setMusic(scene) {
  if(score){score.pause();score=null}
  const track=music.find(m=>m.scene===scene);
  if(track&&!muted){
    score=new Audio(assetURL(track.path));
    score.volume=track.gain;
    score.loop=track.loop===true;
    score.play().catch(()=>{});
  }
}
function sound(){
  for(const e of state.events.slice(at)){
    if(e.type==='transition'||e.type==='win')setMusic(null);
    if(e.type==='battle'||e.type==='bossBurst')setMusic(e.type);
    if(muted)continue;
    for(const q of cues(e)){
      const owner=state;
      setTimeout(()=>{
        if(muted||owner!==state||e.t>state.t)return;
        const queen=q.path==='dr/queen-text.wav';
        if(queen&&(state.line?.text!==e.text||state.line.reveal))return;
        if(queen&&queenVoice)queenVoice.stop();
        const a=new Audio(assetURL(q.path));a.volume=q.gain;a.currentTime=q.start??0;liveAudio.add(a);
        const done=()=>{
          a.pause();liveAudio.delete(a);
          if(queenVoice?.audio===a)queenVoice=null;
        };
        if(queen){
          a.preservesPitch=false;
          a.playbackRate=q.playbackRate;
          queenVoice={audio:a,stop:done};
        }
        a.addEventListener('ended',done,{once:true});a.play().catch(done);
        if(q.limit)setTimeout(done,q.limit*1000);
      },Math.max(0,(q.t-state.t)*1000));
    }
  }
  at=state.events.length;
}
function start(replay=false){
  resetHeld();Object.keys(tap).forEach(k=>delete tap[k]);
  for(const a of liveAudio)a.pause();liveAudio.clear();queenVoice=null;
  state=createGame();play=true;autoplay=replay;budget=0;at=0;setMusic('map');
}
function update(now){
  budget=Math.min(budget+(now-prior)/1000,.1);prior=now;
  while(play&&budget>=1/FPS){
    tick(autoplay?replayInput(state):{...held,...tap,aHeld:!!held.a,bHeld:!!held.b,a:!!tap.a,b:!!tap.b});
    Object.keys(tap).forEach(k=>delete tap[k]);budget-=1/FPS;
    sound();
    if(autoplay&&state.t>=DURATION-1e-4){play=false;setMusic(null);}
  }
  render(canvas,state,fmt);loop();
}
function down(k){
  if(!k)return;
  if(!play)start();
  if(k==='a'||k==='b'||k==='cancel')tap[k]=true;
  if(k!=='cancel')held[k]=true;
}
function up(k){if(k)delete held[k];}
function resetHeld(){Object.keys(held).forEach(up);}
if(capture){
  const renderers=Object.fromEntries(Object.keys(dimensions).map(f=>{
    const c=document.createElement('canvas');size(c,f);return [f,c];
  }));
  let replay=createGame();
  window.capture={
    batch(count,formats=['short','wide']){
      const packets=Object.fromEntries(formats.map(f=>[f,[]]));
      for(let i=0;i<count;i++){
        for(const f of formats){
          const c=renderers[f];render(c,replay,f);
          packets[f].push(c.toDataURL('image/png').split(',')[1]);
        }
        tick(replayInput(replay),replay);
      }
      return packets;
    },
    seek(n){replay=createGame();for(let i=0;i<n;i++)tick(replayInput(replay),replay);},
  };
}else{
  document.addEventListener('keydown',e=>{const k=keys[e.code];if(k){e.preventDefault();if(!e.repeat)down(k);}});
  document.addEventListener('keyup',e=>up(keys[e.code]));
  window.addEventListener('blur',resetHeld);
  document.querySelectorAll('[data-key]').forEach(b=>{
    b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);down(b.dataset.key)};
    b.onpointerup=b.onpointercancel=()=>up(b.dataset.key);
  });
  document.querySelector('[data-start]').onclick=()=>start();
  document.querySelector('[data-replay]').onclick=()=>start(true);
  document.querySelector('[data-mute]').onclick=e=>{
    muted=!muted;if(score)score.muted=muted;if(muted)for(const a of liveAudio)a.pause();
    e.currentTarget.textContent=muted?'Unmute':'Mute';
    if(!muted&&play&&!score)setMusic(state.scene==='battle'?'battle':state.scene==='end'?'bossBurst':'map');
  };
  window.inspectGame=()=>structuredClone(state);
  loop();
}
