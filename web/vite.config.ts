import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api requests are proxied to the FastAPI server, so the browser never hits CORS issues.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
