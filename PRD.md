# SettleWise — product requirements

## Purpose

Help people moving for work, education or family life find accommodation near their chosen area and understand practical trade-offs before contacting a provider.

## Primary experience

The first screen asks for a preferred living area and an optional work/college destination. Search produces results immediately. Users can then personalise without signing up or completing a mandatory questionnaire.

## Users

Graduates, professionals changing jobs or cities, solo renters, couples, families and friends sharing accommodation. Property types: flats, houses/bungalows, PGs, hostels and date-specific hotels.

## Functional requirements

| Requirement | Expected behavior |
| --- | --- |
| Location search | Nearby plus worldwide autocomplete after three characters, address/country context, selected coordinates used for search; keep destination optional |
| Cards | Name, type, available photo, source, price if supplied, rating context, known commute/area distance |
| Personalisation | Budget, strict/flexible policy, type, household count, PG/hostel eligibility, bedrooms, amenities, priorities |
| Travel | Mode, departure/return times, monthly travel days, optional maximum commute; show both directions |
| Recommendations | Deterministic preference fit with reasons, trade-offs and evidence coverage |
| Missing information | Unknown requirements cannot become confirmed matches; clearly separate candidates needing confirmation |
| Rental quotes | User can enter a monthly quote and known room/capacity details; scope it to their browser |
| Hotel results | Require stay dates and guest count; distinguish nightly price from total stay price |
| Details | Place photos, review excerpts/topics, known property facts and source links |
| Nearby | Grocery, pharmacy, hospital, public transport, petrol, railway, airport; schools for families |
| Costs | Known rent/maintenance/deposit, optional personal estimates; distinguish missing costs |
| Area and women's safety | Source leads, limitations, route/building visit questions, community observations |
| Community | Area/category/date/sentiment/text, unverified label, rate limit and duplicate-resistant helpful votes |
| Saved | Anonymous browser-scoped persistence in Neon, local device fallback |
| Compare | 2–4 properties with price units, known facts, commute and trade-offs |
| Responsive/accessibility | Mobile/tablet/desktop layouts, keyboard controls, labelled inputs, focus-contained dialogs and reduced motion |

## Architecture and dependencies

React/Vite frontend; FastAPI backend; SQLAlchemy/psycopg with Neon PostgreSQL; SerpApi provider adapters; Leaflet/OpenStreetMap. Environment secrets belong only in the backend. Search caches use bounded memory and concurrency. Independent provider failures should show unavailable information rather than invented replacements.

## Acceptance criteria

1. A location search works before preferences are completed.
2. Strict budgets do not include known overpriced listings as matches.
3. Unknown rent, occupancy, eligibility, amenities or required commute cannot silently pass those requirements.
4. Failed searches do not relabel old results as a new location.
5. Commute calculations use seconds/metres correctly and show unavailable routes explicitly.
6. Real and fictional properties never mix within one result set.
7. Saved places and private entered quotes remain scoped to a browser identifier.
8. Repeated helpful votes from one browser count once.
9. Credentials never appear in frontend assets, responses, or source links.
10. The app builds and critical screens work at 320, 375, 768 and 1440-pixel widths.

## Scope boundaries and next phase

The local MVP does not book properties, take payments, provide verified criminal statistics, certify safety or claim real-time rental availability. A production rental marketplace needs licensed/owner-verified inventory, quote verification, listing freshness, moderation and production identity/access controls. After that, add richer listing ingestion, neighbourhood infrastructure evidence, owner contact workflows and longer-term saved searches.
