# SettleWise frontend

The complete teammate setup guide is in [the root README](../README.md).

This frontend uses React, Vite, Leaflet and Lucide icons. It runs at http://127.0.0.1:5174 and proxies `/api` to FastAPI at http://127.0.0.1:8001.

From this folder:

```bash
npm ci
npm run dev
```

The backend must also be running. Place the privately shared environment file at `backend/.env` in the repository root's backend folder, never in this frontend folder.

```bash
npm run build
npm run lint
```

Application entry: `src/main.jsx` → `src/SettleWise.jsx`. Responsive styling: `src/styles.css`. The older Vite starter assets/components are unused by that entry point.
