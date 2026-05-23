import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  root: process.cwd(),
  plugins: [react()],
  resolve: {
    preserveSymlinks: true
  },
  build: {
    rollupOptions: {
      input: path.join(process.cwd(), "index.html")
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
