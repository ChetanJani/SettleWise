# SettleWise

A React/Vite + FastAPI app for finding accommodation near a preferred area and comparing it against personal priorities. Ivory, deep green, responsive desktop/tablet/mobile design. No login or signup.

Hosting setup and update commands: [DEPLOYMENT.md](DEPLOYMENT.md). Hackathon walkthrough: [HACKATHON-DEMO.md](HACKATHON-DEMO.md).

## Teammate setup — start here

You need **Git**, **Python 3.12** (tested with 3.12.10), and **Node.js 22.12+ or 24** with npm (tested with Node 24.16.0). Vite also supports Node 20.19+, but use the recommended versions for consistency. Accept the GitHub collaborator invitation before cloning this private repository.

### 1. Get the project

Open PowerShell in the folder where you keep projects:

```powershell
git clone https://github.com/ChetanJani/SettleWise.git
cd SettleWise
```

If GitHub asks you to sign in, use your own GitHub account with access to this repository. GitHub CLI users can run `gh auth login` first and then `gh repo clone ChetanJani/SettleWise`.

### 2. Add the privately shared environment file

Put the `.env` file received from your teammate at **`SettleWise/backend/.env`**. Its filename must be exactly `.env`, not `.env.txt`. Nothing belongs in a frontend environment file for the SerpApi or Neon credentials.

The shared file should contain `SERPAPI_API_KEY` and `DATABASE_URL`; see the placeholder example below. If you have not received it yet, you can create a local demo configuration:

```powershell
Copy-Item backend\.env.example backend\.env
```

Leave those values empty for local SQLite; live search requires a valid SerpApi key. The explicit Try demo button opens the fictional presentation scenario. It does not consume provider credits or automatically replace a failed live search. Do not overwrite an environment file you have already received. `.env` is intentionally ignored by Git, so each friend must add it separately.

### 3. Install and start

From the cloned project directory:

```powershell
.\setup.ps1
.\start.ps1
```

If PowerShell blocks local scripts, run these instead:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Open **http://127.0.0.1:5174**. FastAPI documentation: **http://127.0.0.1:8001/docs**. Give the backend a few seconds to connect to the database. Stop both services with `.\stop.ps1`, or `powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1`. Ports are 5174/8001. Logs and recorded process IDs are in `.local/`.

`setup.ps1` creates a local Python virtual environment, installs backend packages, and installs the exact frontend dependency versions from `package-lock.json` with `npm ci`. `start.ps1` launches both services in the background. `stop.ps1` checks the recorded process start times and stops this app's service processes and their children.

### Manual start / macOS / Linux

The helper scripts are for Windows. You can also run the two services yourself in separate terminals.

**Backend — Windows:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**Backend — macOS/Linux:**

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**Frontend — second terminal, from the repository root:**

```bash
cd frontend
npm ci
npm run dev
```

Use Ctrl+C in each terminal to stop manually started services. The automatic stop script only controls processes launched by the automatic start script.

## Credentials

`backend/.env` is loaded directly and excluded from version control. Restart the backend after changing it. Never add real keys or connection strings to commits, screenshots, issues or README text.

