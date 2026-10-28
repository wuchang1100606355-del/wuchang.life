#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, math, subprocess, tempfile, wave, zlib
from pathlib import Path
import numpy as np
from scipy import signal

SR=24000; DUR=4.5
ROOT=Path("/tmp/w7tp_audio_origin_cell_lab/v3")
ROOT.mkdir(parents=True, exist_ok=True)

def cjson(o): return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()
def h(b): return hashlib.sha256(b).hexdigest()
def midi(n): return 440.0*(2.0**((n-69)/12.0))
def env(n,a,d):
    t=np.arange(n)/SR
    return np.minimum(1.0,t/max(a,1e-6))*np.exp(-d*t)
def add(dst,src,onset):
    s=int(round(onset*SR)); e=min(len(dst),s+len(src))
    if s < len(dst): dst[s:e]+=src[:e-s]
def piano(note,dur,vel):
    n=max(1,int(dur*SR)); t=np.arange(n)/SR; f=midi(note)
    return (np.sin(2*np.pi*f*t)+.45*np.sin(4*np.pi*f*t)+.18*np.sin(6*np.pi*f*t))*env(n,.008,2.4)*vel*.42
def bass(note,dur,vel):
    n=max(1,int(dur*SR)); t=np.arange(n)/SR; f=midi(note)
    return (np.sin(2*np.pi*f*t)+.25*np.sin(4*np.pi*f*t))*env(n,.015,1.8)*vel*.55
def drum(kind,dur,vel,seed):
    n=max(1,int(dur*SR)); t=np.arange(n)/SR; rng=np.random.default_rng(seed)
    if kind=="kick":
        f=45+75*np.exp(-t*18); y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*10)
    elif kind=="snare":
        y=(.82*rng.standard_normal(n)+.18*np.sin(2*np.pi*180*t))*np.exp(-t*13)
    else:
        q=rng.standard_normal(n); y=np.concatenate([[0.0],np.diff(q)])*np.exp(-t*24)
    return y/max(1e-9,float(np.max(np.abs(y))))*vel*.42
def wav_bytes(mono):
    bio=io.BytesIO(); pcm=(np.clip(mono,-1,1)*32767).astype(np.int16)
    with wave.open(bio,"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())
    return bio.getvalue()
def read_wav(path):
    with wave.open(str(path),"rb") as wf:
        sr=wf.getframerate(); ch=wf.getnchannels(); raw=wf.readframes(wf.getnframes())
    x=np.frombuffer(raw,dtype=np.int16).astype(float)/32768.0
    if ch>1: x=x.reshape(-1,ch).mean(axis=1)
    if sr!=SR: x=signal.resample(x,max(1,int(round(len(x)*SR/sr))))
    return x
VOICE={"M1":"cmn+m3","F1":"cmn+f2","F2":"cmn+f4"}
def voice(vid,text):
    with tempfile.TemporaryDirectory(prefix="w7tp-v3-") as td:
        p=Path(td)/"v.wav"
        subprocess.run(["/usr/bin/espeak-ng","-v",VOICE[vid],"-s","172","-p","68","-w",str(p),text],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return read_wav(p)
def render(cell):
    out=np.zeros(int(cell["dur_s"]*SR),float)
    for n,o,d,v in cell["tracks"]["bass"]["notes"]: add(out,bass(n,d,v)*cell["tracks"]["bass"]["gain"],o)
    for n,o,d,v,*_ in cell["tracks"]["piano"]["notes"]: add(out,piano(n,d,v)*cell["tracks"]["piano"]["gain"],o)
    for k,o,d,v,*r in cell["tracks"]["drum"]["hits"]: add(out,drum(k,d,v,int(r[-1] if r else 1)),o)
    for v in cell["voices"]: add(out,voice(v["vid"],v["txt"])*v["nrg"]*.35,v["onset"])
    pk=float(np.max(np.abs(out)))
    return out if pk<=.95 else out*(.95/pk)

phrase="王伯伯您好，五常社區共餐已經為您報名成功，今天中午見！"
cell={"schema":"w7tp-audio-scene-cell/2.3-candidate","sr":SR,"dur_s":DUR,
"tracks":{"bass":{"gain":.55,"notes":[[36,0,0.9,.85],[43,1,0.9,.80],[45,2,0.9,.85],[48,3,1.2,.90]]},
"piano":{"gain":.45,"notes":[[60,0,0.8,.75,-.4],[64,.5,.8,.75,.4],[67,1,.8,.80,-.4],[72,1.5,1.2,.85,.4]]},
"drum":{"hits":[["kick",0,.4,.9,.5,0,101],["hihat",.5,.2,.7,.4,.3,102],["snare",1,.3,.85,.45,.1,103],["hihat",1.5,.2,.7,.4,.3,104],["kick",2,.4,.9,.5,0,105]]}},
"voices":[{"vid":"F1","txt":phrase,"onset":.2,"rate":1.0,"nrg":.92}]}

cell_b=cjson(cell); (ROOT/"scene_cell.json").write_bytes(cell_b)
inst={"piano":wav_bytes(piano(60,1,.8)),"bass":wav_bytes(bass(36,1,.8)),"drum":wav_bytes(drum("kick",.6,.9,101))}
voices={k:wav_bytes(voice(k,phrase)) for k in ("M1","F1","F2")}
r1=wav_bytes(render(cell)); r2=wav_bytes(render(cell))
drift=json.loads(json.dumps(cell,ensure_ascii=False)); drift["tracks"]["piano"]["notes"][0][3]=.76
r3=wav_bytes(render(drift))
for name,b in {**{f"instrument_{k}.wav":v for k,v in inst.items()},**{f"voice_{k}.wav":v for k,v in voices.items()},"scene_r1.wav":r1,"scene_r2.wav":r2,"scene_drift.wav":r3}.items():
    (ROOT/name).write_bytes(b)
ev={"schema":"W7TP_AUDIO_ORIGIN_CELL_DETERMINISTIC_SCENE_CANDIDATE_V1","state":"PASS_CANDIDATE" if r1==r2 and r1!=r3 else "HOLD",
"scene_cell":{"serialized_bytes":len(cell_b),"zlib_bytes":len(zlib.compress(cell_b,9)),"sha256":h(cell_b)},
"instrument_sha256":{k:h(v) for k,v in inst.items()},"voice_sha256":{k:h(v) for k,v in voices.items()},
"reconstruction":{"same_cell_byte_exact":r1==r2,"r1_sha256":h(r1),"r2_sha256":h(r2),"one_parameter_drift_changes_output":r1!=r3,"drift_sha256":h(r3),"output_bytes":len(r1)},
"boundaries":{"three_instruments_rendered":True,"one_male_two_female_rendered":True,"emotion_effect_verified":False,"cosyvoice_used":False,"d8_authority":False,"deployment":False}}
(ROOT/"EVIDENCE.json").write_text(json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True))
print(json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True))
