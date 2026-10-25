#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, subprocess, wave, zlib
from pathlib import Path
import numpy as np
from scipy import signal

SR=24000
VOICE_BASES={"M1":Path("/tmp/m1.wav"),"F1":Path("/tmp/f1.wav"),"F2":Path("/tmp/f2.wav")}
LUT={
 "lut_version":"w7tp.8dadi.audio-emotion-lut/2.3-candidate",
 "profiles":{
  "warm_care":{"rate":0.94,"pitch_st":-0.5,"gain":0.90,"lowpass_hz":5200,"pause_ms":240},
  "excited_joy":{"rate":1.12,"pitch_st":2.0,"gain":1.08,"lowpass_hz":7200,"pause_ms":90},
  "urgent_attentive":{"rate":1.06,"pitch_st":1.0,"gain":1.00,"lowpass_hz":6500,"pause_ms":80},
  "cinema_blend":{"rate":0.90,"pitch_st":-1.0,"gain":0.92,"lowpass_hz":4800,"pause_ms":300}
 }
}
def cjson(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def read_wav_bytes(data):
    with wave.open(io.BytesIO(data),"rb") as wf:
        sr=wf.getframerate(); ch=wf.getnchannels(); sw=wf.getsampwidth(); raw=wf.readframes(wf.getnframes())
    if sw!=2: raise RuntimeError("WAV_NOT_S16")
    x=np.frombuffer(raw,dtype=np.int16).astype(np.float64)/32768.0
    if ch>1: x=x.reshape(-1,ch).mean(axis=1)
    if sr!=SR: x=signal.resample(x,max(1,int(round(len(x)*SR/sr))))
    return x
def wav_bytes(x):
    bio=io.BytesIO(); pcm=(np.clip(x,-1,1)*32767).astype(np.int16)
    with wave.open(bio,"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())
    return bio.getvalue()
def pcm_s16le_from_wav_bytes(data):
    with wave.open(io.BytesIO(data),"rb") as wf:
        if wf.getsampwidth()!=2 or wf.getnchannels()!=1 or wf.getframerate()!=SR:
            raise RuntimeError("PLAYBACK_FORMAT_MISMATCH")
        return wf.readframes(wf.getnframes())
def play_wav_bytes(data):
    raw=pcm_s16le_from_wav_bytes(data)
    subprocess.run(["paplay","--raw","--format=s16le",f"--rate={SR}","--channels=1"],input=raw,check=True)
def rate_change(x,f): return signal.resample(x,max(1,int(round(len(x)/f))))
def pitch_keep_dur(x,st):
    if abs(st)<1e-9:return x.copy()
    r=2.0**(st/12.0); y=signal.resample(x,max(1,int(round(len(x)/r))))
    return signal.resample(y,len(x))
def apply_profile(x,p):
    y=pitch_keep_dur(rate_change(x,float(p["rate"])),float(p["pitch_st"]))
    lp=min(float(p["lowpass_hz"]),SR/2-200)
    y=signal.sosfilt(signal.butter(4,lp,btype="low",fs=SR,output="sos"),y)*float(p["gain"])
    pk=float(np.max(np.abs(y))) if len(y) else 0.0
    return y if pk<=.97 else y*(.97/pk)
def midi_hz(n): return 440*(2**((n-69)/12))
def env(n,d):
    t=np.arange(n)/SR; return np.minimum(1,t/.01)*np.exp(-d*t)
def piano(n,d,v):
    m=int(d*SR); t=np.arange(m)/SR; f=midi_hz(n)
    return (np.sin(2*np.pi*f*t)+.35*np.sin(4*np.pi*f*t))*env(m,2.5)*v*.35
def bass(n,d,v):
    m=int(d*SR); t=np.arange(m)/SR; f=midi_hz(n)
    return (np.sin(2*np.pi*f*t)+.2*np.sin(4*np.pi*f*t))*env(m,1.8)*v*.45
def drum(kind,d,v,seed):
    m=int(d*SR); t=np.arange(m)/SR; r=np.random.default_rng(seed)
    if kind=="kick":
        f=48+70*np.exp(-t*20); y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*11)
    elif kind=="snare": y=(.8*r.standard_normal(m)+.2*np.sin(2*np.pi*190*t))*np.exp(-t*14)
    else:
        q=r.standard_normal(m); y=np.r_[0,np.diff(q)]*np.exp(-t*25)
    return y/max(float(np.max(np.abs(y))),1e-9)*v*.35
def add(dst,src,o):
    s=int(o*SR); e=min(len(dst),s+len(src))
    if e>s: dst[s:e]+=src[:e-s]
def load_voice_material():
    out={}
    for k,p in VOICE_BASES.items():
        b=p.read_bytes(); out[k]={"bytes":b,"sha256":sha(b),"size":len(b)}
    return out
def build_scene(voice_sha):
    return {"schema":"w7tp-audio-origin-cell/2.3-candidate","lut_version":LUT["lut_version"],
      "voice_base_sha256":voice_sha,"voice_id":"F1","emotion_code":"warm_care","voice_gain":.72,"voice_onset":.15,"dur_s":5.0,
      "piano":[[60,0,.8,.72],[64,.5,.8,.70],[67,1,.8,.72],[72,1.5,1.1,.76]],
      "bass":[[36,0,.9,.75],[43,1,.9,.72],[45,2,.9,.75],[48,3,1.2,.78]],
      "drum":[["kick",0,.35,.85,101],["hihat",.5,.18,.60,102],["snare",1,.28,.80,103],["hihat",1.5,.18,.60,104],["kick",2,.35,.85,105]]}
def render_scene(cell,materials):
    out=np.zeros(int(cell["dur_s"]*SR),dtype=np.float64)
    for n,o,d,v in cell["piano"]:add(out,piano(n,d,v),o)
    for n,o,d,v in cell["bass"]:add(out,bass(n,d,v),o)
    for k,o,d,v,s in cell["drum"]:add(out,drum(k,d,v,s),o)
    base=read_wav_bytes(materials[cell["voice_id"]]["bytes"])
    add(out,apply_profile(base,LUT["profiles"][cell["emotion_code"]])*float(cell["voice_gain"]),float(cell["voice_onset"]))
    pk=float(np.max(np.abs(out)))
    if pk>.95:out*=.95/pk
    return wav_bytes(out)
def run(play=False):
    mats=load_voice_material(); lut_b=cjson(LUT)
    scene=build_scene(mats["F1"]["sha256"]); cell_b=cjson(scene)
    r1=render_scene(scene,mats); r2=render_scene(scene,mats)
    drift=json.loads(json.dumps(scene)); drift["emotion_code"]="excited_joy"; r3=render_scene(drift,mats)
    emotion={}
    f1=read_wav_bytes(mats["F1"]["bytes"])
    for name,p in LUT["profiles"].items():
        b=wav_bytes(apply_profile(f1,p)); emotion[name]={"bytes":len(b),"sha256":sha(b)}
    renderer_sha=sha(Path(__file__).read_bytes())
    base_descriptor={"renderer_sha256":renderer_sha,"lut_sha256":sha(lut_b),"voice_material_sha256":{k:v["sha256"] for k,v in mats.items()},"sr":SR}
    base_sha=sha(cjson(base_descriptor))
    ev={"schema":"W7TP_AUDIO_ZERO_DISK_ORIGIN_CELL_EVIDENCE_V1","state":"PASS_CANDIDATE" if r1==r2 and r1!=r3 else "HOLD",
      "scene_cell":{"serialized_bytes":len(cell_b),"zlib_bytes":len(zlib.compress(cell_b,9)),"sha256":sha(cell_b)},
      "lut":{"sha256":sha(lut_b),"version":LUT["lut_version"]},
      "base_descriptor":base_descriptor,"base_cache_sha256":base_sha,
      "voice_material":{k:{"bytes":v["size"],"sha256":v["sha256"]} for k,v in mats.items()},
      "emotion_outputs":emotion,
      "reconstruction":{"r1_sha256":sha(r1),"r2_sha256":sha(r2),"byte_exact_same_cell":r1==r2,"drift_sha256":sha(r3),"emotion_code_drift_changes_output":r1!=r3,"output_bytes":len(r1)},
      "zero_disk_io":{"wav_outputs_written":0,"output_wav_paths":[],"hash_computed_from_ram":True,"playback_from_ram_supported":True},
      "boundaries":{"voice_base_material_is_preexisting_file_input":True,"output_audio_zero_disk":True,"effect_authorization":False,"deployment":False}}
    if play: play_wav_bytes(r1)
    return ev
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--play",action="store_true"); a=ap.parse_args()
    print(json.dumps(run(play=a.play),ensure_ascii=False,indent=2,sort_keys=True))
