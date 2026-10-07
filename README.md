# SettleWise

A React/Vite + FastAPI app for finding accommodation near a preferred area and comparing it against personal priorities. Ivory, deep green, responsive desktop/tablet/mobile design. No login or signup.

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

Leave those example values empty to use fictional Example mode and local SQLite. Do not overwrite an environment file you have already received. `.env` is intentionally ignored by Git, so each friend must add it separately.

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

## How the app was built and how it works

```mermaid
flowchart LR
  Browser[React UI in the browser] --> Proxy[Vite /api proxy]
  Proxy --> API[FastAPI: validation and ranking]
  API --> Provider[SerpApi: places, reviews, photos, routes]
  API --> DB[Neon: saves, quotes, community]
  Browser --> Tiles[OpenStreetMap tiles]
```

1. **React + Vite** builds the interface: search fields, optional preferences, result cards, map, saves, comparison and details. Styles use ivory and deep green and adapt to mobile, tablet and desktop.
2. **Vite proxies `/api` to FastAPI** on port 8001. The browser never needs the SerpApi key or database URL.
3. **FastAPI validates search/preferences** with Pydantic. When a worldwide suggestion is selected, the request carries its name, address and coordinates so the search uses the selected place.
4. **The provider adapter retrieves source data** from SerpApi, normalises fields, strips secret parameters from source links, caches repeated queries and limits concurrent upstream requests to three.
5. **The ranking module applies known requirements** and compares budget, commute, household space and documented security features. It returns reasons, trade-offs, missing facts and a best fit when enough evidence exists. Unknown facts are not invented.
6. **SQLAlchemy stores data in Neon**: property snapshots, browser-scoped saves and entered quotes, community observations and deduplicated helpful votes. Tables are created on backend startup.
7. **The frontend renders the results**. Additional place information loads when a detail section is opened. Leaflet uses OpenStreetMap tiles; there is no separate paid Google Maps key.

The current version uses a preferred-area field plus an optional work/college destination and a single property-type filter. The proposed single-field/multi-select redesign and persistent credit-saving cache are **not implemented in this commit**.

## SerpApi credit use — important for the team

For UI work, select **Example** in the header before typing or searching. Example mode uses fictional properties and routes; it does not call SerpApi. The backend unit tests also use mock provider responses and a temporary local database, so they do not consume live search credits or modify Neon.

Current possible upstream request counts **before cache hits**:

| Action | Requests it can trigger |
| --- | --- |
| Type a new prefix and pause | Two autocomplete lookups (nearby + worldwide), sometimes another city lookup |
| Search monthly accommodation | One Maps accommodation lookup and, for Any/Flat/House, one rental-link Google Search; an area lookup if no suggestion coordinates were selected |
| Change budget, household, bedrooms or amenities | Local filtering of existing candidates, except when commute prioritisation is also active |
| Change property type or hotel dates/guests | A new provider search |
| Prioritise/sort by commute or set a commute limit | Up to two directions per candidate, for up to six candidates |
| Open place details | Place information, photos, reviews; two directions if a destination is set |
| Open Around you | Up to seven nearby category searches; eight for a family including schools |
| Open Area & safety | One local-report Google Search |

These are possible provider requests, not a claim that every request is billed: repeated queries may hit the app or provider cache. The app cache is **memory-only and clears on backend restart**. Moving every detail onto every card would multiply requests, so do not automatically prefetch all properties while the shared budget is small. Use mocked tests for development and agree as a team before repeated live testing.

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
| SerpApi credits/rate limit reached | Switch to Example mode for development and check the shared account budget |
| Price/BHK not provided | This source did not provide those facts; add a provider quote or supply an actual inventory entry |

## User flow

1. Enter the area you want to live in and, optionally, your work/college destination. After three characters, suggestions combine nearby and worldwide places, with address/country context. Selecting a place uses its coordinates; it does not force the original city onto the new location.
2. View nearby accommodation immediately.
3. Apply budget, type, household, gender eligibility, commute, amenities, bedroom and priority preferences. Guided personalisation is optional.
4. Inspect photos, source links, known costs, reviews, two-direction commute estimates, nearby essentials and area evidence.
5. Save places for the current browser, compare 2–4 places, and contribute clearly labelled community observations.

## Data and honest limitations

**Live mode** uses real provider results. **Example mode** is explicitly fictional and never merged into real searches. Missing prices, room counts and rental terms remain unknown. A map-listed building is not proof of an available rental unit. External rental listing links are shown separately.

Maps does not provide a comprehensive rental inventory. Add a provider quote inside the property details panel to personalise comparisons using prices you know. These entered details are private to the browser identifier and marked unverified. Alternatively, supply actual owner listing data in `backend/inventory.json`, using the shape shown in `backend/inventory.example.json`.

Price matching excludes known prices above a strict budget. Unknown required facts appear under places needing confirmation. Flexible-budget options retain an explicit trade-off. Preference percentages describe a deterministic comparison among retrieved candidates, not a probability or safety rating. Commute prioritisation checks up to six candidates to bound search usage. Directions are estimates for the next weekday and selected India-time departure/return times; traffic can change.

Safety uses sourced leads, review context, building-feature information, community experiences and visit questions. It does not fabricate crime counts or women's safety percentages. Community posts are unverified and should not identify private people or share personal contact details.

No account is required. Saved places and entered quotes use a random browser identifier; clearing browser storage changes that identity. This is intended for local demonstration, not public production access. Public deployment would need proper identity controls, moderation, durable abuse protection and an approved property inventory source.

## SerpApi engines

| Engine | Purpose |
| --- | --- |
| Google Maps Search / Place | Area lookup, accommodation discovery, property/place information, nearby essentials |
| Google Maps Autocomplete | Location suggestions |
| Google Maps Directions | Home→destination and destination→home estimates |
| Google Maps Reviews | Recent review excerpts and transparent keyword topic counts |
| Google Maps Photos | Place photographs |
| Google Search | External rental leads and local report/advisory sources |
| Google Hotels + details | Date-specific hotel prices, images and information |

No Airbnb integration. Provider queries are cached in memory with bounded concurrency. Nearby services and area searches load when their tabs are opened. Cache resets on restart. Map tiles are OpenStreetMap with attribution and no bulk prefetch.

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
```

The implementation has passed 27 backend tests and a production frontend build. Browser checks exercised cards, filters, saves, comparison, details, Escape/back dismissal and layouts at 320, 375, 768 and 1440 pixels. Live checks connected to Neon and returned real places, images, reviews and both commute directions. Worldwide autocomplete checks returned Navrangpura, Navsari and locations in Spain for “nav”, plus Paris, Paraguay and Parma for “par”. Suggestions reflect provider coverage and relevance, not a complete list of every place. Provider results and available credits may change.
