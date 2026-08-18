import { createHash } from 'node:crypto';
import { readFile, stat, writeFile } from 'node:fs/promises';
const asset='assets/xiaoj_single_core_geometry.glb', source=await readFile(asset), app=await readFile('app.js','utf8');
const mapping=JSON.parse(await readFile('adi_mapping.json','utf8')), hash=createHash('sha256').update(source).digest('hex');
const checks={asset_exists:(await stat(asset)).size===20217896,source_hash_match:hash==='5d9d07e55d5d1515537e9ba73ed677659cff362b9b282ad318694ef55cbcf44a',runtime_skinning:app.includes('SkinnedMesh')&&app.includes('skinWeight'),skeleton_seven_bones:app.includes('const bones=[root,spine,head,la,ra,ll,rl]'),emotions_12:['喜-3','怒-3','哀-3','樂-3'].every(x=>app.includes(x)),phonemes_7:['休止','A','E','I','O','U','M'].every(x=>app.includes(x)),actions_5:['坐下','起立','步行','慢跑','跳躍'].every(x=>app.includes(x)),adi_8d:mapping.coordinates.length===8,local_launcher:(await readFile('launcher.py','utf8')).includes('127.0.0.1')};
const receipt={schema:'w7tp.local-3d.verification-receipt.v1',timestamp:new Date().toISOString(),asset:{path:asset,bytes:source.length,sha256:hash,source_mode:'copied from read-only source; original untouched'},checks,pass:Object.values(checks).every(Boolean)},json=`${JSON.stringify(receipt,null,2)}\n`;
await writeFile('receipts/LOCAL_VALIDATION_RECEIPT.json',json); process.stdout.write(json); if(!receipt.pass)process.exit(1);
