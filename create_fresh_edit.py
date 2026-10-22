"""A newly authored montage from user-attested footage, with an original synthesized score.
Effects already baked into source are not claimed as authored here.
"""
from pathlib import Path
import hashlib,json,subprocess,wave,tempfile
import numpy as np
ROOT=Path(__file__).parent
SRC=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
FPS=30;RATE=44100;DURATION=14
# source start, output length, playback rate, label, creative purpose
SHOTS=[(13.1,.5,1,'THE SWITCH','Cold open on serious character'),
 (6,2,1,'BEFORE','Contrast: return to comic performance'),
 (9.5,.5,1.3,'WAIT...','Accelerate anticipation'),
 (10.2,1.5,.9,'AFTER','Main reveal on synthesized beat'),
 (12.15,.5,1,'','Reaction insert'),
 (13.1,1,1.15,'NO MORE GAMES','Hero beat'),
 (14.45,.5,1.1,'','Short attack'),
 (14.9,.5,.8,'','Hold intensity'),
 (15.2,.5,1,'','Close-up'),
 (15.85,.5,1.25,'','Fast action'),
 (16.55,1,.8,'FOCUS','Slow emphasis'),
 (17.7,.5,1,'','Detail cut'),
 (10.95,.5,1.2,'','Return motif'),
 (16.6,1.5,.7,'','Slow close-up'),
 (15.45,.5,1.4,'','Final hit'),
 (16.65,2,.8,'QUIET. NOT WEAK.','Resolve and fade')]

