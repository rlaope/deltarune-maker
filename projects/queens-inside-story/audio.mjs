export const music = [
  {path:'bis/peachs-castle.mp3',scene:'map',gain:.38,loop:true},
  {path:'bis/tough-guy-alert.mp3',scene:'battle',gain:.49},
  {path:'bis/battle-victory.mp3',scene:'bossBurst',gain:.41},
];
const effects={
  gate:['dr/select.wav',.38],
  fieldPickup:['bis/field-pickup.wav',.58],
  fieldPower:['dr/tell.wav',.41],
  fieldBlock:['bis/field-block.wav',.33],
  tell:['dr/tell.wav',.37],
  shot:['dr/shot.wav',.31],
  hit:['bis/damage.wav',.65],
  select:['bis/confirm.wav',.43],
  blockHit:['bis/block-hit.wav',.68],
  charge:['dr/select.wav',.32],
  heal:['dr/event.wav',.50],
};

const jumps = {
  field: ['bis/field-jump.wav', .98],
  menu: ['bis/battle-jump.wav', .74],
  dodge: ['bis/dodge.wav', .69, .28, .010],
  stomp: ['bis/battle-jump.wav', .88],
};
const STOMP = 'bis/stomp.wav';
const GOOD = 'bis/good.wav';
const EXCELLENT = 'bis/excellent.wav';
const BOSS_BURST = 'bis/boss-burst.wav';
export const QUEEN_GLYPHS_PER_SECOND = 30;
const QUEEN_VOICE = 'dr/queen-text.wav';
const voices = { queen: QUEEN_VOICE, susie: 'dr/susie-text.wav' };
const HEART_SUCTION = 'dr/heart-suction.wav';
const ENCOUNTER = 'dr/encounter.wav';
const AXE_IMPACT = 'dr/impact.wav';
const BATTLE_HIT = 'bis/hit.wav';
const QUEEN_SILENT = new Set([' ', '\n', '&', '^', '!', '.', '?', ',', ':', '/', '\\', '|', '*']);

export const audioAssets = [...new Set([
  ...music.map(({ path }) => path),
  ...Object.values(effects).map(([path]) => path),
  ...Object.values(jumps).map(([path]) => path),
  ...Object.values(voices),
  HEART_SUCTION, ENCOUNTER, AXE_IMPACT, BATTLE_HIT, STOMP, GOOD, EXCELLENT, BOSS_BURST,
])];

function queenTextCues(text, time) {
  const cues = [];
  let cooldown = 0;
  let seed = (Math.round(time * 60) ^ 0x9e3779b9) >>> 0;
  for (const [index, glyph] of [...text].entries()) {
    cooldown = Math.max(0, cooldown - 1);
    if (cooldown || QUEEN_SILENT.has(glyph)) continue;
    cooldown = 2;
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const t = time + (index + 1) / QUEEN_GLYPHS_PER_SECOND;
    const previous = cues.at(-1);
    if (previous) previous.limit = t - previous.t;
    cues.push({
      path: QUEEN_VOICE,
      gain: .83,
      t,
      pan: .10,
      start: 0,
      playbackRate: .9 + .15 * (seed / 2 ** 32),
    });
  }
  return cues;
}

export function cues(event){
  const {t,type,target,mode}=event;
  const pan=target===0?-.26:target===1?-.10:0;
  const one=(path,gain,delta=0,p=pan,limit,start=0)=>[{path,gain,t:t+delta,pan:p,limit,start}];
  if(type==='line'){
    if(event.speaker==='queen')return queenTextCues(event.text,t);
    const voice=voices[event.speaker];
    if(!voice)return [];
    return [...event.text].flatMap((char,i)=>/\w/.test(char)&&i%2===0
      ?one(voice,.33,i/32,.10,.075):[]);
  }
  if(type==='transition')return [
    ...one(HEART_SUCTION,.53,.29,0,.84),
    ...one(AXE_IMPACT,.19,1.06,0,.21),
    ...one(ENCOUNTER,.59,1.31,0,.84),
  ];
  if(type==='jump'){
    // The first stomp contact already sounds on the rebound frame.
    if(mode==='bonus')return [];
    const [path,gain,limit,start]=jumps[mode]??jumps.stomp;
    return one(path,gain,0,pan,limit,start);
  }
  if(type==='release')return one(effects.shot[0],.36,0,pan,.20);
  if(type==='impact'||type==='excellent'){
    const hit=event.weapon==='axe'
      ?one(AXE_IMPACT,.78,0,pan,.32)
      :event.kind==='jump'
        ?one(STOMP,.72,0,pan,undefined,.010)
        :one(BATTLE_HIT,.72,0,pan,.31,.010);
    if(event.grade==='GOOD!')return [...hit,...one(GOOD,.56,.040,pan,undefined,.010)];
    if(event.grade==='EXCELLENT!')return [...hit,...one(EXCELLENT,.74,.045,pan,undefined,.010)];
    return hit;
  }
  if(type==='win')return one(BOSS_BURST,.62,0,0,undefined,.010);
  if(effects[type])return one(...effects[type],type==='fieldPickup'?.06:0,type==='shot'?.28:pan,undefined,type==='blockHit'?.010:0);
  return [];
}
