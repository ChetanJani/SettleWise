# SettleWise — Product requirements

Updated 10 October 2026. Local prototype for a three-person hackathon team.

## Purpose

Help students, graduates, workers, families and travellers compare accommodation near a chosen place using their personal needs, sourced facts and clearly identified unknowns. No signup is required for local exploration, favourites or preferences. Booking and proof of vacancy are outside the MVP.

## Core flow

Enter **one location** → select one or more **PG, Hostel, Hotel, Flat, House** (All types supported) → find nearby places → refine the collected results → inspect popup details/map → save or compare.

The location can be an office, college, neighbourhood, station, hotel or another searchable place. Its selected coordinates are the reference for straight-line distance and requested routes. There is no second destination field or mandatory preference wizard.

## Functional requirements

| ID | Requirement | Implementation / constraint |
| --- | --- | --- |
| F01 | One worldwide location input | Suggestions after 2 characters and a 350 ms pause; address context and selected coordinates retained |
| F02 | Required multi-type selection | All types default; last selected type cannot be removed |
| F03 | Optional filters before/after search | One Filters control; monthly/nightly budgets, eligibility, people, BHK, radius, amenities, travel, photos and known-only |
| F04 | Zero-request local filtering | Browser ranks and filters candidate snapshots without provider or recommendation requests |
| F05 | Fast first results | Discovery cards render before bounded missing-photo enrichment; detail sections load explicitly |
| F06 | Rich, readable cards | Source image, name, type, price/unit, distance, rating, gender/BHK, amenities, evidence and concerns |
| F07 | PG/hostel eligibility | Male, Female, Both, Unknown; source-name inference requires user verification |
| F08 | Unknown prices | Not available; hotel rates without dates say Price needs dates; never invent rent |
| F09 | Source photographs | Gallery and cached more-photos action; honest missing/broken image fallback; no generated property photos |
| F10 | Popup details | Place, Reviews, Nearby, Travel, Safety; no mandatory navigation to a separate page |
| F11 | Visible map | Landing map, desktop side map and mobile/tablet Map control |
| F12 | Named map pins | Compact at low zoom, property names at zoom 15+; tooltip and click-to-open details |
| F13 | Safety evidence | Documentation coverage for CCTV, guard, controlled entry and lighting; unavailable without facts |
| F14 | Two-direction routes | Explicit user request, selected mode/times, context-sensitive cache; unknown is not zero |
| F15 | Nearby essentials | Combined search, sourced straight-line distances; optional schools; coverage is incomplete |
| F16 | Reviews/concerns | Source excerpts and low-rating warning; no unsupported incident assertions |
| F17 | Community experiences | Small card button opens a dedicated popup; unverified good/issues/serious reports, dates and deduplicated helpful votes |
| F18 | No-signup local persistence | Preferences, result snapshots, search cache, suggestions and favourites in browser storage |
| F19 | Compare | 2–4 places, comparable price units and loaded travel facts; no invented comparisons |
| F20 | Data/credit protection | Server-side credentials, persistent provider cache, concurrent deduplication and local daily cap |

Sorting supports best fit, distance, price, rating, travel time and safety evidence %. All five types are collected regardless of selection. Discovery targets 10 per type within 10 km, with broader queries for sparse types and internal coverage reports; shared listings are deduplicated. Unknown strict-filter facts remain labelled; the known-only setting can exclude them.

## Meaning of review safety and security evidence

Review sentiment = positive / classified safety-related English reviews × 100, with a minimum of three classified reviews. Positive, negative, mixed and unclear counts are explained inside the popup. Cards hide sample-shortfall text and category/result counts. General star ratings remain labelled Review score, separate from Safety score. Stars, unrelated texts and duplicate reviews are excluded. This is sampled sentiment, not personal safety probability. Dated Google News sources add context and never automatically change the percentage.


Percentage = documented boolean answers / four building checks × 100. A documented absent feature counts as an answer. Thus 100% means complete documentation, **not a safe property** or four present features. Ratings never become crime/women's-safety probabilities. The UI explanation and percentage label must preserve this distinction.

Women-oriented information includes lighting, last-mile access, entry controls, resident experiences and sourced local-report leads. Search/news links and community claims remain unverified. A validated area-risk model needs reliable geographic incident data and is future work.

## Design requirements

