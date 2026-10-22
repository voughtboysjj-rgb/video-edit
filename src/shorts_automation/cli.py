"""CPU-only original motion graphics pipeline. No remote upload operations."""
import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import wave
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
FPS = 24
DURATION = 16

def run(args, timeout=120):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]).stdout)

def environment():
    return {'python':sys.version, 'ffmpeg':run(['ffmpeg','-version']).stdout.splitlines()[0],
            'ffprobe':run(['ffprobe','-version']).stdout.splitlines()[0], 'free_bytes':shutil.disk_usage(ROOT).free}

def validate(plan):
    if plan.get('rights') != 'original_project_generated':
        raise ValueError('Rights not verified: production blocked')
    if plan['variant'] not in [1,2]:
        raise ValueError('Unknown variant')
    if plan['width'] != 1080 or plan['height'] != 1920 or plan['duration'] != DURATION:
        raise ValueError('Unsupported render settings')
    end=0
    for shot in plan['shots']:
        if shot['start'] != end or shot['end'] <= shot['start']:
            raise ValueError('Invalid or discontinuous timeline')
        end=shot['end']
    if end != DURATION:
        raise ValueError('Invalid timeline length')
    return plan

def plan_for(variant):
    return validate({'version':1,'seed':1729+variant,'variant':variant,
        'rights':'original_project_generated','width':1080,'height':1920,
        'duration':DURATION,'fps':FPS,'profile':'original_neon_reveal',
        'description':'Original abstract vector wolf reveal; not film footage or a replica of reference.',
        'shots':[{'start':0,'end':4,'mode':'calm','reason':'Quiet setup creates contrast'},
                 {'start':4,'end':6,'mode':'build','reason':'Anticipation before reveal'},
                 {'start':6,'end':14,'mode':'reveal','reason':'Geometric subject with rhythmic punch-ins'},
                 {'start':14,'end':16,'mode':'outro','reason':'Resolve and fade'}]})

def audio(path, variant):
    # Entire score synthesized here; no samples or third-party music.
    rate=44100
    data=array.array('h')
    bpm=120 if variant==1 else 132
    beat=60/bpm
    for i in range(rate*DURATION):
        t=i/rate
        phase=t%beat
        bass=math.sin(2*math.pi*(55 if variant==1 else 65.406)*t)
        kick=math.sin(2*math.pi*(48*phase+9*(1-math.exp(-30*phase))))*math.exp(-18*phase)
        note=[220,261.626,329.628,391.995][int(t/(beat/2))%4]
        arp=math.sin(2*math.pi*note*t)*math.exp(-12*(t%(beat/2)))
        build=0.35 if t<6 else 1
        fade=min(1,t/0.08,max(0,(DURATION-t)/0.6))
        value=fade*(0.11*bass+build*(0.34*kick+0.1*arp))
        sample=int(max(-0.95,min(0.95,value))*32767)
        data.extend((sample,sample))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(data.tobytes())

