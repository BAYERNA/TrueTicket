import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [{
    name: "bundled-license-notices",
    apply: "build",
    generateBundle() {
      const notices = {
        react: "react/LICENSE", "react-dom": "react-dom/LICENSE",
        scheduler: "scheduler/LICENSE", vite: "vite/LICENSE.md",
      };
      for (const [name, source] of Object.entries(notices)) {
        const file = new URL(`./node_modules/${source}`, import.meta.url);
        this.emitFile({ type: "asset", fileName: `licenses/${name}.txt`, source: readFileSync(file, "utf8") });
      }
    },
  }],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
