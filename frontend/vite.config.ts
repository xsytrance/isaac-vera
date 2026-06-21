import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy the API to the prime-as-brain server so the SPA can call
// /facts, /report and /ask same-origin (no CORS needed). Override the target
// with VITE_API (e.g. your tailnet prime) when running `npm run dev`.
const API = process.env.VITE_API || "http://localhost:8765";

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    proxy: {
      "/facts": API,
      "/report": API,
      "/ask": { target: API, changeOrigin: true },
      "/healthz": API,
    },
  },
});
