// Fetch official PyPI wheels into a disposable project cache. pip still validates dependency resolution.
import { mkdir, writeFile, open, readFile, rename } from "node:fs/promises";
import { join } from "node:path";
const directory = "artifacts/wheels";
await mkdir(directory,{recursive:true});
const packages = ["pillow","pyside6-essentials","shiboken6","pytest","pluggy","iniconfig","packaging","pygments","colorama","ruff","setuptools","pip","pyinstaller","altgraph","pefile","pyinstaller-hooks-contrib","pywin32-ctypes","pybind11"];
const files=[];
const {createHash}=await import("node:crypto");
for(const name of packages){
  const response=await fetch(`https://pypi.org/pypi/${name}/json`);if(!response.ok)throw Error(`${name}: ${response.status}`);
  const info=await response.json();
  const wheels=info.urls.filter(x=>x.filename.endsWith(".whl"));
  const wheel=wheels.find(x=>/cp312-cp312-win_amd64/.test(x.filename))??wheels.find(x=>/cp3(9|10|11|12)-abi3-win_amd64/.test(x.filename))??wheels.find(x=>/py3-none-win_amd64/.test(x.filename))??wheels.find(x=>/py(2.py)?3-none-any/.test(x.filename));
  if(!wheel)throw Error(`No compatible wheel: ${name}`);
  const target=join(directory,wheel.filename);
  try{if(createHash("sha256").update(await readFile(target)).digest("hex")===wheel.digests.sha256){console.log(`${name}: cached and verified`);continue;}}catch{}
  files.push({...wheel,target});
}
const jobs=[];
for(const file of files){
 file.handle=await open(`${file.target}.part`,"w");
 for(let start=0;start<file.size;start+=262144)jobs.push({file,start,end:Math.min(start+262144,file.size)-1});
}
let cursor=0,done=0;
await Promise.all(Array.from({length:16},async()=>{
 while(cursor<jobs.length){const job=jobs[cursor++];
  for(let attempt=0;attempt<5;attempt++)try{
   const r=await fetch(job.file.url,{headers:{Range:`bytes=${job.start}-${job.end}`},signal:AbortSignal.timeout(90000)});
   if(r.status!==206)throw Error(`Range status ${r.status}`);
   const data=Buffer.from(await r.arrayBuffer());if(data.length!==job.end-job.start+1)throw Error("Short range");
   await job.file.handle.write(data,0,data.length,job.start);break;
  }catch(e){if(attempt===4)throw e;}
  if(++done%40===0)console.log(`Downloaded ranges ${done}/${jobs.length}`);
 }
}));
for(const file of files){await file.handle.close();const data=await readFile(`${file.target}.part`);if(createHash("sha256").update(data).digest("hex")!==file.digests.sha256)throw Error(`Hash mismatch: ${file.filename}`);await rename(`${file.target}.part`,file.target);console.log(`${file.filename} SHA-256 verified`);}
await writeFile(join(directory,"manifest.json"),JSON.stringify(files.map(({filename,digests})=>({filename,sha256:digests.sha256})),null,2));
