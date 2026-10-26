#!/usr/bin/env python3
"""Real semantic adapters; never substitutes file bytes for PCM/RGB/bone inputs.

MP4 -> AAC decode -> explicit 48 kHz stereo signed-16-bit PCM ->
existing analyze_audio_pcm / reconstruct_audio_pcm.
MP4 -> explicit 1 Hz 16x9 RGB feature grid -> per-coordinate integer time series ->
existing encode_temporal_series / decode_temporal_series.
VROID -> freshly observed VRoid Studio VRM export -> existing glTF skeleton scan ->
explicit millimetre coordinates -> existing analyze_3d_bone_tracks / reconstruction.

These are extracted-state roundtrips, NOT restoration of the compressed MP4,
the VROID editor project, unquantized PCM, or a live animation.
"""
from pathlib import Path
import argparse,array,ast,copy,datetime as dt,hashlib,json,struct,subprocess,sys,types
from decimal import Decimal,ROUND_HALF_EVEN

ROOT=Path('/home/taiji_admin/W7TP_SEMANTIC_ADAPTER_20261025')
EXPECTED={
 'universal_8d_file_engine.py':'3cef224bf5adb929f7f40c6f9a362bca543fcc66c0aedb5b14c6ed4008113fec',
 'gst_transceiver.py':'a27110275810088a4f1c105394a33aec13a4b2c8e49938b66dd7128ac243fdf2',
 'gltf_spatiotemporal_field.py':'38ddcdc90f7946f1b6d951c127aadfc929c305ab57186acf7883f29f1499cb8e'}
