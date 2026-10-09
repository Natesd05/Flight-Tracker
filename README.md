# FlightPlanner

**A flight search that remembers you have class on Friday.**

The cheapest flight isn’t always the cheapest trip. A midday departure can mean missing a lab, paying for a bag, and spending another hour getting to the airport. FlightPlanner puts those tradeoffs next to the fare so you can decide whether the savings are worth it.

It’s a small React + FastAPI app with PostgreSQL underneath. The default setup uses repeatable sample flights; you don’t need an API key to try it. **Sample fares aren’t bookable.**

## What it does

- **Checks the whole time away.** Add your weekly classes, cancel an individual meeting, or add a one-off session. Conflicts include the stay and airport travel, not just the flights.
- **Keeps the extra costs visible.** Each result includes airfare plus your round-trip baggage and ground travel estimates. Lodging and meals are outside that total.
- **Lets you weigh the tradeoffs.** Rank by cost, missed class time, stops, travel windows, and travel time. Open “Why this flight” to see the details behind a score.
- **Separates preferences from requirements.** You can prefer fewer missed classes or rule them out entirely. If no flight meets your requirements, the app explains what excluded them.
- **Keeps a shortlist.** Save options and compare up to three side by side. Saved prices and scores stay as they were when you searched.

## Run it

With Docker and Compose installed:

```sh
cp .env.example .env
docker compose up --build
```

Open [localhost:5173](http://localhost:5173). The backend applies migrations and seeds a starter schedule automatically. The [API docs](http://localhost:8000/docs) are available locally too.

Create an account with your email and a password of at least 12 characters. Your schedule, preferences, searches, and saved flights are stored separately in PostgreSQL and restored when you log in again. Sessions last 30 days; logging out revokes the session.

New accounts start with one class Monday through Thursday, with Sunday displayed first. Mark a class optional to exclude it from flight conflicts. Click **One-time changes** to add or cancel a meeting.

In Preferences, **Use my location** shows straight-line distance to your home airport and recommends the nearest supported major airport. Location requires browser permission; coordinates stay in the tab. Save preferences to retain a chosen home airport.

To stop it:

```sh
docker compose down
```

The database volume is retained, so your changes are still there next time.

## A useful first trip

Start with the default ORD → LAX route, leaving next Friday and returning Sunday. The sample provider has six options with different fares, connections, and departure times.

1. Check **My schedule** and **Preferences**. Set a budget that includes your bag and airport transportation.
2. Run **Find my flights**. Open a result’s explanation and look at the classes affected.
3. Give class schedule more weight, then search again. Compare how the order changes.
4. Save a couple of options and open **Saved flights** to compare them.

Date ranges can cover up to four departure dates and four return dates. “Days away” counts elapsed hours from leaving home to getting back: a 48-hour trip is two days, regardless of how many calendar dates it touches.

## How the ranking works

The engine first removes flights that fail your requirements. It then scores the remaining flights from 0 to 100 using five weighted penalties. Higher scores mean a better fit with the priorities you chose.

The defaults put 35% on cost, 30% on class conflicts, 15% on travel time, and 10% each on stops and travel windows. These are explicit rules, not a trained recommendation model. A score is a way to compare tradeoffs; it isn’t a promise that a trip is right for you.

The [engineering notes](docs/engineering.md#recommendation-rules) cover the formula, timezone rules, interval boundaries, and tie-breaking. The ranking code lives in [backend/app/engine.py](backend/app/engine.py), separate from the API and database.

## A few boundaries

There’s no booking or payment flow. Baggage and ground costs are your estimates. The airport catalog is limited to 49 major airports, and transit time is based on your home airport setting; update it if you search from somewhere else.

An optional Duffel adapter feeds offers into the same ranking engine. Its HTTP contract has tests, but it hasn’t been verified with a credential-based request. Setup and provider limits are in the [Duffel notes](docs/engineering.md#optional-duffel-provider).

## Working on it

The frontend is React and TypeScript with plain CSS. FastAPI validates requests; PostgreSQL stores the schedule, preferences, searches, and saved evaluations. Alembic manages schema changes.

- [Development setup and test commands](docs/development.md)
- [Architecture, ranking rules, API, and configuration](docs/engineering.md)
- [Recorded verification and limitations](VERIFICATION.md)
- [Protected hosted-demo setup and deployment runbook](docs/deployment.md)

The backend tests cover ranking, timezones, providers, database behavior, account isolation, session expiry, and optional classes. The browser suite covers the planning flow, persistence, comparison limits, filters, and desktop/mobile layouts.

The selected **$0 hosted demo** uses Render Free and Neon Free, with sample
flights and no Duffel account or token. Follow [the free-demo setup](docs/free-demo.md).
The [portable Docker server runbook](docs/deployment.md) remains an alternative.
Public hosting has not yet been verified.

For the current project state and deployment handoff, see [docs/handoff.md](docs/handoff.md).
