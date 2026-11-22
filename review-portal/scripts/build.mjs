import { readFile, writeFile, mkdir } from "node:fs/promises";
const read = (path) => readFile(path, "utf8");
const [fixtures, server, template, css, client, mobilePage, mobileScript] = await Promise.all(
  [
    "src/fixtures.js",
    "worker/index.js",
    "src/index.html",
    "src/style.css",
    "src/client.js",
    "src/mobile.html",
    "src/mobile.js",
  ].map(read),
);
const embedded = [
  ["PAGE", template],
  ["STYLE", css],
  ["CLIENT", client],
  ["MOBILE_PAGE", mobilePage],
  ["MOBILE_SCRIPT", mobileScript],
].map(([key, value]) => "const " + key + " = " + JSON.stringify(value) + ";");
await mkdir("dist/drizzle", { recursive: true });
await writeFile(
  "dist/server/index.js",
  [fixtures, ...embedded, server].join("\n"),
);
