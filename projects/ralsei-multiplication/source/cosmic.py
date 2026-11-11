"""Native Ralsei dummy sprites drift, tumble, and spiral into a procedural hole."""
from math import sin,cos,pi
from PIL import Image,ImageDraw
import numpy as np

def cosmic_frame(v,t,edition):
 size=(360,640) if edition=='short' else (640,360)
 w,h=size; image=Image.new('RGB',size,(1,2,12));d=ImageDraw.Draw(image)
 # Original Cyber Field stars, repeated seamlessly over a dark space field.
 stars,_=v.source('nativeStars',0)
 for y in range(-stars.height,h,stars.height):
  for x in range(-stars.width,w,stars.width):image.paste(stars,(x,y),stars)
 center=(w*.52,h*.43)
 if t<93.6:
  if not hasattr(v,'_last_town'):
   v._last_town={}
  if edition not in v._last_town:v._last_town[edition]=v.frame(91.999,edition)
  image=Image.blend(v._last_town[edition],image,max(0,min(1,(t-92.8)/.8)))
  age=t-92
  for n in range(7):
   phase=age-n*.10
   if 0<=phase<.57:
    body,_=v.body('nativeExplosion',min(16,int(phase*30)),3.8)
    x=center[0]+sin(n*2.4)*w*.28-body.width/2;y=center[1]+cos(n*2.4)*h*.14-body.height/2
    image.paste(body,(round(x),round(y)),body)
  return image
 rng=np.random.default_rng(913)
 angles=rng.uniform(0,2*pi,38);radii=rng.uniform(.12,.6,38);spin=rng.uniform(-140,140,38)
 hole=max(0,min(1,(t-99)/1.8)) * (1-max(0,min(1,(t-109.2)/1.3)))
 if hole and t<110.5:
  r=38*hole
  for k in range(5):
   box=(center[0]-r-k*3,center[1]-r*.4-k,center[0]+r+k*3,center[1]+r*.4+k)
   d.ellipse(box,outline=(90-k*14,55-k*9,150-k*20),width=2)
  d.ellipse((center[0]-r,center[1]-r*.45,center[0]+r,center[1]+r*.45),fill='black')
 for i,(angle,radius,speed) in enumerate(zip(angles,radii,spin)):
  absorb=102+i/37*7
  if t>=absorb:continue
  drift=min(1,(t-93.6)/5.4)
  inward=max(0,min(1,(t-99)/(absorb-99)))
  orbit=angle+inward*inward*9
  distance=radius*(.5+.5*drift)*(1-inward**2)
  x=center[0]+cos(orbit)*w*distance;y=center[1]+sin(orbit)*h*.70*distance
  scale=max(.001,(.65+(i%5)*.18)*(1-inward**3)*min(1,(t-93.6)/.4))
  body,_=v.body('ralseiDummy',0,round(scale,3))
  body=body.rotate((t-93.6)*speed,resample=Image.Resampling.NEAREST,expand=True)
  image.paste(body,(round(x-body.width/2),round(y-body.height/2)),body)
 if t>=110.5:
  u=min(1,(t-110.5)/.8);body,anchor=v.body('starwalkerIdle',0,2)
  eased=u*u*(3-2*u)
  x=w/2;y=(h+body.height)*(1-eased)+h*.45*eased
  image.paste(body,(round(x-anchor[0]),round(y-anchor[1])),body)
 cue=next((q for q in v.story.DIALOGUE if q['start']<=t<q['end']),None)
 if cue:v.dialogue(image,cue,t,edition)
 return image