def run(args):return subprocess.run(args,check=True,capture_output=True,timeout=240)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]).stdout)
def score(path):
    n=RATE*DURATION;t=np.arange(n)/RATE;mix=np.zeros(n);rng=np.random.default_rng(1022)
    # Original composition, no samples or melody borrowed from the source.
    def add(start,signal,gain=1):
        i=round(start*RATE);end=min(n,i+len(signal))
        if i<n:mix[i:end]+=signal[:end-i]*gain
    for k in range(28):
        start=k*.5
        u=np.arange(int(RATE*.4))/RATE
        kick=np.sin(2*np.pi*(47*u+2.5*(1-np.exp(-35*u))))*np.exp(-18*u)
        add(start,kick,.40 if start>=3 else .13)
        if k%2==1 and start>=3:
            u=np.arange(int(RATE*.15))/RATE
            noise=rng.uniform(-1,1,len(u));noise=np.r_[0,np.diff(noise)]
            add(start,noise*np.exp(-30*u),.09)
        for sub in [0,.25]:
            u=np.arange(int(RATE*.06))/RATE
            add(start+sub,rng.uniform(-1,1,len(u))*np.exp(-65*u),.035 if start>=3 else .012)
        u=np.arange(int(RATE*.48))/RATE
        f=[55,55,65.406,49][(k//4)%4]
        bass=(np.sin(2*np.pi*f*u)+.2*np.sin(2*np.pi*2*f*u))*np.minimum(1,u/.015)*np.exp(-5*u)
        add(start,bass,.17 if start>=3 else .08)
    # Minor arpeggio, brighter after reveal.
    for k in range(56):
        start=k*.25;u=np.arange(int(RATE*.32))/RATE
        f=[220,261.626,329.628,440,391.995,329.628,261.626,220][k%8]
        add(start,np.sin(2*np.pi*f*u)*np.exp(-12*u)*np.minimum(1,u/.008),.055 if start>=3 else .025)
    # Short rising texture before the main reveal, not a full-frame flash.
    u=np.arange(int(RATE*.5))/RATE
    add(2.5,rng.uniform(-1,1,len(u))*(u/.5)**2,.045)
    mix*=np.minimum(1,t/.04)*np.minimum(1,(DURATION-t)/.4)
    peak=float(np.max(np.abs(mix)));mix*=.79/max(peak,.79)
    stereo=np.stack([mix,mix],axis=1)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((stereo*32767).astype('<i2').tobytes())
    return {'seed':1022,'bpm':120,'bpm_source':'composition clock, not inferred from reference','peak_dbfs_before_aac':float(20*np.log10(np.max(np.abs(mix)))),'rights':'original_project_generated'}

def main():
    timeline=[];cursor=0
    for i,(src,duration,speed,label,reason) in enumerate(SHOTS):
        timeline.append({'shot':i+1,'source_start':src,'source_end':src+duration*speed,'output_start':cursor,'output_end':cursor+duration,'speed':speed,'label':label,'reason':reason,'new_effects':['independent animated scale of full foreground','shot-specific color grade','new beat-grid cut placement'],'source_effects':'retained, not authored by this project'})
        cursor+=duration
    assert cursor==DURATION
    final=OUT/'fresh_edit_the_switch.mp4'
    with tempfile.TemporaryDirectory(prefix='fresh-edit-',dir=OUT) as folder:
        tmp=Path(folder);wav=tmp/'original_score.wav';audio=score(wav)
        clips=[]
        for i,shot in enumerate(timeline):
            duration=shot['output_end']-shot['output_start'];src=shot['source_start'];speed=shot['speed']
            # Scale the complete foreground inside the canvas, not crop its watermark.
            calm=i in (1,2)
            contrast=1.02 if calm else 1.12;saturation=.6 if calm else 1.12
            scale_expr="960*(1+0.065*(1-exp(-5*t)))" if not calm else "940*(1+0.018*sin(2*t))"
            graph=f"[0:v]trim=duration={duration*speed:.8f},setpts=(PTS-STARTPTS)/{speed},fps=30,eq=contrast={contrast}:saturation={saturation}:brightness=-0.012,split=2[bg][fg];[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,gblur=sigma=15,eq=brightness=-0.13,scale=1080:1920[b];[fg]scale=w='{scale_expr}':h=-2:eval=frame,setsar=1[f];[b][f]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame,setsar=1"
            # Original typography occupies margin outside the full source image.
            if shot['label']:
                text=tmp/f'text{i}.txt';text.write_text(shot['label'])
                graph+=f",drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile={text}:fontsize=52:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2:x=(w-tw)/2:y=1550"
            graph+=",drawbox=x=100:y=1640:w=880:h=3:color=0xC62E48:t=fill,format=yuv420p[v]"
            clip=tmp/f'shot_{i:02}.mp4'
            run(['ffmpeg','-y','-v','error','-ss',str(src),'-i',str(SRC),'-filter_complex',graph,'-map','[v]','-an','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','19','-threads','4',str(clip)])
            clips.append(clip);print('Rendered shot',i+1,flush=True)
        listing=tmp/'clips.txt';listing.write_text('\n'.join("file '"+str(p)+"'" for p in clips))
        joined=tmp/'joined.mp4'
        run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(joined)])
        partial=tmp/'final.mp4'
        run(['ffmpeg','-y','-v','error','-i',str(joined),'-i',str(wav),'-map','0:v','-map','1:a','-vf','fade=t=out:st=13.65:d=0.35','-c:v','libx264','-preset','fast','-crf','18','-threads','4','-c:a','aac','-b:a','192k','-t','14','-movflags','+faststart',str(partial)])
        p=probe(partial);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        decode=run(['ffmpeg','-v','error','-i',str(partial),'-f','null','-'])
        checks={'size':(v['width'],v['height'])==(1080,1920),'frames':int(v['nb_frames'])==420,'duration':abs(float(p['format']['duration'])-14)<.06,'av_match':abs(float(v['duration'])-float(a['duration']))<.06,'full_decode':not decode.stderr}
        assert all(checks.values()),checks
        level=run(['ffmpeg','-hide_banner','-i',str(partial),'-vn','-af','volumedetect','-f','null','-']).stderr.decode()
        partial.replace(final)
        report={'title':'The Switch — newly authored montage','source':SRC.name,'source_sha256':digest(SRC),'source_rights':'user_attested','duration':14,'timeline':timeline,'audio':audio,'render':'1080x1920 30fps H264/AAC','qc':checks,'audio_level_log':level,'sha256':digest(final),'authorship':{'newly_authored':['shot order and durations','per-shot playback rates (not continuous speed ramps)','animated foreground scaling','shot-specific grade','margin typography','entire synthesized instrumental','ending fade'],'reused':['all character imagery','all effects baked into source'],'not_claimed':['raw film animation authorship','recovery of original project layers','removal of original watermark']},'not_checked':['human listening review','native 1080 detail','independent source license verification'],'youtube_upload':'not performed'}
        (OUT/'fresh_edit_the_switch.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('READY',final,flush=True)
if __name__=='__main__':main()