def frame(t, variant):
    w,h=540,960
    accent=(245,65,95) if variant==1 else (58,224,236)
    im=Image.new('RGB',(w,h),(5,9,18)); d=ImageDraw.Draw(im)
    rng=random.Random(1729+variant)
    for _ in range(65):
        x=rng.randrange(w); y=(rng.randrange(h)+int(t*(10+rng.randrange(15))))%h
        brightness=rng.randrange(25,90)
        d.ellipse((x,y,x+1,y+1),fill=(brightness,brightness,brightness+20))
    # Perspective grid, original programmatic artwork.
    horizon=610
    for n in range(-8,9):
        d.line((270+n*15,horizon,270+n*110,960), fill=(18,33,48),width=1)
    for n in range(9):
        y=horizon+((n/9+(t*.08)%1)%1)**2*350
        d.line((0,y,w,y),fill=(18,33,48),width=1)
    active=t>=6
    beat=60/(120 if variant==1 else 132)
    pulse=math.exp(-14*(t%beat)) if active else 0
    scale=(0.82 if not active else 1.03+0.045*pulse)
    if variant==2: scale*=1+0.035*math.sin(t*2)
    cx=270+math.sin(t*1.1)*(6 if active else 14);cy=440
    def poly(points,fill,outline=None,width=1):
        pts=[(cx+x*scale,cy+y*scale) for x,y in points]
        d.polygon(pts,fill=fill)
        if outline:d.line(pts+[pts[0]],fill=outline,width=width)
    # Wolf mask: explicit original polygons, not extracted from film or logo.
    edge=accent if active else (55,85,105)
    poly([(-150,-70),(-125,-205),(-58,-119),(0,-140),(58,-119),(125,-205),(150,-70),(100,65),(0,159),(-100,65)],(15,27,43),edge,2)
    poly([(-125,-180),(-109,-92),(-67,-119)],(35,49,63))
    poly([(125,-180),(109,-92),(67,-119)],(35,49,63))
    poly([(-145,-55),(-55,-105),(-35,-4),(-98,54)],(36,54,74))
    poly([(145,-55),(55,-105),(35,-4),(98,54)],(22,38,57))
    poly([(-55,-105),(0,-132),(55,-105),(35,-4),(0,85),(-35,-4)],(44,64,85))
    poly([(-98,54),(-35,-4),(0,85),(0,155)],(20,35,49))
    poly([(98,54),(35,-4),(0,85),(0,155)],(12,24,37))
    eyes=accent if active else (95,115,125)
    poly([(-105,-44),(-40,-25),(-60,-8),(-101,-19)],eyes)
    poly([(105,-44),(40,-25),(60,-8),(101,-19)],eyes)
    poly([(-25,55),(25,55),(0,85)],(3,7,12))
    if active:
        # Glow layer limited to eyes rather than flashing the full screen.
        glow=Image.new('RGB',(w,h));g=ImageDraw.Draw(glow)
        for x in (-74,74):
            ex=cx+x*scale;ey=cy-24*scale
            g.ellipse((ex-16,ey-8,ex+16,ey+8),fill=accent)
        from PIL import ImageChops
        im=ImageChops.add(im,glow.filter(ImageFilter.GaussianBlur(14)),scale=1.0)
        d=ImageDraw.Draw(im)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    def text(s,y,size,color):
        f=ImageFont.truetype(font,size)
        box=d.textbbox((0,0),s,font=f);x=(w-(box[2]-box[0]))/2
        d.text((x,y),s,font=f,fill=color)
    d.rounded_rectangle((30,40,168,66),radius=10,outline=(49,72,91))
    d.text((42,46),'ORIGINAL / 0'+str(variant),font=ImageFont.truetype(font,10),fill=(145,167,186))
    if t<4:
        text('STAY QUIET' if variant==1 else 'HOLD YOUR GROUND',150,29,(220,231,243))
        text('NOT EVERY SIGNAL IS LOUD',710,13,(130,154,176))
    elif t<6:
        text('WAIT FOR IT',150,32,accent)
        text('THE SHIFT IS COMING',710,14,(170,190,208))
    elif t<14:
        text('UNTIL IT IS TIME' if variant==1 else 'THEN TAKE THE LEAD',150,27,(235,242,250))
        text('AWAKEN' if variant==1 else 'FOCUS',695,56,accent)
        text('CONTROL THE ENERGY',775,15,(170,190,208))
    else:
        text('QUIET POWER' if variant==1 else 'MOVE WITH PURPOSE',710,26,(225,235,245))
        text('ORIGINAL MOTION STUDY',765,12,(130,154,176))
    d.rectangle((30,886,510,888),fill=(25,40,56))
    d.rectangle((30,886,30+480*t/DURATION,888),fill=accent)
    if t>15.5:
        im=Image.blend(Image.new('RGB',im.size),im,max(0,(16-t)/.5))
    return im

