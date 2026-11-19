import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// При локальной разработке запросы /api уходят на FastAPI (порт 8000).
// В Docker то же самое делает nginx (см. nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
