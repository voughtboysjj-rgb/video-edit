"""20-second, 60fps editorial remix. Source footage is reused; music/EDL/effects newly authored."""
from pathlib import Path
import subprocess, tempfile, json, hashlib, wave, math, shutil
import numpy as np
ROOT=Path(__file__).parent
SOURCE=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
RATE=48000;FPS=60;BEAT=25;TOTAL=1200
# start in source, duration in output frames, speed, focal x in source [0,1], framing
# Intro = 300 frames (5s). Cut positions use integer frames; 25 frames/beat = 144BPM.
EDL=[(5.7,150,1,.52,'wide'),(8.2,100,1,.52,'wide'),(9.6,50,.75,.52,'wide'),
(10.18,50,.80,.50,'hero'),(11.0,25,1.35,.51,'impact'),(13.08,75,.78,.50,'hero'),
(14.45,25,1.0,.49,'impact'),(14.82,25,1.0,.51,'impact'),(15.16,50,.85,.51,'close'),
(15.82,25,1.15,.50,'impact'),(16.55,50,.8,.55,'close'),(17.48,25,1,.54,'impact'),
(10.45,50,1.1,.50,'hero'),(12.12,25,1,.49,'reaction'),(13.3,50,.85,.5,'hero'),
(15.3,25,1.2,.51,'impact'),(16.62,50,.65,.54,'close'),(14.50,25,1.1,.5,'impact'),
(15.80,25,1.0,.50,'impact'),(11.12,25,1.1,.50,'impact'),(13.2,50,.9,.50,'hero'),
(16.45,50,.8,.54,'close'),(17.2,50,.75,.54,'close'),(15.30,25,1.05,.50,'impact'),
(13.08,50,.8,.50,'hero'),(17.25,50,.65,.54,'final')]
# Total output must stay exactly 1200 frames.
assert sum(s[1] for s in EDL)==TOTAL, sum(s[1] for s in EDL)

def run(args,timeout=300):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-5000:])
    return p