def qc(path):
    p=probe(path);vs=next(s for s in p['streams'] if s['codec_type']=='video');a=next((s for s in p['streams'] if s['codec_type']=='audio'),None)
    checks={'dimensions':vs['width']==1080 and vs['height']==1920,
            'video_codec':vs['codec_name']=='h264','audio_codec':bool(a and a['codec_name']=='aac'),
            'duration':abs(float(p['format']['duration'])-DURATION)<.2,
            'av_duration_match':bool(a and abs(float(vs['duration'])-float(a['duration']))<.15)}
    decode=run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'])
    checks['full_decode']=not decode.stderr.strip()
    audio_log=run(['ffmpeg','-hide_banner','-i',str(path),'-vn','-af','volumedetect','-f','null','-']).stderr
    return {'passed':all(checks.values()),'checks':checks,'probe':p,'audio_measurement_log':audio_log,
            'not_checked':['semantic crop quality','subtitle readability','integrated LUFS','human audiovisual review','platform acceptance']}

def produce(variant, outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    plan=plan_for(variant)
    config_hash=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    db=sqlite3.connect(ROOT/'jobs.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT, file_hash TEXT, report TEXT)')
    job=f'original-{variant}-{config_hash[:12]}'
    target=outdir/f'short_{variant:02}.mp4'
    old=db.execute('SELECT state,file_hash FROM jobs WHERE id=?',(job,)).fetchone()
    if old and old[0]=='awaiting_review' and target.exists() and sha(target)==old[1]:
        print('Already rendered, hash verified:',target);return
    if shutil.disk_usage(outdir).free<250_000_000:raise RuntimeError('Insufficient disk space')
    db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?)',(job,'rendering',None,None));db.commit()
    try:
        with tempfile.TemporaryDirectory(prefix='shorts-',dir=outdir) as tmp:
            tmp=Path(tmp);wav=tmp/'score.wav';audio(wav,variant);partial=tmp/'render.mp4'
            args=['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','540x960','-framerate',str(FPS),'-i','pipe:0','-i',str(wav),'-vf','scale=1080:1920:flags=lanczos','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-t',str(DURATION),str(partial)]
            with (tmp/'ffmpeg.log').open('wb') as log:
                proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=log)
                try:
                    for i in range(FPS*DURATION):proc.stdin.write(frame(i/FPS,variant).tobytes())
                    proc.stdin.close()
                    if proc.wait(timeout=180):raise RuntimeError((tmp/'ffmpeg.log').read_text())
                except BaseException:
                    proc.kill();proc.wait();raise
            result=qc(partial)
            if not result['passed']:raise ValueError('QC failed')
            os.replace(partial,target)
        metadata={'title':'Quiet Power — Original Neon Wolf' if variant==1 else 'Focus — Original Neon Wolf',
                  'description':'Original geometric animation and procedural synthesized instrumental. Not film footage.','#tags':['animation','motiongraphics','shorts']}
        report={'job':job,'state':'awaiting_review','plan':plan,'file':target.name,'sha256':sha(target),
                'metadata':metadata,'metadata_sha256':hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest(),
                'qc':result,'environment':environment(),'youtube':'not_configured','rights':'original_project_generated',
                'limitations':['Not a replica of reference footage','No speech or transcription','No automatic publishing','No beat detector; generated score uses a known clock']}
        (outdir/f'short_{variant:02}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
        db.execute('UPDATE jobs SET state=?,file_hash=?,report=? WHERE id=?',('awaiting_review',report['sha256'],json.dumps(report),job));db.commit()
        print('Rendered and QC passed:',target)
    except BaseException:
        db.execute('UPDATE jobs SET state=? WHERE id=?',('failed',job));db.commit();raise
    finally:db.close()

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('environment')
    p=sub.add_parser('plan');p.add_argument('--variant',type=int,choices=[1,2],default=1)
    p=sub.add_parser('produce');p.add_argument('--variant',type=int,choices=[1,2],required=True);p.add_argument('--out',default=str(ROOT/'outputs'))
    p=sub.add_parser('qc');p.add_argument('file')
    args=ap.parse_args()
    if args.command=='environment':print(json.dumps(environment(),indent=2))
    elif args.command=='plan':print(json.dumps(plan_for(args.variant),indent=2))
    elif args.command=='qc':print(json.dumps(qc(args.file),indent=2))
    else:produce(args.variant,args.out)
if __name__=='__main__':main()
