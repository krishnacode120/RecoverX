import {readFileSync,writeFileSync} from "node:fs";
const path="apps/web/package.json";
const pkg=JSON.parse(readFileSync(path));
const lock=JSON.parse(readFileSync("apps/web/package-lock.json"));
for(const group of ["dependencies","devDependencies"])for(const name of Object.keys(pkg[group]))pkg[group][name]=lock.packages[`node_modules/${name}`].version;
writeFileSync(path,JSON.stringify(pkg,null,2)+"\n");
