"""Two real re-edits of user-authorized reference. No upload to YouTube."""
import subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
SOURCE=ROOT/'2_5379566238978584676.mp4'
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
def execute(args):
    subprocess.run(args,check=True,timeout=240)
def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for variant in (1,2):
    name=OUT/f'reedit_0{variant}.mp4';temp=OUT/f'reedit_0{variant}.partial.mp4'
    if variant==1:
        base='[0:v]trim=start=0:end=20.766667,setpts=PTS-STARTPTS,fps=30,eq=contrast=1.035:saturation=1.045[v];[0:a]atrim=start=0:end=20.766667,asetpts=PTS-STARTPTS,afade=t=out:st=20.4:d=0.366667[a];'
        timeline=[{'start':0,'end':20.766667}]
    else:
        base='[0:v]split=2[v0][v1];[v0]trim=start=0:end=2.6,setpts=PTS-STARTPTS,fps=30[p0];[v1]trim=start=10:end=20.766667,setpts=PTS-STARTPTS,fps=30[p1];[p0][p1]concat=n=2:v=1:a=0,eq=contrast=1.05:saturation=1.06[v];[0:a]asplit=2[a0][a1];[a0]atrim=start=0:end=2.6,asetpts=PTS-STARTPTS,afade=t=out:st=2.55:d=0.05[q0];[a1]atrim=start=10:end=20.766667,asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st=10.4:d=0.366667[q1];[q0][q1]concat=n=2:v=0:a=1[a];'
        timeline=[{'start':0,'end':2.6},{'start':10,'end':20.766667}]
    graph=base+'[v]split=2[fg][bg];[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,gblur=sigma=14,eq=brightness=-0.09,scale=1080:1920[back];[fg]scale=1080:1200[front];[back][front]overlay=0:360,setsar=1,format=yuv420p[out]'
    execute(['ffmpeg','-y','-v','error','-i',str(SOURCE),'-filter_complex',graph,'-map','[out]','-map','[a]','-c:v','libx264','-preset','fast','-crf','19','-threads','4','-c:a','aac','-b:a','192k','-movflags','+faststart',str(temp)])
    p=probe(temp);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
    execute(['ffmpeg','-v','error','-i',str(temp),'-f','null','-'])
    checks={'dimensions':(v['width'],v['height'])==(1080,1920),'video_codec':v['codec_name']=='h264','audio_codec':a['codec_name']=='aac','duration':abs(float(p['format']['duration'])-sum(x['end']-x['start'] for x in timeline))<0.15,'av_duration_match':abs(float(v['duration'])-float(a['duration']))<0.15,'full_decode':True}
    if not all(checks.values()):raise ValueError(checks)
    temp.replace(name)
    report={'file':name.name,'sha256':digest(name),'source_sha256':digest(SOURCE),'rights':{'status':'user_attested','statement':'User states all images and music in the video are authorized. Not independently verified.'},'timeline_seconds':timeline,'render':'1080x1920,30fps,H264,AAC; full frame over blurred background; no watermark removal','qc':checks,'probe':p,'limits':['No beat-sync claim','No independent license verification','No human listening QA','Re-edit of existing compressed final, not raw scene production'],'youtube_upload':'not_performed'}
    (OUT/f'reedit_0{variant}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print('READY',name,flush=True)
