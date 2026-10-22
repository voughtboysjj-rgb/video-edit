"""A newly authored montage from user-attested footage, with an original synthesized score.
Effects already baked into source are not claimed as authored here.
"""
from pathlib import Path
import hashlib,json,subprocess,wave,tempfile
import numpy as np
ROOT=Path(__file__).parent
SRC=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
FPS=60;RATE=44100;DURATION=14.4
# source start, output length, playback rate, label, creative purpose
SHOTS=[(6,2.4,1,'JUST HAVING FUN','Comic opening'),
 (9,.8,1,'UNTIL...','Comic anticipation before drop'),
 (10.2,1.6,1,'THE SWITCH','Serious wolf reveal on beat 8'),
 (13.1,.8,1.1,'NO MORE GAMES','Hero shot'),
 (14.45,.4,1,'','Attack'),
 (14.9,.4,1,'','Impact'),
 (15.2,.8,1,'','Close-up'),
 (15.85,.4,1.15,'','Fast action'),
 (16.55,1.2,1,'FOCUS','Hold the stare'),
 (17.7,.8,1,'','Weapon detail'),
 (10.95,.8,1,'','Return motif'),
 (16.6,1.6,1,'','Sustained intensity'),
 (15.45,.4,1.2,'','Final hit'),
 (16.65,2,1,'QUIET. NOT WEAK.','Resolution')]