def score(path):
    n=RATE*20;mix=np.zeros((n,2));rng=np.random.default_rng(1442026)
    def add(time,sig,gain=1,pan=0):
        i=round(time*RATE);j=min(n,i+len(sig));sig=sig[:j-i]
        if i<0 or i>=n:return
        mix[i:j,0]+=sig*gain*math.sqrt((1-pan)/2)
        mix[i:j,1]+=sig*gain*math.sqrt((1+pan)/2)
    beat=60/144
    def bell(f,length=.3):
        u=np.arange(round(RATE*length))/RATE
        # Two detuned metal resonators with a short noisy attack.
        v=(np.sin(2*np.pi*f*u+1.1*np.sin(2*np.pi*1.48*f*u))+.5*np.sin(2*np.pi*1.48*f*u))
        return np.tanh(1.9*v)*np.exp(-13*u)*np.minimum(1,u/.002)
    notes=[622.254,622.254,739.989,554.365,622.254,466.164,554.365,415.305]
    for k in range(48):
        t=k*beat;drop=k>=12;half=k>=36
        # Kick and long 808 hits, while preserving kick transients.
        if not drop or k%8 in [0,2,3,4,6,7]:
            u=np.arange(round(RATE*.32))/RATE
            kick=np.sin(2*np.pi*(45*u+3.6*(1-np.exp(-38*u))))*np.exp(-19*u)
            add(t,kick,.62 if drop else .17)
        if drop:
            u=np.arange(round(RATE*beat*.98))/RATE
            f=[38.891,38.891,46.249,34.648][((k-12)//4)%4]
            # Portamento on selected 808s.
            f0=f*(1.5 if k%8==7 else 1)
            inst=f+(f0-f)*np.exp(-18*u)
            phase=2*np.pi*np.cumsum(inst)/RATE
            bass=np.tanh(2.8*(np.sin(phase)+.18*np.sin(2*phase)))
            env=np.minimum(1,u/.012)*np.exp(-3.8*u)
            duck=.5+.5*(1-np.exp(-24*u))
            add(t,bass*env*duck,.42)
        if k%2==1:
            u=np.arange(round(RATE*.16))/RATE
            noise=rng.normal(0,.35,len(u));noise=np.r_[0,np.diff(noise)]
            snare=(noise+np.sin(2*np.pi*185*u)*.25)*np.exp(-27*u)
            add(t,snare,.30 if drop else .07)
        hats=[0,.5] if not drop else ([0,.5,.75,.875] if k%4==3 else [0,.5])
        for h in hats:
            u=np.arange(round(RATE*.055))/RATE
            noise=rng.normal(0,.3,len(u));noise=np.r_[0,np.diff(noise)]
            add(t+h*beat,noise*np.exp(-85*u),.10 if drop else .025,pan=(-.25 if k%2 else .25))
        melody=[0,0,3,2,0,5,4,7][(k-12)%8] if drop else k%8
        voice=bell(notes[melody],.32)
        add(t,voice,.26 if drop else .055,pan=.08)
        if drop:
            add(t+beat*.75,voice,.035,pan=-.7)
            if k%4 in [1,3]:add(t+beat*.5,bell(notes[(melody+2)%8]*2,.15),.11,pan=-.25)
    # Rising reverse-noise swell into a deliberate short pre-drop gap.
    u=np.arange(round(RATE*1))/RATE
    add(4,rng.normal(0,.3,len(u))*(u**2),.16)
    mix[round(4.92*RATE):5*RATE]*=np.linspace(1,0,round(.08*RATE))[:,None]
    # Authored whooshes and downlifters, original noise only.
    for t in [5,10,15,18.75]:
        u=np.arange(round(RATE*.45))/RATE
        add(t,rng.normal(0,.25,len(u))*np.exp(-12*u),.10,pan=-.15)
    # Soft saturation on mix; fade and conservative headroom for AAC.
    mix=np.tanh(1.35*mix)
    t=np.arange(n)/RATE;mix*= (np.minimum(1,t/.02)*np.minimum(1,(20-t)/.25))[:,None]
    mix*=.68/max(.68,float(np.max(np.abs(mix))))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((mix*32767).astype('<i2').tobytes())
    return {'style':'original phonk-inspired cowbell/808 composition','bpm':144,'drop_at':5,'seed':1442026,'sample_rate':RATE,'third_party_samples':False,'peak_dbfs_pre_aac':float(20*np.log10(np.max(np.abs(mix))))}

def main():
    final=OUT/'wolf_phonk_directors_cut_20s_60fps.mp4';reportfile=final.with_suffix('.json')
    timeline=[];cursor=0
    folder=OUT/'directors_work';folder.mkdir(exist_ok=True)
    if True:
        tmp=Path(folder);wav=tmp/'score.wav';audio=score(wav);clips=[]
        for i,(src,frames,speed,focal,style) in enumerate(EDL):
            duration=frames/FPS;calm=style=='wide';zoom=1.02 if calm else (1.14 if style=='close' else 1.06)
            # Full-bleed editorial crop. Does not erase, inpaint or selectively cover source marks.
            # Focal point is authored per shot rather than a fixed center crop for all footage.
            width=int(round(1728*zoom/2)*2);height=int(round(1920*zoom/2)*2)
            marginx=width-1080;marginy=height-1920
            x=max(18,min(marginx-18,width*focal-540));y=marginy*.43
            amp=0 if calm else (8 if style=='impact' else 3)
            decay="exp(-14*t)"
            xexpr=f"{x:.3f}+{amp}*sin(88*t)*{decay}"
            yexpr=f"{y:.3f}+{amp*.6}*cos(73*t)*{decay}"
            bright='-0.005' if calm else '-0.012'
            graph=f"[0:v]trim=duration={duration*speed+.07:.9f},setpts=(PTS-STARTPTS)/{speed},fps=60:start_time=0,scale={width}:{height}:flags=lanczos,crop=1080:1920:x='{xexpr}':y='{yexpr}',setsar=1,eq=contrast={1.03 if calm else 1.10}:saturation={.82 if calm else 1.04}:brightness={bright}"
            if not calm:
                graph+=",unsharp=5:5:0.24:3:3:0"
            # Subtle chromatic displacement for only the impact frames, no strobe/flash.
            if style=='impact':graph+=",rgbashift=rh=2:bh=-2:enable='lt(t,0.05)'"
            # One short title before the drop; no persistent slogans or decorative bars.
            if i==2:
                graph+=",drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='WAIT.':fontsize=70:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=3:x=(w-tw)/2:y=h*0.8"
            graph+=f",tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={frames},setpts=N/(60*TB),format=yuv420p[v]"
            clip=tmp/f'{i:02}.mp4'
            run(['ffmpeg','-y','-v','error','-ss',str(src),'-i',str(SOURCE),'-filter_complex',graph,'-map','[v]','-an','-frames:v',str(frames),'-r','60','-fps_mode','cfr','-video_track_timescale','60000','-c:v','libx264','-preset','fast','-crf','18','-threads','4',str(clip)])
            cp=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',str(clip)]).stdout)
            assert int(cp['streams'][0]['nb_frames'])==frames, (i,cp['streams'][0]['nb_frames'],frames)
            clips.append(clip)
            timeline.append({'shot':i+1,'source_start':src,'output_start_frame':cursor,'output_frames':frames,'speed':speed,'focal_x':focal,'framing':style,'new_effects':['full-bleed focal crop','shot-specific grade','short decaying shake' if amp else 'no shake','brief chromatic offset' if style=='impact' else 'no chromatic offset'],'source_effects':'retained and not claimed as newly authored'})
            cursor+=frames;print(f'Shot {i+1}/{len(EDL)} complete',flush=True)
        listing=tmp/'clips.txt';listing.write_text('\n'.join("file '"+str(p)+"'" for p in clips))
        joined=tmp/'joined.mp4'
        run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(joined)])
        partial=tmp/'final.mp4'
        run(['ffmpeg','-y','-v','error','-i',str(joined),'-i',str(wav),'-map','0:v','-map','1:a','-vf','fps=60:start_time=0,tpad=stop_mode=clone:stop_duration=1,trim=end_frame=1200,setpts=N/(60*TB),fade=t=out:st=19.75:d=0.25','-r','60','-fps_mode','cfr','-video_track_timescale','60000','-c:v','libx264','-preset','fast','-crf','17','-threads','4','-c:a','aac','-b:a','256k','-t','20','-movflags','+faststart',str(partial)])
        p=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(partial)]).stdout)
        v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        decode=run(['ffmpeg','-v','error','-i',str(partial),'-f','null','-'])
        checks={'resolution':(v['width'],v['height'])==(1080,1920),'fps':v['avg_frame_rate']=='60/1','frames':int(v['nb_frames'])==1200,'duration':abs(float(p['format']['duration'])-20)<.04,'av_match':abs(float(v['duration'])-float(a['duration']))<.05,'decode':not decode.stderr}
        (tmp/'last_qc.json').write_text(json.dumps({'checks':checks,'probe':p},indent=2))
        assert all(checks.values()),checks
        level=run(['ffmpeg','-hide_banner','-i',str(partial),'-vn','-af','volumedetect','-f','null','-']).stderr.decode()
        partial.replace(final)
        report={'title':'Wolf — 20s Directors Cut','source':SOURCE.name,'rights':'user_attested','timeline':timeline,'music':audio,'render':p,'qc':checks,'audio_measurement':level,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'limitations':['full-bleed crop discards peripheral picture; source attribution retained separately in README','slowdown uses repeated frames, no optical-flow interpolation','baked-in effects remain from original','no professional human listening session','subjective superiority is not established'],'publication':'not uploaded to YouTube'}
        reportfile.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('READY',final,flush=True)
        shutil.rmtree(tmp)
if __name__=='__main__':main()