BLOCK=4096
AF=struct.Struct('>HQII32s')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def jb(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def readn(f,n):
 b=f.read(n)
 if len(b)!=n:raise ValueError('TRUNCATED_SEMANTIC_PACKET')
 return b
def load(name):
 p=ROOT/'source_refs'/name
 if sha(p)!=EXPECTED[name]:raise ValueError('SOURCE_ENGINE_DRIFT:'+name)
 tree=ast.parse(p.read_text());original=ast.dump(tree)
 expose={'reconstruct_audio_pcm':('samples','recon'),
         'reconstruct_3d_bone_tracks':('frames','recon'),
         'decode_temporal_series':('samples','recon')}
 class AddOutputs(ast.NodeTransformer):
  def visit_FunctionDef(self,n):
   self.generic_visit(n)
   if n.name in expose:
    key,var=expose[n.name]
    for ret in ast.walk(n):
     if isinstance(ret,ast.Return) and isinstance(ret.value,ast.Dict):
      ret.value.keys.append(ast.Constant(key))
      ret.value.values.append(ast.Name(id=var,ctx=ast.Load()))
   return n
 class StripOutputs(ast.NodeTransformer):
  def visit_FunctionDef(self,n):
   self.generic_visit(n)
   if n.name in expose:
    key,var=expose[n.name]
    for ret in ast.walk(n):
     if isinstance(ret,ast.Return) and isinstance(ret.value,ast.Dict):
      pairs=[(k,v) for k,v in zip(ret.value.keys,ret.value.values) if not(isinstance(k,ast.Constant) and k.value==key)]
      ret.value.keys=[k for k,v in pairs];ret.value.values=[v for k,v in pairs]
   return n
 modified=ast.fix_missing_locations(AddOutputs().visit(tree))
 if ast.dump(StripOutputs().visit(copy.deepcopy(modified)))!=original:raise ValueError('ALGORITHM_CHANGED')
 ns={'__name__':'bound_'+p.stem,'__file__':str(p)}
 exec(compile(modified,str(p),'exec'),ns)
 return types.SimpleNamespace(**ns)
def engine():return load('universal_8d_file_engine.py').Universal8DFileEngine
def temporal():return load('gst_transceiver.py').GSTBidirectionalTransceiver
def write_header(f,magic,h):
 b=jb(h);f.write(magic+struct.pack('>I',len(b))+b)
def read_header(f,magic):
 if readn(f,8)!=magic:raise ValueError('WRONG_SEMANTIC_PACKET_TYPE')
 n=struct.unpack('>I',readn(f,4))[0]
 if n>1048576:raise ValueError('HEADER_TOO_LARGE')
 return json.loads(readn(f,n))
def segments(values):
 """Only frame input to the existing int16 amplitude/delta contract; no clipping."""
 start=0;lo=hi=values[0]
 for i in range(1,len(values)):
  x=values[i];nlo=min(lo,x);nhi=max(hi,x)
  if i-start>=BLOCK or nhi-nlo>32767:
   yield start,values[start:i];start=i;lo=hi=x
  else:lo=nlo;hi=nhi
 yield start,values[start:]
def ffmpeg():
 import imageio_ffmpeg
 return imageio_ffmpeg.get_ffmpeg_exe()
def ff(args):
 p=subprocess.run([ffmpeg(),'-nostdin','-hide_banner','-loglevel','error','-threads','2',*map(str,args)],capture_output=True,text=True,timeout=600)
 if p.returncode:raise RuntimeError(p.stderr[-2000:])
def ints16be(b):
 a=array.array('h');a.frombytes(b)
 if sys.byteorder=='little':a.byteswap()
 return a
def pack16be(values):
 a=array.array('h',values)
 if sys.byteorder=='little':a.byteswap()
 return a.tobytes()

def audio_encode(pcm,packet,source_sha):
 E=engine();nbytes=pcm.stat().st_size
 if nbytes%4:raise ValueError('PCM_ALIGNMENT')
 h={'sample_rate_hz':48000,'channels':2,'sample_format':'s16be',
    'sample_count_per_channel':nbytes//4,'source_pcm_sha256':sha(pcm),
    'source_mp4_sha256':source_sha,'engine':EXPECTED['universal_8d_file_engine.py'],
    'native_input':'List[int] signed int16 amplitude, one channel at a time',
    'conversion':'AAC decoded and explicitly quantized to PCM16; not AAC byte reconstruction',
    'framing':'range-bounded segments preserve every sample; no clipping in adapter'}
 calls=0;cells=0;wire=0;global_sample=0
 with pcm.open('rb') as src,packet.open('xb') as dst:
  write_header(dst,b'AUDSEM01',h)
  while b:=src.read(BLOCK*4):
   interleaved=ints16be(b);count=len(interleaved)//2
   for ch in range(2):
    values=list(interleaved[ch::2])
    for start,part in segments(values):
     bundle=E.analyze_audio_pcm(part);calls+=1;cells+=len(bundle['packets'])
     body=b''.join(bundle['packets']);wire+=len(body)
     assert len(body)==18*len(bundle['packets'])
     dst.write(AF.pack(ch,global_sample+start,len(part),len(bundle['packets']),bytes.fromhex(bundle['source_sha256'])))
     dst.write(body)
   global_sample+=count
   if global_sample%480000==0:print('AUDIO analyzed per channel:',global_sample,flush=True)
 return {'native_analyzer_calls':calls,'native_cells':cells,'native_cell_bytes':wire,**h}

def audio_decode(packet,out):
 E=engine();counts=[0,0];temp=[out.with_suffix('.ch0'),out.with_suffix('.ch1')]
 streams=[p.open('xb') for p in temp]
 try:
  with packet.open('rb') as f:
   h=read_header(f,b'AUDSEM01')
   if h['engine']!=EXPECTED['universal_8d_file_engine.py']:raise ValueError('ENGINE_BINDING')
   while head:=f.read(AF.size):
    if len(head)!=AF.size:raise ValueError('AUDIO_FRAME_TRUNCATED')
    ch,offset,n,cells,digest=AF.unpack(head)
    if ch>=2 or offset!=counts[ch] or not(1<=n<=BLOCK) or cells>n:raise ValueError('AUDIO_COORDINATE_MISMATCH')
    raw=readn(f,cells*18);packets=[raw[i:i+18] for i in range(0,len(raw),18)]
    result=E.reconstruct_audio_pcm({'total_samples':n,'packets':packets,'source_sha256':digest.hex()})
    if not result['byte_exact']:raise ValueError('NATIVE_AUDIO_RECONSTRUCTION_FAILED')
    streams[ch].write(pack16be(result['samples']));counts[ch]+=n
  if counts!=[h['sample_count_per_channel']]*2:raise ValueError('AUDIO_SAMPLE_COUNT')
 finally:
  for s in streams:s.close()
 with temp[0].open('rb') as left,temp[1].open('rb') as right,out.open('xb') as dst:
  while b0:=left.read(BLOCK*2):
   b1=right.read(len(b0))
   if len(b1)!=len(b0):raise ValueError('CHANNEL_LENGTH_MISMATCH')
   x=ints16be(b0);y=ints16be(b1);merged=[v for pair in zip(x,y) for v in pair]
   dst.write(pack16be(merged))
 if sha(out)!=h['source_pcm_sha256']:raise ValueError('FULL_PCM_SHA256_MISMATCH')
 for p in temp:p.unlink()
 return {'decoded_samples_per_channel':counts,'pcm_sha256':sha(out),'pcm_bytes':out.stat().st_size,'roundtrip_exact':True}

def visual_encode(rgb,packet,source_sha,width=16,height=9,fps=1):
 T=temporal();raw=rgb.read_bytes();stride=width*height*3
 if len(raw)%stride:raise ValueError('RGB_ALIGNMENT')
 frames=len(raw)//stride
 h={'width':width,'height':height,'channels':['R','G','B'],'sample_format':'rgb24',
    'output_feature_fps':[fps,1],'frame_count':frames,
    'coordinate_rule':'track=(y*width+x)*3+channel; time=frame_index/fps',
    'feature_definition':'FFmpeg area-scaled RGB grid; reduced visual features, not full-resolution frames',
    'source_rgb_sha256':sha(rgb),'source_mp4_sha256':source_sha,
    'engine':EXPECTED['gst_transceiver.py'],'native_input':'integer temporal series per fixed pixel/channel'}
 native_bytes=0
 with packet.open('xb') as dst:
  write_header(dst,b'VISSEM01',h)
  for track in range(stride):
   values=list(raw[track::stride]);p=T.encode_temporal_series(values);native_bytes+=len(p)
   dst.write(struct.pack('>II',track,len(p)));dst.write(p)
 return {'native_analyzer_calls':stride,'native_cell_bytes':native_bytes,**h}
def visual_decode(packet,out):
 T=temporal()
 with packet.open('rb') as f:
  h=read_header(f,b'VISSEM01');stride=h['width']*h['height']*3
  if h['engine']!=EXPECTED['gst_transceiver.py']:raise ValueError('ENGINE_BINDING')
  data=bytearray(stride*h['frame_count'])
  for expected in range(stride):
   track,n=struct.unpack('>II',readn(f,8))
   if track!=expected or n>49+24*h['frame_count']:raise ValueError('VISUAL_TRACK_BOUNDS')
   p=readn(f,n);result=T.decode_temporal_series(p)
   if not result['byte_exact'] or len(result['samples'])!=h['frame_count']:raise ValueError('NATIVE_VISUAL_RECONSTRUCTION_FAILED')
   for frame,value in enumerate(result['samples']):
    if not 0<=value<=255:raise ValueError('RGB_VALUE_RANGE')
    data[frame*stride+track]=value
  if f.read(1):raise ValueError('TRAILING_VISUAL_PACKET')
 out.write_bytes(data)
 if sha(out)!=h['source_rgb_sha256']:raise ValueError('FULL_FEATURE_SHA256_MISMATCH')
 return {'rgb_bytes':len(data),'rgb_sha256':sha(out),'roundtrip_exact':True}

def run_mp4(source,out,seconds=None):
 out.mkdir(parents=True,exist_ok=False);original=sha(source)
 trim=['-t',str(seconds)] if seconds else []
 pcm=out/'source_audio.s16be'
 print('EXTRACT AUDIO: true AAC -> stereo 48 kHz PCM16',flush=True)
 ff(['-i',source,*trim,'-map','0:a:0','-vn','-ac','2','-ar','48000','-c:a','pcm_s16be','-f','s16be',pcm])
 audio=audio_encode(pcm,out/'audio_native_cells.bin',original)
 audio.update(audio_decode(out/'audio_native_cells.bin',out/'reconstructed_audio.s16be'))
 audio['packet_file_bytes']=(out/'audio_native_cells.bin').stat().st_size
 print('AUDIO native contract roundtrip PASS; samples/channel=',audio['sample_count_per_channel'],flush=True)
 rgb=out/'source_visual_features.rgb'
 print('EXTRACT VISUAL: true video -> timestamped 16x9 RGB grid at 1 Hz',flush=True)
 ff(['-i',source,*trim,'-map','0:v:0','-an','-vf','fps=1:start_time=0,scale=16:9:flags=area,format=rgb24','-fps_mode','passthrough','-f','rawvideo',rgb])
 visual=visual_encode(rgb,out/'visual_native_cells.bin',original)
 visual.update(visual_decode(out/'visual_native_cells.bin',out/'reconstructed_visual_features.rgb'))
 visual['packet_file_bytes']=(out/'visual_native_cells.bin').stat().st_size
 print('VISUAL native contract roundtrip PASS; frames=',visual['frame_count'],flush=True)
 if sha(source)!=original:raise ValueError('SOURCE_MP4_CHANGED')
 report={'state':'PASS_EXTRACTED_SEMANTIC_STATE_ROUNDTRIP','source_mp4':str(source),
  'source_sha256':original,'source_unchanged':True,'clip_seconds_limit':seconds,
  'audio':audio,'visual':visual,'opaque_file_fallback_used':False,'original_mp4_reconstructed':False,
  'formal_d8_authority':False,'observed_at':dt.datetime.now(dt.timezone.utc).isoformat()}
 (out/'mp4_semantic_receipt.json').write_bytes(jb(report))
 print(json.dumps({k:report[k] for k in ['state','source_sha256','source_unchanged','opaque_file_fallback_used']},ensure_ascii=False),flush=True)
 return report

def bone_decode(header_path,packet_path,out):
 E=engine();h=json.loads(header_path.read_bytes());raw=packet_path.read_bytes()
 if len(raw)!=h['bone_cells']*22:raise ValueError('BONE_PACKET_LENGTH_MISMATCH')
 h['packets']=[raw[i:i+22] for i in range(0,len(raw),22)]
 result=E.reconstruct_3d_bone_tracks(h)
 if not result['byte_exact']:raise ValueError('NATIVE_BONE_RECONSTRUCTION_FAILED')
 out.write_bytes(pack16be(v for frame in result['frames'] for xyz in frame for v in xyz))
 if sha(out)!=h['source_sha256']:raise ValueError('FULL_BONE_COORDINATE_SHA256_MISMATCH')
 return {'reconstructed_coordinate_sha256':sha(out),'coordinate_bytes':out.stat().st_size,
         'roundtrip_exact_for_quantized_coordinates':True}

def run_bones(vroid,vrm,export_receipt,out):
 out.mkdir(parents=True,exist_ok=False);vroid_sha=sha(vroid);vrm_sha=sha(vrm);proof=json.loads(export_receipt.read_bytes())
 if proof.get('source_vroid_sha256')!=vroid_sha or proof.get('exported_vrm_sha256')!=vrm_sha or proof.get('fresh_export_observed') is not True:
  raise ValueError('EXACT_VROID_EXPORT_PROVENANCE_REQUIRED')
 G=load('gltf_spatiotemporal_field.py');E=engine();scan=G.scan_gltf_skeletons(vrm)
 if scan['source_sha256']!=vrm_sha or not scan['skins']:raise ValueError('NO_SOURCE_SKELETON')
 joints={}
 for skin in scan['skins']:
  for joint in skin['joint_bind_positions']:
   if joint['node'] in joints and joints[joint['node']]!=joint:raise ValueError('JOINT_ID_CONFLICT')
   joints[joint['node']]=joint
 ordered=[joints[k] for k in sorted(joints)]
 frame=[];max_error=Decimal(0)
 for joint in ordered:
  xyz=[]
  for value in joint['world_bind_xyz']:
   exact=Decimal.from_float(value)*Decimal(1000)
   q=int(exact.to_integral_value(rounding=ROUND_HALF_EVEN))
   if not -32768<=q<=32767:raise ValueError('MILLIMETRE_COORDINATE_EXCEEDS_NATIVE_INT16')
   max_error=max(max_error,abs(exact-Decimal(q)));xyz.append(q)
  frame.append(tuple(xyz))
 frames=[frame]
 bundle=E.analyze_3d_bone_tracks(frames)
 header={k:v for k,v in bundle.items() if k!='packets'}
 (out/'bone_native_header.json').write_bytes(jb(header))
 (out/'bone_native_cells.bin').write_bytes(b''.join(bundle['packets']))
 (out/'source_joint_coordinates.s16be').write_bytes(pack16be(v for xyz in frame for v in xyz))
 decoded=bone_decode(out/'bone_native_header.json',out/'bone_native_cells.bin',out/'reconstructed_joint_coordinates.s16be')
 if sha(out/'source_joint_coordinates.s16be')!=decoded['reconstructed_coordinate_sha256']:
  raise ValueError('SOURCE_AND_RECONSTRUCTED_BONE_COORDINATES_DIFFER')
 (out/'joint_bind_coordinates.json').write_bytes(jb({'ordered_joints':ordered,'frames_mm':frames,
   'units':'millimetres','scale_per_metre':1000,'rounding':'half_even','static_bind_pose_frames':1}))
 report={'state':'PASS_REAL_VROID_EXPORTED_BIND_POSE','source_vroid_sha256':vroid_sha,
  'exported_vrm_sha256':vrm_sha,'joint_count':len(frame),'frame_count':1,
  'native_input_contract':'List[List[Tuple[int,int,int]]] signed int16 world XYZ in declared millimetres',
  'native_method':'analyze_3d_bone_tracks / reconstruct_3d_bone_tracks',
  'roundtrip_exact_for_quantized_coordinates':True,'max_quantization_error_mm':str(max_error),
  'native_cell_bytes':sum(len(p) for p in bundle['packets']),
  'unquantized_float_pose_byte_exact_claimed':False,'fabricated_motion_frames':False,
  'opaque_file_fallback_used':False,'source_unchanged':sha(vroid)==vroid_sha,
  'decoder_reads_saved_native_packets_only':True,**decoded}
 (out/'bone_semantic_receipt.json').write_bytes(jb(report));print(json.dumps(report,ensure_ascii=False),flush=True)
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 m=sub.add_parser('mp4');m.add_argument('source',type=Path);m.add_argument('output',type=Path);m.add_argument('--seconds',type=int)
 b=sub.add_parser('bones');b.add_argument('vroid',type=Path);b.add_argument('vrm',type=Path);b.add_argument('export_receipt',type=Path);b.add_argument('output',type=Path)
 a=p.parse_args()
 if a.command=='mp4':run_mp4(a.source,a.output,a.seconds)
 else:run_bones(a.vroid,a.vrm,a.export_receipt,a.output)

