import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {createReadStream, mkdirSync, statSync, writeFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {resolve,extname,join,sep} from 'node:path';
import {assetRoot} from './asset-root.mjs';
import {createGame,step,FPS,DURATION} from './engine.mjs';
import { replayInput } from './replay.mjs';
import {cues,music} from './audio.mjs';

const here=import.meta.dirname;
const require=createRequire(import.meta.url);
const mime={'.html':'text/html','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.wav':'audio/wav','.mp3':'audio/mpeg'};
export function server(){
  return createServer((req,res)=>{
    const request=new URL(req.url,'http://127.0.0.1').pathname;
    let pathname;
    try { pathname=decodeURIComponent(request); }
    catch { res.writeHead(400).end(); return; }
    const isAsset=pathname.startsWith('/assets/');
    const root=isAsset?assetRoot:here;
    const name=isAsset?pathname.slice('/assets/'.length):pathname==='/'?'index.html':'.'+pathname;
    const path=resolve(root,name);
    if(!path.startsWith(root+sep)||!statSync(path,{throwIfNoEntry:false})?.isFile()){
      res.writeHead(404).end();return;
    }
    res.writeHead(200,{'content-type':mime[extname(path)]??'application/octet-stream'});
    createReadStream(path).pipe(res);
  });
}
const modes={short:{w:2160,h:3840}};
function encoder(f){
  const {w,h}=modes[f];
  const params=['-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','pipe:0',
      '-vf',`scale=${w}:${h}:flags=neighbor:in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p`,
      '-an','-c:v','libx264','-preset','veryfast','-crf','15','-threads','7',
      '-color_range','tv','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
      '-movflags','+faststart',`out/${f}-picture.mp4`];
  const p=spawn('ffmpeg',params,{cwd:here,stdio:['pipe','inherit','inherit']});
  return {p,result:once(p,'exit')};
}
async function push(p,data){
  const b=Buffer.concat(data.map(x=>Buffer.from(x,'base64')));
  if(!p.stdin.write(b))await once(p.stdin,'drain');
}
const command=process.argv[2];
if(command==='events'){
  const game=createGame();for(let i=0;i<FPS*DURATION;i++)step(game,1/FPS,replayInput(game));
  const times=Object.fromEntries(['transition','battle','win','bossBurst'].map(k=>[k,game.events.find(e=>e.type===k).t]));
  mkdirSync(join(here,'out'),{recursive:true});
  writeFileSync(join(here,'out/events.json'),JSON.stringify({duration:DURATION,times,music,cues:game.events.flatMap(cues),events:game.events},null,2)+'\n');
}else if(command==='serve'){
  server().listen(Number(process.argv[3])||8623,'127.0.0.1',()=>console.log('http://127.0.0.1:'+ (Number(process.argv[3])||8623)));
}else{
  const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  const web=server().listen(0,'127.0.0.1');await once(web,'listening');
  let browser;
  const enc={};
  try{
    browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM,args:['--mute-audio']});
    const page=await browser.newPage();
    page.on('pageerror',e=>console.error(e));
    await page.goto(`http://127.0.0.1:${web.address().port}/?capture`);
    await page.waitForFunction(()=>window.capture!==undefined,{},{timeout:12000});
    if(command==='stills'){
      for(const t of [0,1.26,1.30,1.42,1.5,1.89,2.12,2.96,4.25,5.70,8.9,10.8,12.6,13.9,15.0,17.4,18.65,18.9,28.83,28.95,29.09,29.25,30.66,32.47,33.83,33.95,34.12,36.8,37.4,37.63,37.69,37.75,37.86,37.98,38.15,47.1,53.95,54.22,54.54,55.30,55.63,55.78,55.9,56.1,56.6,57.2,57.9,59.1]){
        const frames=await page.evaluate(({t,fps})=>{window.capture.seek(Math.round(t*fps));return window.capture.batch(1,['short']);},{t,fps:FPS});
        for(const f of Object.keys(frames))writeFileSync(join(here,`qa/${f}-${t}.png`),Buffer.from(frames[f][0],'base64'));
      }
    }else{
      const formats=command in modes?[command]:Object.keys(modes);
      mkdirSync(join(here,'out'),{recursive:true});
      for(const f of formats)enc[f]=encoder(f);
      for(let i=0;i<FPS*DURATION;i+=60){
        const frames=await page.evaluate(f=>window.capture.batch(60,f),formats);
        await Promise.all(formats.map(f=>push(enc[f].p,frames[f])));
        if(i%600===0)console.log('encoded input',i/FPS,'s');
      }
      for(const f of formats)enc[f].p.stdin.end();
      const results=await Promise.all(formats.map(f=>enc[f].result));
      if(results.some(([code])=>code!==0))throw new Error('Encoding failed: '+JSON.stringify(results));
    }
  }finally{await browser?.close();web.close();for(const {p} of Object.values(enc))if(p.exitCode==null)p.kill();}
}
