"""Forensic timeline reconstruction from a flattened MP4, not effect-layer recovery.
Reuses baked-in image/audio. Run: python reverse_engineer.py
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).parent
SOURCE=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'reports/reconstruction';OUT.mkdir(parents=True,exist_ok=True)
FPS=60

def run(args,timeout=240):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)

def main():
    metadata=OUT/'scene_scores.txt'
    run(['ffmpeg','-v','error','-y','-i',str(SOURCE),'-an','-vf',f"scale=270:-1,select='gte(scene,0)',metadata=print:file={metadata}",'-f','null','-'])
    rows=[{'frame':int(f),'time':float(t),'score':float(s)} for f,t,s in re.findall(r'frame:(\d+).*?pts_time:([\d.]+)\s+lavfi.scene_score=([\d.]+)',metadata.read_text())]
    count=len(rows)
    # Group adjacent detector events. These are candidate boundaries, not verified shots.
    groups=[]
    for r in rows:
        if r['score']<.12:continue
        if groups and r['frame']-groups[-1][-1]['frame']<=12:groups[-1].append(r)
        else:groups.append([r])
    events=[{'frame':g[0]['frame'],'time':g[0]['frame']/FPS,'status':'estimated','method':'scene score >=0.12; first event in group, gaps <=12 frames grouped','max_score':max(r['score'] for r in g)} for g in groups]
    # Manually located transition from a 4fps contact sheet; deliberately not marked exact.
    events.append({'frame':610,'time':610/FPS,'status':'estimated','method':'visual contact sheet: character/scene change around 10.2s; exact boundary not verified','max_score':None})
    events.sort(key=lambda e:e['frame'])
    marks=sorted(set([0,count]+[e['frame'] for e in events]))
    segments=[{'id':f'B{i+1:02}','start_frame':a,'end_frame_exclusive':b,'start':a/FPS,'end':b/FPS,'role':'candidate block, not a verified single shot','effects':'already baked into source; not recovered'} for i,(a,b) in enumerate(zip(marks,marks[1:]))]
    # Measure energy windows, not perceived loudness and not musical beat truth.
    wav=OUT/'analysis_audio.wav'
    run(['ffmpeg','-v','error','-y','-i',str(SOURCE),'-vn','-ac','1','-ar','22050',str(wav)])
    with wave.open(str(wav),'rb') as f:
        samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float64)/32768;rate=f.getframerate()
    hop=int(rate*.02);windows=[samples[i:i+hop] for i in range(0,len(samples),hop)]
    rms=np.array([math.sqrt(float(np.mean(w*w))) for w in windows])
    peaks=[float(np.max(np.abs(w))) for w in windows]
    rising=np.maximum(0,np.diff(rms,prepend=rms[0]));candidates=[]
    threshold=float(np.percentile(rising,95))
    for i in range(1,len(rising)-1):
        if rising[i]>threshold and rising[i]>=rising[i-1] and rising[i]>=rising[i+1] and (not candidates or i*.02-candidates[-1]>.15):candidates.append(round(i*.02,3))
    audio={'method':'mono 22050Hz PCM; 20ms RMS windows; 95th percentile positive RMS rise','rms_windows':[{'time':round(i*.02,3),'rms':float(v),'peak':peaks[i]} for i,v in enumerate(rms)],'energy_rise_candidates':candidates,'bpm':None,'beats_verified':False,'limitations':'Energy rises are not verified beats. No source separation, independent music track, or listening QA.'}
    (OUT/'audio_energy.json').write_text(json.dumps(audio,indent=2))
    # Native aspect ratio is preserved. Split source into timeline blocks and concatenate.
    filters=[];n=len(segments)
    filters.append('[0:v]split='+str(n)+''.join(f'[s{i}]' for i in range(n)))
    for i,s in enumerate(segments):filters.append(f"[s{i}]trim=start_frame={s['start_frame']}:end_frame={s['end_frame_exclusive']},setpts=PTS-STARTPTS[b{i}]")
    filters.append(''.join(f'[b{i}]' for i in range(n))+f'concat=n={n}:v=1:a=0[v]')
    (OUT/'filtergraph.txt').write_text(';\n'.join(filters))
    target=ROOT/'outputs/reconstructed_timeline.mp4'
    command=['ffmpeg','-y','-v','error','-i',str(SOURCE),'-filter_complex',';'.join(filters),'-map','[v]','-map','0:a','-c:v','libx264','-preset','fast','-crf','16','-threads','4','-c:a','copy','-movflags','+faststart',str(target)]
    run(command)
    # Pixel comparison after re-encoding, not evidence of effect recovery.
    cmp=run(['ffmpeg','-hide_banner','-i',str(SOURCE),'-i',str(target),'-filter_complex','[0:v][1:v]ssim','-an','-f','null','-'])
    cmp_log=cmp.stderr.decode(errors='replace');(OUT/'ssim.log').write_text(cmp_log)
    match=re.findall(r'All:([0-9.]+)',cmp_log);ssim=float(match[-1]) if match else None
    p=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target)]).stdout)
    v=next(s for s in p['streams'] if s['codec_type']=='video')
    decoded=run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'])
    plan={'source':SOURCE.name,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rights':'user_attested; independent license review not performed','fps':FPS,'frame_count':count,'events':events,'blocks':segments,'scene_scores':rows,'audio_energy_file':'audio_energy.json','recovery':{'timeline_partition':'implemented','source_pixels':'reused including baked-in effects','original_audio_mix':'reused, AAC stream copy','raw_footage':'not available','zoom_curves':'not recovered','speed_ramp_curves':'not recovered','color_LUT':'not recovered','transition_layers':'not recovered','watermarks':'preserved'},'result':{'file':target.name,'ssim_all':ssim,'frame_count':int(v['nb_frames']),'frame_count_matches':int(v['nb_frames'])==count,'width':v['width'],'height':v['height'],'full_decode_passed':not decoded.stderr,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},'interpretation':'High similarity demonstrates timeline reassembly and low re-encode distortion only. It does not demonstrate independent reconstruction of baked-in effects.'}
    (OUT/'edit_plan.json').write_text(json.dumps(plan,indent=2))
    # An explicitly annotated breakdown makes the engineering visible.
    ass=['[Script Info]','PlayResX: 1080','PlayResY: 1200','[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding','Style: Default,DejaVu Sans,26,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,2,0,8,20,20,20,1','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def stamp(t):
        cs=round(t*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
    for s in segments:
        txt=f"ANALYSIS / {s['id']} / frames {s['start_frame']}-{s['end_frame_exclusive']-1}\\NSource effects retained - NOT independently recovered"
        ass.append(f"Dialogue: 0,{stamp(s['start'])},{stamp(s['end'])},Default,,0,0,0,,{txt}")
    subtitle=OUT/'breakdown.ass';subtitle.write_text('\n'.join(ass))
    annotated=ROOT/'outputs/reconstruction_breakdown.mp4'
    run(['ffmpeg','-y','-v','error','-i',str(target),'-vf',f'ass={subtitle}','-c:v','libx264','-preset','fast','-crf','20','-threads','4','-c:a','copy','-movflags','+faststart',str(annotated)])
    # Static visual plot.
    im=Image.new('RGB',(1200,440),'#08121e');d=ImageDraw.Draw(im)
    d.text((25,15),'REFERENCE FORENSICS | top: scene score | bottom: RMS audio energy',fill='white')
    for k,arr,col,top in [('scene',np.array([r['score'] for r in rows]),'#48d3ef',55),('rms',rms,'#fa5975',240)]:
        maximum=max(float(np.max(arr)),.00001)
        pts=[(25+i/(len(arr)-1)*1150,top+140-140*float(a)/maximum) for i,a in enumerate(arr)]
        d.line(pts,fill=col,width=2)
    for e in events:
        x=25+e['time']/(count/FPS)*1150;d.line((x,45,x,390),fill='#42536c')
    d.text((25,410),'Vertical lines = candidate boundaries, not verified cuts. RMS spikes are not verified beats.',fill='white')
    im.save(OUT/'measurements.png')
    print(json.dumps({'blocks':n,'frames':count,'result':plan['result']},indent=2),flush=True)
if __name__=='__main__':main()