def run(args):return subprocess.run(args,check=True,capture_output=True,timeout=240)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]).stdout)
def score(path):
    n=round(RATE*DURATION);t=np.arange(n)/RATE;mix=np.zeros(n);rng=np.random.default_rng(606150)
    beat=.4;drop=3.2
    def add(start,signal,gain=1):
        i=round(start*RATE);end=min(n,i+len(signal))
        if i<n:mix[i:end]+=signal[:end-i]*gain
    def cowbell(freq,length=.28):
        u=np.arange(round(RATE*length))/RATE
        # Metallic two-resonator, FM-like cowbell voice. No third-party samples.
        tone=np.sin(2*np.pi*freq*u+1.6*np.sin(2*np.pi*freq*1.48*u))
        tone+=.55*np.sin(2*np.pi*freq*1.48*u)
        return np.tanh(1.8*tone)*np.exp(-15*u)*np.minimum(1,u/.002)
    notes=[587.33,587.33,698.46,523.25,587.33,466.16,523.25,440]
    for k in range(36):
        start=k*beat;active=start>=drop
        u=np.arange(round(RATE*.35))/RATE
        kick=np.sin(2*np.pi*(43*u+3.2*(1-np.exp(-42*u))))*np.exp(-17*u)
        add(start,kick,.6 if active else .12)
        if active:
            u=np.arange(round(RATE*.42))/RATE
            f=[43.654,43.654,51.913,38.891][((k-8)//4)%4]
            env=np.minimum(1,u/.008)*np.exp(-5*u)
            sub=np.sin(2*np.pi*f*u)+.25*np.sin(2*np.pi*2*f*u)
            add(start,np.tanh(2.7*sub)*env,.31)
        if k%2==1:
            u=np.arange(round(RATE*.14))/RATE
            noise=rng.uniform(-1,1,len(u));noise=np.r_[0,np.diff(noise)]
            add(start,noise*np.exp(-30*u),.14 if active else .035)
        for sub in [0,.2,.3] if active else [0]:
            u=np.arange(round(RATE*.045))/RATE
            add(start+sub,rng.uniform(-1,1,len(u))*np.exp(-95*u),.055 if active else .02)
        add(start,cowbell(notes[k%8]),.18 if active else .055)
        if active and k%4 in [1,3]:
            add(start+.2,cowbell(notes[(k+2)%8]*2,.16),.09)
    # Riser and impact mark the change from comic opening to serious wolf.
    u=np.arange(round(RATE*.8))/RATE
    add(2.4,rng.uniform(-1,1,len(u))*(u/.8)**2,.065)
    u=np.arange(round(RATE*.6))/RATE
    add(drop,np.sin(2*np.pi*(29*u+5*(1-np.exp(-12*u))))*np.exp(-7*u),.4)
    mix=np.tanh(1.6*mix)
    mix*=np.minimum(1,t/.03)*np.minimum(1,(DURATION-t)/.35)
    mix*=.88/max(.88,float(np.max(np.abs(mix))))
    stereo=np.stack([mix,mix],axis=1)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((stereo*32767).astype('<i2').tobytes())
    return {'seed':606150,'style':'original synthesized phonk-inspired instrumental','bpm':150,'drop_seconds':3.2,'bpm_source':'composition clock','peak_dbfs_before_aac':float(20*np.log10(np.max(np.abs(mix)))),'rights':'original_project_generated','instruments':['metallic FM cowbell','distorted sub bass 808-style','synthesized kick','noise clap','hi hats']}

def main():
    timeline=[];cursor=0
    for i,(src,duration,speed,label,reason) in enumerate(SHOTS):
        timeline.append({'shot':i+1,'source_start':src,'source_end':src+duration*speed,'output_start':cursor,'output_end':cursor+duration,'speed':speed,'label':label,'reason':reason,'new_effects':['independent animated scale of full foreground','shot-specific color grade','new beat-grid cut placement'],'source_effects':'retained, not authored by this project'})
        cursor+=duration
    assert abs(cursor-DURATION)<1e-8
    final=OUT/'phonk_wolf_60fps.mp4'
    with tempfile.TemporaryDirectory(prefix='fresh-edit-',dir=OUT) as folder:
        tmp=Path(folder);wav=tmp/'original_score.wav';audio=score(wav)
        clips=[]
        for i,shot in enumerate(timeline):
            duration=shot['output_end']-shot['output_start'];src=shot['source_start'];speed=shot['speed']
            # Scale the complete foreground inside the canvas, not crop its watermark.
            calm=i in (0,1)
            contrast=1.02 if calm else 1.12;saturation=.6 if calm else 1.12
            scale_expr="960*(1+0.065*(1-exp(-5*t)))" if not calm else "940*(1+0.018*sin(2*t))"
            graph=f"[0:v]trim=duration={duration*speed:.8f},setpts=(PTS-STARTPTS)/{speed},fps=60,eq=contrast={contrast}:saturation={saturation}:brightness=-0.012,split=2[bg][fg];[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,gblur=sigma=15,eq=brightness=-0.13,scale=1080:1920[b];[fg]scale=w='{scale_expr}':h=-2:eval=frame,setsar=1[f];[b][f]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame,setsar=1"
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
        run(['ffmpeg','-y','-v','error','-i',str(joined),'-i',str(wav),'-map','0:v','-map','1:a','-vf','fade=t=out:st=14.05:d=0.35','-c:v','libx264','-preset','fast','-crf','18','-threads','4','-af','volume=0.75','-c:a','aac','-b:a','192k','-t',str(DURATION),'-movflags','+faststart',str(partial)])
        p=probe(partial);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        decode=run(['ffmpeg','-v','error','-i',str(partial),'-f','null','-'])
        checks={'size':(v['width'],v['height'])==(1080,1920),'frames':int(v['nb_frames'])==864,'duration':abs(float(p['format']['duration'])-DURATION)<.06,'av_match':abs(float(v['duration'])-float(a['duration']))<.06,'full_decode':not decode.stderr}
        assert all(checks.values()),checks
        level=run(['ffmpeg','-hide_banner','-i',str(partial),'-vn','-af','volumedetect','-f','null','-']).stderr.decode()
        partial.replace(final)
        report={'title':'Comic to Menacing Wolf — 60fps Phonk','source':SRC.name,'source_sha256':digest(SRC),'source_rights':'user_attested','duration':DURATION,'timeline':timeline,'audio':audio,'render':'1080x1920 60fps H264/AAC','qc':checks,'audio_level_log':level,'sha256':digest(final),'authorship':{'newly_authored':['shot order and durations','per-shot playback rates (not continuous speed ramps)','animated foreground scaling','shot-specific grade','margin typography','entire synthesized instrumental','ending fade'],'reused':['all character imagery','all effects baked into source'],'not_claimed':['raw film animation authorship','recovery of original project layers','removal of original watermark']},'not_checked':['human listening review','native 1080 detail','independent source license verification'],'youtube_upload':'not performed'}
        (OUT/'phonk_wolf_60fps.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('READY',final,flush=True)
if __name__=='__main__':main()
