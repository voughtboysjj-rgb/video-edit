"""Keep source's first 10 seconds intact in content/framing/timing; author last 10 seconds.
Native 1080x1200 aspect ratio, 60fps, 20 seconds. No crop, zoom or reframing.
"""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from create_phonk_directors_cut import score
ROOT=Path(__file__).parent
SOURCE=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
# Exactly 600 action frames (10 seconds); each segment length is a multiple of 25 frames.
SHOTS=[(10.20,100,.82),(13.08,50,.9),(14.45,25,1.1),(15.14,50,.8),
       (14.85,25,1),(15.84,50,.85),(16.55,75,.8),(11.05,25,1.2),
       (13.17,50,.9),(15.30,25,1.1),(16.70,75,.7),(13.08,50,.75)]
assert sum(s[1] for s in SHOTS)==600

def run(args,timeout=240):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-4000:])
    return p

def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]).stdout)
def main():
    target=OUT/'original_intro_10s_custom_finish_20s_60fps.mp4'
    with tempfile.TemporaryDirectory(prefix='original-intro-',dir=OUT) as folder:
        tmp=Path(folder);clips=[];timeline=[]
        intro=tmp/'intro.mp4'
        run(['ffmpeg','-y','-v','error','-i',str(SOURCE),'-an','-vf','trim=start_frame=0:end_frame=600,setpts=PTS-STARTPTS,eq=contrast=1.025:saturation=1.025,unsharp=5:5:0.12:3:3:0,setsar=1','-frames:v','600','-r','60','-fps_mode','cfr','-video_track_timescale','60000','-c:v','libx264','-preset','fast','-crf','16','-threads','4',str(intro)])
        clips.append(intro);timeline.append({'output_frames':[0,600],'source_frames':[0,600],'speed':1,'effects':['mild contrast 1.025','mild saturation 1.025','unsharp amount 0.12'],'geometry':'unchanged; no crop, scale, padding, rotation or zoom'})
        cursor=600
        for i,(start,frames,speed) in enumerate(SHOTS):
            duration=frames/60
            fx=f"trim=duration={duration*speed+.08},setpts=(PTS-STARTPTS)/{speed},fps=60:start_time=0,eq=contrast=1.075:saturation=1.04:brightness=-0.004,unsharp=5:5:0.20:3:3:0"
            if i in [2,4,7,9]:fx+=",rgbashift=rh=2:bh=-2:enable='lt(t,0.05)'"
            fx+=f',tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={frames},setpts=N/(60*TB),setsar=1,format=yuv420p'
            clip=tmp/f'action_{i:02}.mp4'
            run(['ffmpeg','-y','-v','error','-ss',str(start),'-i',str(SOURCE),'-an','-vf',fx,'-frames:v',str(frames),'-r','60','-fps_mode','cfr','-video_track_timescale','60000','-c:v','libx264','-preset','fast','-crf','17','-threads','4',str(clip)])
            v=probe(clip)['streams'][0];assert int(v['nb_frames'])==frames
            clips.append(clip);timeline.append({'output_frames':[cursor,cursor+frames],'source_start':start,'speed':speed,'geometry':'unchanged; full source frame','chromatic_hit':i in [2,4,7,9]})
            cursor+=frames;print('Action shot',i+1,'complete',flush=True)
        listing=tmp/'clips.txt';listing.write_text('\n'.join("file '"+str(p)+"'" for p in clips))
        joined=tmp/'joined.mp4';run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(joined)])
        music=tmp/'composed.wav';musicinfo=score(music)
        # Preserve source soundtrack until 10s; authored phonk starts exactly at 10s.
        audio="[1:a]atrim=start=0:end=10,asetpts=PTS-STARTPTS,aresample=48000,volume=0.4,afade=t=out:st=9.98:d=0.02[original];[2:a]atrim=start=5:end=15,asetpts=PTS-STARTPTS,volume=1.2,afade=t=out:st=9.75:d=0.25[phonk];[original][phonk]concat=n=2:v=0:a=1[a]"
        partial=tmp/'delivery.mp4'
        run(['ffmpeg','-y','-v','error','-i',str(joined),'-i',str(SOURCE),'-i',str(music),'-filter_complex',audio,'-map','0:v','-map','[a]','-vf','fps=60:start_time=0,tpad=stop_mode=clone:stop_duration=1,trim=end_frame=1200,setpts=N/(60*TB),fade=t=out:st=19.75:d=0.25','-frames:v','1200','-r','60','-fps_mode','cfr','-video_track_timescale','60000','-c:v','libx264','-preset','fast','-crf','16','-threads','4','-c:a','aac','-b:a','256k','-t','20','-movflags','+faststart',str(partial)])
        p=probe(partial);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        decode=run(['ffmpeg','-v','error','-i',str(partial),'-f','null','-'])
        checks={'source_dimensions_preserved':(v['width'],v['height'])==(1080,1200),'60fps':v['avg_frame_rate']=='60/1','1200_frames':int(v['nb_frames'])==1200,'20_seconds':abs(float(p['format']['duration'])-20)<.04,'av_duration_match':abs(float(v['duration'])-float(a['duration']))<.05,'full_decode':not decode.stderr}
        assert all(checks.values()),checks
        comparison=run(['ffmpeg','-hide_banner','-i',str(SOURCE),'-i',str(partial),'-filter_complex','[0:v]trim=end_frame=600,setpts=PTS-STARTPTS[a];[1:v]trim=end_frame=600,setpts=PTS-STARTPTS[b];[a][b]ssim','-an','-f','null','-']).stderr.decode()
        import re
        match=re.findall(r'All:([0-9.]+)',comparison)
        # Side-by-side visual evidence of first ten seconds. Labels do not touch delivery.
        comparison_video=OUT/'intro_comparison_original_left_edited_right.mp4'
        run(['ffmpeg','-y','-v','error','-i',str(SOURCE),'-i',str(partial),'-filter_complex',"[0:v]trim=end_frame=600,setpts=PTS-STARTPTS,scale=540:600,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='ORIGINAL':fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5:x=10:y=10[a];[1:v]trim=end_frame=600,setpts=PTS-STARTPTS,scale=540:600,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='EDITED - SAME FRAMING':fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5:x=10:y=10[b];[a][b]hstack[v]",'-map','[v]','-an','-r','60','-c:v','libx264','-preset','fast','-crf','19','-threads','4','-movflags','+faststart',str(comparison_video)])
        levels=run(['ffmpeg','-hide_banner','-i',str(partial),'-vn','-af','volumedetect','-f','null','-']).stderr.decode()
        partial.replace(target)
        report={'file':target.name,'duration':20,'fps':60,'dimensions':[1080,1200],'first_ten_seconds':'Source frames 0-599, same timing and full framing, original soundtrack retained with level balancing and 20ms ending fade; subtle grade/sharpening only. Re-encoded, not byte-identical.','timeline':timeline,'second_half_music':{**musicinfo,'input_excerpt_seconds':[5,15],'output_start':10},'intro_ssim':float(match[-1]) if match else None,'ssim_interpretation':'Measures difference after subtle grading and re-encoding, not proof of aesthetic superiority.','qc':checks,'audio_measurement':levels,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_rights':'user_attested, not independently verified','authorship':'Source imagery and baked-in effects retained. Second-half order, rates, new chromatic hits, grade, ending and music authored by project.','limitations':['Native source aspect ratio, not 9:16','No claim of new detail recovery','No human listening QA','Slowdowns may repeat source frames'],'youtube_upload':'not performed'}
        target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('READY',target,flush=True);print('QC',checks,flush=True)
if __name__=='__main__':main()
