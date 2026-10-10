# SettleWise demo

Start the services and open http://127.0.0.1:5174. Click **Try demo** in the header. It resets filters and shows the Navrangpura scenario with **50 fictional stays: 10 PGs, 10 hostels, 10 hotels, 10 flats and 10 houses**. **Live search** exits the demo. No automatic fallback silently substitutes examples for real search results.

The demo uses stored stock photographs to illustrate the fictional stays. Prices, reviews, nearby businesses, eligibility, building features, map positions and travel estimates are demonstration scenarios, not verified listings. Keep the visible Demo/Example labels during the presentation.

## A short presentation flow

1. Say: “Imagine a graduate moving near a new office. This labelled scenario shows the product; live search uses SerpApi.”
2. Select PG and Hostel, then open Filters. Try a monthly budget of ₹12,000 and Female eligibility. Apply them to show immediate filtering without provider searches.
3. Open Safety on a card. Show the positive/negative review examples and building features. Explain that the percentage describes safety-related review sentiment, not a probability of personal safety.
4. Open Nearby to show transport, groceries, pharmacy, hospital and fuel station. Family filters also include a school scenario.
5. Compare two PGs to show the price and commute trade-off. Save one and reload to demonstrate browser persistence.
6. Open Local experiences. Read the fictional observations, add an example observation and mark one helpful. Example contributions stay in browser storage and never enter the real community database.
7. Return to All types and zoom the map to see property names. The gallery uses three illustrative scenes per property.
8. Use Live search when demonstrating provider integration. Live searches still depend on credits, source coverage, network and database availability.

## What works without paid APIs

Demo search, all detail sections, simulated routes, filters, sorting, comparison, favourites, photo galleries and example community interactions. Provider usage does not increase. Demo properties remain in backend memory; the browser retains the search snapshot. Restarting the backend may require clicking Try demo again before loading an uncached detail section. Map background tiles use OpenStreetMap and still need a network connection; local cards and photographs do not need image hosting.

The default demo includes varied budgets, male/female/mixed eligibility, studio through four-bedroom homes, single/shared rooms, different security features, both positive and negative safety scenarios, monthly deposits and separate nightly hotel pricing. Filters can naturally reduce a category below ten.

Photo origin URLs and filenames are recorded in `frontend/public/demo-photos/credits.json`. The photos illustrate room/exterior styles and are not evidence about these fictional property names.
