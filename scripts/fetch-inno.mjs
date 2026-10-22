// Development compiler cache from NuGet; validate its Authenticode signer before execution.
import {writeFile} from "node:fs/promises";
const url="https://api.nuget.org/v3-flatcontainer/tools.innosetup/6.7.3/tools.innosetup.6.7.3.nupkg";
const response=await fetch(url);if(!response.ok)throw Error(`Download failed: ${response.status}`);
await writeFile("artifacts/inno-tools.zip",Buffer.from(await response.arrayBuffer()));
console.log("Downloaded compiler package to artifacts/inno-tools.zip. Verify publisher signature before running.");
