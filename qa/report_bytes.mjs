import { createHash } from "node:crypto";
import worker from "../review-portal/dist/server/index.js";
const results={};
for(const id of ["SP-FEST","SP-MUS","SP-BASE"]){
  const response=await worker.fetch(new Request("https://invalid.example/reports/"+id+".txt"),{});
  if(response.status!==200 || !response.headers.get("Content-Disposition")?.includes("attachment")) throw Error(id);
  const data=Buffer.from(await response.arrayBuffer());
  results[id]={bytes:data.length,sha256:createHash("sha256").update(data).digest("hex")};
}
console.log(JSON.stringify(results,null,2));