Ivory `#F7F8F4`, deep forest green `#145C45`, white cards, dark text `#14251E`, muted text `#69776F`, sage `#EDF4ED`, border `#E0E6DF`, restrained gold accent `#BC9762`.

Use Inter/Segoe UI/system typography, 16px base and mobile inputs, prominent property names/prices, generous spacing, quiet borders and minimal copy. Main loading uses animated line-drawn homes/skeletons, with reduced-motion support. Keyboard autocomplete, visible focus and accessible modal dismissal are required.

Desktop uses two-column cards with a side map; tablet/mobile offer an inline Map view. Avoid duplicate preference actions, forced steps and mandatory hotel dates.

## Architecture and API budget

React/Vite + Leaflet → FastAPI/Pydantic → SerpApi adapters; SQLAlchemy → Neon or local SQLite. The browser owns instant ranking. Browser storage keeps snapshots; a separate local SQLite cache persists provider responses.

Five category Maps queries per selected point, with bounded pagination and a broader search per sparse category (at most four requests per category); resolving unselected typed text can add one request. Autocomplete uses one request per uncached paused prefix. At most two missing-photo candidates are enriched after a fresh search. Additional sections are explicit and cached; there/back directions can cost two requests. Filtering, sorting, expanding a card and map zoom cost zero SerpApi requests.

Provider cache: generally 24 hours, photos/autocomplete 7 days; directions adapter uses a shorter TTL while its optional detail snapshot can persist 24 hours. Browser search cache: 24 hours. Source result dates remain visible. Local attempted-request cap: 30/day by default, configurable through `SERPAPI_DAILY_LIMIT`; it does not enforce a global shared-key budget.

Current engines: Google Maps Search/Place, Autocomplete, Photos, Reviews, Directions, and Google News for local reports. No Airbnb. Hotels are discoverable without dates, but automatic dated hotel-rate retrieval is not in this redesigned flow.

## Acceptance checks

- Exactly one location field and one Filters entry in the primary flow.
- Selected-coordinate discovery and property distance use the same point.
- Multi-type choices are retained; zero empty-type searches.
- Changing ordinary filters/sort emits no HTTP/provider searches.
- Concurrent identical provider queries consume one outbound request; cache survives restart; daily cap blocks excess attempts.
- Cards render before optional photo/detail work; opening a card alone does not fetch reviews/routes/nearby.
- Map names appear after zooming, pin selection expands its card, and filtering preserves map interaction.
- Male/Female/Both/Unknown labels and honest unavailable price/photo/evidence states exist.
- Reload restores preferences/results/favourites without automatically searching.
- Desktop and mobile layouts avoid horizontal page overflow; mobile inputs remain 16px.
- Frontend production build, backend mock tests and browser fixture checks pass without paid provider calls.

## Data constraints and deployment gaps

Maps is a bounded sample of places, not an authoritative rental/vacancy feed. Reliable prices, BHK, amenities, high-resolution photos and availability need owner/partner inventory. Nearby categories, source reviews and local news coverage can be incomplete. Area-wide average costs and verified crime counts are not implemented.

Browser identifiers are prototype scoping, not authentication. Public deployment needs protected anonymous sessions or appropriate identity controls, HTTPS/CORS configuration, production hosting, shared quota/rate controls, persistent cache hosting, migrations/backups, monitoring, moderation/reporting/removal, approved inventory/source use and map tile usage planning. Worldwide route timezone handling also needs expansion beyond the current India-time adapter.

## Team and demonstration

One member owns UI/map, one backend/cache/data, one QA/docs/demo. Demonstrate a graduate finding a PG near work, filtering instantly, inspecting a sourced photo, zooming for names, requesting one route and saving. Use Try demo for the labelled 50-stay presentation scenario or mocked fixtures for development. The frontend never silently replaces live failures with examples.

See [SettleWise-Project-Brief.txt](SettleWise-Project-Brief.txt) for the full shareable overview and [README.md](README.md) for setup.

## Explicit hackathon demo

Try demo opens 50 complete fictional stays, ten per category, with local illustrative stock images, synthetic safety reviews, simulated routes and nearby services. All provider requests are bypassed. Example observations/votes stay in browser storage; demo properties remain in backend memory and are excluded from real property persistence. Live search exits the scenario. See HACKATHON-DEMO.md for the presentation flow.