```dotenv
SERPAPI_API_KEY="your_serpapi_key"
DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

The same SerpApi key works across the configured SerpApi engines, subject to your account credits and provider availability. No Google API key is required for the Leaflet map. Neon credentials are separate. All provider requests and database operations happen on the backend; keys are not sent to React.

A configured Neon connection failure stays visible; the app does not secretly switch to SQLite. SQLite is used only when `DATABASE_URL` is absent, for local development.

Teammates using the same SerpApi key share the same remaining credits. Teammates using the same Neon URL share property/community storage; saved places and rental quotes are separated by browser identifier, not by signed-in accounts.

## How it works

1. Enter **one location**: office, college, area, station, hotel or another place. Worldwide suggestions include address context and coordinates.
2. Choose **PG, Hostel, Hotel, Flat, House**, or All types. Optional filters remain available through one Filters button.
3. FastAPI resolves the point if needed, queries all five accommodation types, even when only one is selected, and returns cached candidate snapshots within 10 km by default, sorted nearest first. It targets 10 per type, reuses farther results already returned, and expands sparse categories with a broader Maps query and bounded pagination. Maps coverage is a sample, not a complete rental inventory.
4. React renders source thumbnails and uses `rankLocal` to filter/sort the dataset. Budget, eligibility, BHK, amenities and sorting send **no API requests**.
5. Details open in a popup. A separate small Local experiences button opens community observations in its own popup. Reviews, photos, nearby services, place facts and routes are cached; opening Safety loads sampled reviews on demand. At most two missing-photo places receive background photo enrichment after a fresh search.
6. Leaflet/OSM maps appear on the landing page and beside desktop results. Mobile has a Map toggle. At zoom 15+, pins show property names; clicking selects and expands the matching card.
7. Browser storage restores preferences, results and saved places without automatically searching. Source data can become stale; the result date remains visible.
8. SQLAlchemy stores source snapshots, quotes and community data in Neon; local SQLite is used only when no database URL is configured. Browser-scoped quotes remain unverified.

Vite proxies `/api` to FastAPI on port 8001. Provider credentials stay on the backend.

## SerpApi request budget

| Action, before cache hits | Provider requests |
| --- | --- |
| Uncached autocomplete prefix, 2+ characters and 350 ms pause | 1 |
| Search after selecting a suggestion with coordinates | 5 category queries; sparse types can add pagination and one broader query (maximum 4 requests/type) |
| Search without coordinates | Up to 1 resolution + the category queries above |
| Background enrichment of missing photos | At most 2 additional photo requests |
| Filters, sorting, opening Details/Local experiences, local saves, map zoom | 0 |
| Explicit photos, reviews, place facts, nearby services or local reports | Usually 1 per action |
| Explicit travel there/back | Up to 2 directions requests |

One user search can require several requests; SerpApi does not return all detail endpoints in one response. All five types are collected in the same discovery batch and cached. Changing type selections does not start a search. Real coverage varies: the 10-per-type target cannot be guaranteed where the source returns fewer places. Shared PG/hostel listings appear once in All types. The UI omits collection counts. A tighter distance or budget filter can reduce the displayed set below the collection target.

`backend/data/search-cache.sqlite3` persists successful provider responses across restarts. Queries normally cache for 24 hours; photos/autocomplete for 7 days. Directions use a shorter provider TTL and detail snapshots can remain cached for 24 hours. Identical in-flight queries share a lock. Browser searches cache for 24 hours; local result snapshots persist until replaced. Detail requests are reused per property/context.

The local daily attempted-request limit defaults to **30**. Set `SERPAPI_DAILY_LIMIT=30` in `backend/.env`; `/api/usage` exposes the local count. This is **not** the SerpApi account billing counter and does not count other teammates or backend instances using the same key. A configured shared daily budget is future deployment work.

Use Try demo, intercepted fixtures or the backend demo endpoint for development. Mock backend tests use temporary SQLite and do not spend credits or modify Neon.

## Working together and getting updates

Start each change on your own branch, then push it and open a pull request for a teammate to review:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/your-change
# edit files and run the checks below
git add README.md frontend/src backend/app
git diff --cached --stat
git commit -m "Describe your change"
git push -u origin feature/your-change
```

Stage any other intentional files by name. Avoid committing runtime folders, real environment files or logs. The root `.gitignore` excludes these, while `backend/.env.example` provides only empty placeholders.

To update a clean local checkout:

```powershell
.\stop.ps1
git switch main
git pull --ff-only origin main
.\setup.ps1
.\start.ps1
```

If you have uncommitted work, commit it on your feature branch before switching. There is no need to re-send `.env` unless the credentials change.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| GitHub says repository not found | Accept the invitation and sign into the GitHub account that has access |
| `python` or `npm` not found | Install the runtimes above, reopen the terminal, check `python --version` and `node --version` |
| Vite reports an unsupported Node version | Use Node 22.12+ or 24, then run setup again |
| Port 5174/8001 is in use | Stop your existing SettleWise instance; if started manually, stop it in its own terminal |
| Backend unavailable | Check `.local/backend-error.log`; for the automatic start script, run stop and start again |
| Live search needs a key | Confirm the received file is exactly `backend/.env`, then restart the backend |
| Database storage unavailable | Check the Neon URL/SSL parameters and database/network availability; a configured Neon failure does not switch to SQLite |
| SerpApi credits/rate limit reached | Use mocked fixtures for development and check the shared account budget |
| Price/BHK not provided | This source did not provide those facts; add a provider quote or supply an actual inventory entry |

