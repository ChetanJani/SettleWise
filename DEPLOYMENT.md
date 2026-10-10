# SettleWise HCA deployment

Frontend: Netlify, project name `settlewisehca`.
Backend: Render Python web service. The source repository stays private.

## Render

The root `render.yaml` documents the web service settings:

- Root directory: `backend`
- Python: `3.12.8`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/api/health`
- Region: Singapore
- Plan: Free

Set these in Render's environment settings; never commit their secret values:

```dotenv
SERPAPI_API_KEY=your_existing_key
DATABASE_URL=your_existing_neon_postgres_url
SERPAPI_DAILY_LIMIT=100
CORS_ORIGINS=https://settlewisehca.netlify.app
PYTHON_VERSION=3.12.8
```

Neon stores properties and community data. Browser favourites and preferences
stay on the same browser without signup. Demo records do not populate live inventory.

The provider cache and daily attempt counter currently use instance-local SQLite.
Free Render services can lose these on restart/redeploy. The cap is per instance,
not an account-wide SerpApi spending guarantee. Keep one worker/instance; production
traffic needs a durable shared provider cache/budget before scaling.

## Netlify

The root `netlify.toml` builds `frontend` and publishes `dist` with an SPA fallback.
Set only the **public** backend origin as a Netlify build variable:

```dotenv
VITE_API_BASE_URL=https://YOUR_RENDER_SERVICE.onrender.com
```

Do not put SerpApi keys or database credentials in `VITE_` variables. Frontend API
requests go directly to Render, so long initial searches are not constrained by a
Netlify proxy timeout. Render CORS permits only the configured frontend origin.
Local Vite development continues to use its `/api` proxy with this variable empty.

## Updates

Push to `ChetanJani/SettleWise` first. If Render builds a private deployment copy in
your account, also push the same `main` branch there; do not force-push either repo.
Git-connected Render redeploys that copy automatically. For a manual Netlify deploy:

```powershell
cd frontend
$env:VITE_API_BASE_URL='https://YOUR_RENDER_SERVICE.onrender.com'
npm.cmd ci
npm.cmd run build
npx netlify-cli deploy --prod --dir dist --site YOUR_NETLIFY_SITE_ID --no-build
```

The latest manual frontend deploy must be repeated after frontend changes unless
Netlify continuous deployment has been connected to the deployment repository.

## Verify

- Render `/api/health`: HTTP 200; `database_ready` and `serpapi_configured` true.
- Netlify home loads, local demo photos load, Try demo shows all five stay types.
- Demo filtering, safety details and browser favourites work without SerpApi use.
- CORS permits Netlify and rejects unrelated origins.
- Live search remains separate from explicitly labelled fictional examples.

Free Render services can sleep when idle; open the site before the presentation
and let the backend wake. Cold-start time is not the normal search speed.