## Data and limitations

Cards show actual source images when available, price/unit, selected-point straight-line distance, rating, known amenities, PG eligibility and safety evidence. Unknown monthly price says **Not available**. Hotels can be discovered without dates; an unknown rate says **Price needs dates**. There is no current automatic dated Google Hotels pricing query and no Airbnb integration.

Maps is not a comprehensive rental/vacancy feed. For reliable rent/BHK/details, supply an actual owner inventory (`backend/inventory.example.json`) or enter a private provider quote inside the card. Missing source data remains unknown. Photos are prioritised but cannot be guaranteed when sources provide none; source pictures may differ from the available unit.

**Review safety sentiment %** uses positive / classified safety-related English review texts, with at least three classified reviews. The Safety popup explains the positive, negative and mixed counts. Cards omit sample-shortfall text. Overall ratings can appear as a separate Review score fallback; ratings are never renamed as safety. Unknown stays unknown; star ratings are excluded. This is sample sentiment, not a personal safety probability. Google News links provide dated context and do not change the percentage.

**Security evidence % is documentation coverage**: documented boolean answers for CCTV, guard, controlled entry and lighting, divided by four. A documented absent feature also counts as an answer. Without documented facts the percentage is unavailable. Ratings never become women's safety percentages. Local-report links are leads, and community posts/helpful votes are unverified. A validated area crime-risk model needs trustworthy geographic incident data and is outside this prototype.

Live and fictional Example data stay distinct. The header’s Try demo button opens 50 fictional stays, ten per type; Live search exits. Local stock scenes, simulated routes and populated detail popups need no provider calls. Example community posts/votes stay in browser storage. See [HACKATHON-DEMO.md](HACKATHON-DEMO.md) for the presentation flow. Travel estimates load explicitly; the current adapter uses next-weekday India-time departure/return times. Traffic estimates are not guarantees and worldwide timezone handling is future work.

Browser storage keeps favourites/preferences/results on the same device without signup. Clearing storage or using another browser loses that identity. The API's browser identifier is not authentication. Public deployment requires protected anonymous sessions or proper identity controls, moderation, shared rate/spend limits and durable cache hosting.

## SerpApi engines used by the current flow

| Engine | Purpose |
| --- | --- |
| Google Maps Search / Place | Location resolution, discovery, place facts, combined nearby search |
| Google Maps Autocomplete | Worldwide location suggestions |
| Google Maps Photos | Actual place photographs |
| Google Maps Reviews | Recent source excerpts |
| Google Maps Directions | Explicit there/back estimates |
| Google News | Dated, sourced local safety/news leads in the Safety popup |

One SerpApi key covers these engines subject to account availability and limits. Leaflet uses attributed OpenStreetMap tiles, not a separate paid Google Maps key. Provider results are bounded; not all categories or requested fields will be present.

## Project structure

```text
backend/app/             FastAPI routes, provider adapters, ranking, persistence
backend/tests/           Backend validation, ranking, persistence and adapter tests
frontend/src/            React screens, components and responsive styles
backend/.env             Your private credentials (not committed)
start.ps1 / stop.ps1     Local service controls
PRD.md                   Product requirements and acceptance criteria
```

Tables created in Neon are prefixed `sw_`: properties, saved places, observations, helpful votes and private rental inputs. Existing unrelated database tables are not replaced.

## Verify

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\frontend
npm.cmd run build
npm.cmd test
```

The redesigned backend passed **35 mocked tests**, including one-request discovery/autocomplete, concurrent deduplication, persistent cache reuse, quota enforcement, no-provider filtering, private quotes and conservative eligibility parsing. Six browser-ranking unit tests and the frontend production build passed. Browser fixture checks verified one location/Filters control, worldwide suggestions, names on zoomed map pins, inline details, zero-request filtering, reload persistence, source image rendering and a 390px layout without horizontal overflow. These checks use no live SerpApi credits. They do not establish complete live inventory coverage.

See **SettleWise-Project-Brief.txt** for the shareable plain-text overview and **PRD.md** for requirements and deployment gaps.
