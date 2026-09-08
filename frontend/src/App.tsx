import { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  CalendarDays,
  Check,
  Compass,
  GraduationCap,
  LayoutDashboard,
  LoaderCircle,
  Plane,
  Plus,
  Search,
  Settings2,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import { api } from "./api";
import type {
  Airport,
  Preferences,
  Schedule,
  SearchResult,
  Saved,
  Query,
  ClassItem,
  ExceptionItem,
  Weights,
} from "./types";
import {
  AirportSelect,
  Field,
  FlightCard,
  WeightEditor,
  money,
  duration,
  dateLabel,
} from "./components";

const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const baseWeights: Weights = {
  cost: 35,
  conflicts: 30,
  layovers: 10,
  windows: 10,
  travel: 15,
};
function nextFriday() {
  const d = new Date();
  d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7 || 7));
  return d;
}
function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
const first = nextFriday(),
  last = new Date(first);
last.setDate(last.getDate() + 2);
const initialQuery: Query = {
  origin: "ORD",
  destination: "LAX",
  departure_from: iso(first),
  departure_to: iso(first),
  return_from: iso(last),
  return_to: iso(last),
  min_trip_days: 1,
  max_trip_days: 4,
  hard_budget: true,
  hard_conflicts: false,
  hard_windows: false,
  max_stops: null,
  weights: baseWeights,
  departure_start: "08:00",
  departure_end: "21:00",
  arrival_start: "07:00",
  arrival_end: "23:00",
};
const emptyClass = {
  title: "",
  weekday: 0,
  start_time: "09:00",
  end_time: "10:15",
};
const navigation = [
  { id: "search", label: "Find flights", icon: Compass },
  { id: "schedule", label: "My schedule", icon: CalendarDays },
  { id: "saved", label: "Saved flights", icon: Bookmark },
  { id: "preferences", label: "Preferences", icon: Settings2 },
] as const;
type Page = (typeof navigation)[number]["id"];

export default function App() {
  const [page, setPage] = useState<Page>("search");
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [draftPrefs, setDraftPrefs] = useState<Preferences | null>(null);
  const [schedule, setSchedule] = useState<Schedule>({
    classes: [],
    exceptions: [],
  });
  const [airports, setAirports] = useState<Airport[]>([]);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [query, setQuery] = useState<Query>(initialQuery);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [history, setHistory] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [provider, setProvider] = useState("mock");
  const [classDraft, setClassDraft] = useState(emptyClass);
  const [editClass, setEditClass] = useState<number | null>(null);
  const [exception, setException] = useState({
    kind: "cancel" as "cancel" | "add",
    date: iso(first),
    class_id: "",
    title: "",
    start_time: "09:00",
    end_time: "10:00",
  });
  const [compare, setCompare] = useState<number[]>([]);
  const [sort, setSort] = useState("score");
  const [onlyClear, setOnlyClear] = useState(false);
  const [filterCost, setFilterCost] = useState("");
  const [filterStops, setFilterStops] = useState("");
  const [filterTravel, setFilterTravel] = useState("");
  const [stale, setStale] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [p, s, a, v, h, health] = await Promise.all([
        api<Preferences>("/preferences"),
        api<Schedule>("/schedule"),
        api<Airport[]>("/airports"),
        api<Saved[]>("/saved"),
        api<SearchResult[]>("/searches"),
        api<{ provider: string }>("/health"),
      ]);
      setPrefs(p);
      setDraftPrefs(p);
      setSchedule(s);
      setAirports(a);
      setSaved(v);
      setHistory(h);
      setProvider(health.provider);
      setQuery((q) => ({
        ...q,
        origin: p.home_airport,
        weights: p.weights,
        departure_start: p.departure_start.slice(0, 5),
        departure_end: p.departure_end.slice(0, 5),
        arrival_start: p.arrival_start.slice(0, 5),
        arrival_end: p.arrival_end.slice(0, 5),
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function action(work: () => Promise<void>, success: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      setNotice(success);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function updateQuery<K extends keyof Query>(key: K, value: Query[K]) {
    setQuery((q) => ({ ...q, [key]: value }));
    setStale(true);
  }
  async function searchFlights() {
    setSearching(true);
    setError("");
    setNotice("");
    try {
      const r = await api<SearchResult>("/searches", "POST", query);
      setResult(r);
      setHistory((h) => [r, ...h].slice(0, 10));
      setStale(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSearching(false);
    }
  }
  async function saveFlight(id: string) {
    if (!result) return;
    await action(async () => {
      await api("/saved", "POST", { search_id: result.id, itinerary_id: id });
      setSaved(await api<Saved[]>("/saved"));
    }, "Flight saved. Find it in Saved flights.");
  }
  async function refreshSchedule() {
    setSchedule(await api<Schedule>("/schedule"));
    setStale(true);
  }
  function classSubmit() {
    void action(
      async () => {
        await api(
          editClass ? `/classes/${editClass}` : "/classes",
          editClass ? "PUT" : "POST",
          classDraft,
        );
        await refreshSchedule();
        setClassDraft(emptyClass);
        setEditClass(null);
      },
      editClass ? "Class updated." : "Class added to your week.",
    );
  }
  function edit(c: ClassItem) {
    setEditClass(c.id);
    setClassDraft({
      title: c.title,
      weekday: c.weekday,
      start_time: c.start_time.slice(0, 5),
      end_time: c.end_time.slice(0, 5),
    });
  }
  const visible = (result?.results || [])
    .filter(
      (e) =>
        (!onlyClear || !e.conflicts.length) &&
        (!filterCost || e.cost.total <= +filterCost) &&
        (!filterStops || e.stops <= +filterStops) &&
        (!filterTravel || e.travel_minutes <= +filterTravel * 60),
    )
    .sort((a, b) =>
      sort === "cost"
        ? a.cost.total - b.cost.total
        : sort === "travel"
          ? a.travel_minutes - b.travel_minutes
          : sort === "conflicts"
            ? a.conflict_minutes - b.conflict_minutes
            : sort === "stops"
              ? a.stops - b.stops
              : b.score - a.score,
    );
  const chosen = saved.filter((s) => compare.includes(s.id));
  const mock = provider === "mock";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setPage("search");
          }}
        >
          <span className="brand-icon">
            <Plane size={24} />
          </span>
          <span>
            Student Flight<span className="brand-sub">P L A N N E R</span>
          </span>
        </a>
        <div className="workspace-label">YOUR TRAVEL NOTEBOOK</div>
        <nav aria-label="Main navigation">
          {navigation.map((n, index) => (
            <button
              key={n.id}
              className={page === n.id ? "nav-item active" : "nav-item"}
              aria-current={page === n.id ? "page" : undefined}
              onClick={() => {
                setPage(n.id);
                setNotice("");
              }}
            >
              <n.icon size={19} />
              <span className="nav-number" aria-hidden="true">
                0{index + 1}
              </span>
              {n.label}
              {n.id === "saved" && saved.length > 0 && (
                <span className="count">{saved.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <GraduationCap size={25} />
          <strong>
            A little less planning.
            <br />A little more going.
          </strong>
          <p>Your classes and budget come along for the ride.</p>
        </div>
        <div className="profile">
          <span className="avatar">
            {prefs?.name
              .split(" ")
              .map((n) => n[0])
              .slice(0, 2)
              .join("") || "AM"}
          </span>
          <div>
            <strong>{prefs?.name || "Demo student"}</strong>
            <small>Student · Demo profile</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            <LayoutDashboard size={15} /> My notebook{" "}
            <span className="slash">/</span>{" "}
            <strong>{navigation.find((n) => n.id === page)?.label}</strong>
          </span>
          <span className="demo-pill">
            <i />
            {mock ? "Demo flight data" : "Duffel provider"}
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div className="eyebrow">
              {page === "search"
                ? "FIELD NOTES / A LITTLE FURTHER FROM CAMPUS"
                : "FIELD NOTES / THE LITTLE DETAILS"}
            </div>
            <div className="heading-row">
              <div>
                <h1>
                  {page === "search" ? (
                    <>
                      Good flights.{" "}
                      <span className="ink-underline">Better timing.</span>
                    </>
                  ) : page === "schedule" ? (
                    "Your week, accounted for."
                  ) : page === "saved" ? (
                    "A shortlist worth saving."
                  ) : (
                    "Travel on your terms."
                  )}
                </h1>
                <p>
                  {page === "search"
                    ? "Find a trip that fits your life between lectures."
                    : page === "schedule"
                      ? `Classes and exceptions are evaluated in ${prefs?.timezone || "your timezone"}.`
                      : page === "saved"
                        ? "Compare up to three flights and see what works best for you."
                        : "Set your starting point, budget, and what matters most."}
                </p>
              </div>
              <div className="trip-note" aria-hidden="true">
                <svg viewBox="0 0 115 45" fill="none">
                  <path d="M4 9C28 35 57 3 67 17S47 43 37 28 86 13 109 35M94 33l16 3-5-15" />
                </svg>
                leave room for a little adventure
              </div>
            </div>
          </div>
          {error && (
            <div className="message error" role="alert">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={18} />
              </button>
            </div>
          )}
          {notice && (
            <div className="message success" role="status">
              <Check size={18} />
              {notice}
            </div>
          )}
          {loading ? (
            <div className="empty">
              <LoaderCircle className="spin" />
              <h2>Getting your planner ready…</h2>
            </div>
          ) : !prefs ? (
            <div className="empty">
              <h2>Let’s get connected</h2>
              <p>Start the backend and database, then reload your planner.</p>
              <button className="button primary" onClick={() => void load()}>
                Retry connection
              </button>
            </div>
          ) : (
            <>
              {page === "search" && (
                <>
                  <div className="stats">
                    <div>
                      <span className="stat-icon">
                        <CalendarDays size={20} />
                      </span>
                      <span>
                        <small>Your weekly schedule</small>
                        <strong>
                          {schedule.classes.length} classes <em>in the plan</em>
                        </strong>
                      </span>
                      <button
                        aria-label="Edit schedule"
                        onClick={() => setPage("schedule")}
                      >
                        <ArrowUpRight size={18} />
                      </button>
                    </div>
                    <div>
                      <span className="stat-icon">
                        <span>$</span>
                      </span>
                      <span>
                        <small>Trip budget</small>
                        <strong>
                          {money(prefs.budget)} <em>including extras</em>
                        </strong>
                      </span>
                      <button
                        aria-label="Edit budget"
                        onClick={() => setPage("preferences")}
                      >
                        <ArrowUpRight size={18} />
                      </button>
                    </div>
                    <div>
                      <span className="stat-icon">
                        <Plane size={20} />
                      </span>
                      <span>
                        <small>Your home airport</small>
                        <strong>
                          {prefs.home_airport}{" "}
                          <em>{prefs.transit_minutes} min from campus</em>
                        </strong>
                      </span>
                      <button
                        aria-label="Edit home airport"
                        onClick={() => setPage("preferences")}
                      >
                        <ArrowUpRight size={18} />
                      </button>
                    </div>
                  </div>
                  <div className="planner-grid">
                    <aside className="search-column">
                      <form
                        className="panel search-panel"
                        onSubmit={(e) => {
                          e.preventDefault();
                          void searchFlights();
                        }}
                      >
                        <div className="section-title">
                          <h2>Where are we going?</h2>
                          <Plane size={20} />
                        </div>
                        <AirportSelect
                          label="Flying from"
                          value={query.origin}
                          onChange={(v) => updateQuery("origin", v)}
                          airports={airports}
                        />
                        <AirportSelect
                          label="Flying to"
                          value={query.destination}
                          onChange={(v) => updateQuery("destination", v)}
                          airports={airports}
                        />
                        <div className="field-grid">
                          <Field label="Depart from">
                            <input
                              type="date"
                              required
                              value={query.departure_from}
                              onChange={(e) => {
                                const v = e.target.value;
                                setQuery((q) => ({
                                  ...q,
                                  departure_from: v,
                                  departure_to:
                                    v > q.departure_to ? v : q.departure_to,
                                }));
                                setStale(true);
                              }}
                            />
                          </Field>
                          <Field label="Depart by">
                            <input
                              type="date"
                              required
                              min={query.departure_from}
                              value={query.departure_to}
                              onChange={(e) =>
                                updateQuery("departure_to", e.target.value)
                              }
                            />
                          </Field>
                          <Field label="Return from">
                            <input
                              type="date"
                              required
                              min={query.departure_from}
                              value={query.return_from}
                              onChange={(e) => {
                                const v = e.target.value;
                                setQuery((q) => ({
                                  ...q,
                                  return_from: v,
                                  return_to: v > q.return_to ? v : q.return_to,
                                }));
                                setStale(true);
                              }}
                            />
                          </Field>
                          <Field label="Return by">
                            <input
                              type="date"
                              required
                              min={query.return_from}
                              value={query.return_to}
                              onChange={(e) =>
                                updateQuery("return_to", e.target.value)
                              }
                            />
                          </Field>
                        </div>
                        <small className="helper">
                          Explore up to 4 departure and 4 return dates.
                        </small>
                        <div className="field-grid">
                          <Field label="Min days away">
                            <input
                              type="number"
                              min="0"
                              max="30"
                              step="0.5"
                              value={query.min_trip_days}
                              onChange={(e) =>
                                updateQuery("min_trip_days", +e.target.value)
                              }
                              required
                            />
                          </Field>
                          <Field label="Max days away">
                            <input
                              type="number"
                              min="0.5"
                              max="30"
                              step="0.5"
                              value={query.max_trip_days}
                              onChange={(e) =>
                                updateQuery("max_trip_days", +e.target.value)
                              }
                              required
                            />
                          </Field>
                        </div>
                        <p className="helper">
                          Days away = elapsed time from leaving home to
                          returning home, divided by 24 hours.
                        </p>
                        <details className="advanced">
                          <summary>
                            <SlidersHorizontal size={16} /> Constraints & travel
                            windows
                          </summary>
                          <div className="checks">
                            {(
                              [
                                [
                                  "hard_budget",
                                  `Stay within ${money(prefs.budget)} budget`,
                                ],
                                ["hard_conflicts", "No missed classes"],
                                ["hard_windows", "Enforce travel windows"],
                              ] as const
                            ).map(([k, label]) => (
                              <label key={k}>
                                <input
                                  type="checkbox"
                                  checked={query[k]}
                                  onChange={(e) =>
                                    updateQuery(k, e.target.checked)
                                  }
                                />
                                {label}
                              </label>
                            ))}
                          </div>
                          <Field label="Maximum stops per direction">
                            <select
                              value={query.max_stops ?? ""}
                              onChange={(e) =>
                                updateQuery(
                                  "max_stops",
                                  e.target.value === ""
                                    ? null
                                    : +e.target.value,
                                )
                              }
                            >
                              <option value="">Any</option>
                              <option value="0">Nonstop</option>
                              <option value="1">1 stop</option>
                              <option value="2">2 stops</option>
                            </select>
                          </Field>
                          <TimeWindows
                            value={query}
                            onChange={(k, v) => updateQuery(k, v)}
                          />
                        </details>
                        <button
                          className="button primary search-button"
                          disabled={
                            searching ||
                            !Object.values(query.weights).some(Boolean)
                          }
                        >
                          {searching ? (
                            <LoaderCircle size={18} className="spin" />
                          ) : (
                            <Search size={18} />
                          )}
                          {searching ? "Finding your fit…" : "Find my flights"}
                          <ArrowRight size={17} />
                        </button>
                      </form>
                      <section className="panel priorities">
                        <div className="section-title">
                          <h2>Your priorities</h2>
                          <Settings2 size={18} />
                        </div>
                        <p className="helper">
                          Move the sliders, then search to update your ranking.
                        </p>
                        <WeightEditor
                          weights={query.weights}
                          onChange={(v) => updateQuery("weights", v)}
                        />
                      </section>
                    </aside>
                    <section className="results" aria-busy={searching}>
                      <div className="results-heading">
                        <div>
                          <h2>
                            {result
                              ? `${result.results.length} flights that fit`
                              : "Your next trip starts here"}
                          </h2>
                          <p>
                            {result
                              ? `${result.evaluated_count} options evaluated · ${result.provider === "mock" ? "Sample fares, not bookable" : result.provider}`
                              : "Your schedule. Your budget. A better way to get away."}
                          </p>
                        </div>
                        {result && (
                          <label className="sort">
                            Sort by
                            <select
                              aria-label="Sort flights"
                              value={sort}
                              onChange={(e) => setSort(e.target.value)}
                            >
                              <option value="score">Best fit</option>
                              <option value="cost">Lowest cost</option>
                              <option value="conflicts">
                                Fewest conflicts
                              </option>
                              <option value="stops">Fewest stops</option>
                              <option value="travel">Shortest travel</option>
                            </select>
                          </label>
                        )}
                      </div>
                      <div className="context-note">
                        <GraduationCap size={20} />
                        <span>
                          <strong>Built around your student life.</strong>{" "}
                          Rankings account for classes, airport travel, and the
                          time you’re away.
                        </span>
                      </div>
                      {result && (
                        <>
                          <div className="filters">
                            <label className="check-chip">
                              <input
                                type="checkbox"
                                checked={onlyClear}
                                onChange={(e) => setOnlyClear(e.target.checked)}
                              />
                              No class conflicts
                            </label>
                            <input
                              aria-label="Filter maximum total cost"
                              type="number"
                              min="0"
                              placeholder="Max cost ($)"
                              value={filterCost}
                              onChange={(e) => setFilterCost(e.target.value)}
                            />
                            <select
                              aria-label="Filter total stops"
                              value={filterStops}
                              onChange={(e) => setFilterStops(e.target.value)}
                            >
                              <option value="">Any stops</option>
                              <option value="0">Nonstop</option>
                              <option value="2">≤ 2 total stops</option>
                            </select>
                            <input
                              aria-label="Filter maximum travel hours"
                              type="number"
                              min="0"
                              placeholder="Max travel (h)"
                              value={filterTravel}
                              onChange={(e) => setFilterTravel(e.target.value)}
                            />
                          </div>
                          {stale && (
                            <div className="message warning">
                              Your inputs have changed. Search again to update
                              these results.
                            </div>
                          )}
                          {Object.keys(result.rejected).length > 0 && (
                            <p className="helper">
                              Excluded by hard constraints:{" "}
                              {Object.entries(result.rejected)
                                .map(([k, v]) => `${k} (${v})`)
                                .join(" · ")}
                              . An option may fail multiple constraints.
                            </p>
                          )}
                        </>
                      )}
                      {searching ? (
                        <div className="empty">
                          <LoaderCircle className="spin" size={30} />
                          <h3>Checking the whole trip…</h3>
                          <p>
                            Comparing fares, class conflicts, and travel time.
                          </p>
                        </div>
                      ) : result ? (
                        visible.length ? (
                          <div className="flight-list">
                            {visible.map((e) => (
                              <FlightCard
                                key={e.itinerary.id}
                                item={e}
                                rank={
                                  result.results.findIndex(
                                    (r) => r.itinerary.id === e.itinerary.id,
                                  ) + 1
                                }
                                saved={saved.some(
                                  (s) =>
                                    s.search_id === result.id &&
                                    s.itinerary_id === e.itinerary.id,
                                )}
                                pending={busy}
                                onSave={() => void saveFlight(e.itinerary.id)}
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="empty">
                            <Search size={32} />
                            <h3>
                              {result.results.length
                                ? "No matches for these filters"
                                : "No flights meet all your constraints"}
                            </h3>
                            {result.suggestions.map((s) => (
                              <p key={s}>{s}</p>
                            ))}
                            {result.results.length > 0 && (
                              <button
                                className="button secondary"
                                onClick={() => {
                                  setOnlyClear(false);
                                  setFilterCost("");
                                  setFilterStops("");
                                  setFilterTravel("");
                                }}
                              >
                                Clear result filters
                              </button>
                            )}
                          </div>
                        )
                      ) : (
                        <div className="empty search-empty">
                          <div className="notebook-sketch" aria-hidden="true">
                            <span className="sketch-label">
                              somewhere between classes & clouds
                            </span>
                            <svg viewBox="0 0 320 150" fill="none">
                              <circle
                                className="sketch-sun"
                                cx="249"
                                cy="40"
                                r="22"
                              />
                              <path
                                className="sketch-trail"
                                d="M28 114c37 18 78-8 69-29-9-23-43-4-22 14s80 10 120-39"
                              />
                              <path
                                className="sketch-plane"
                                d="m182 45 90-23-37 73-17-33-36-17Zm36 17 54-40M218 62l-4 23 12-10"
                              />
                              <path
                                className="sketch-cloud"
                                d="M25 54h57c6-14-9-23-18-17-4-23-34-17-31 2-10-3-18 5-8 15ZM240 125h48M250 133h23M130 27v12m-6-6h12"
                              />
                            </svg>
                            <span className="sketch-caption">
                              a change of scenery sounds nice.
                            </span>
                          </div>
                          <h3>A weekend away, without the guesswork.</h3>
                          <p>
                            Choose your dates and find flights. We’ll show what
                            each trip costs and which classes it overlaps.
                          </p>
                          <div className="empty-points">
                            <span>
                              <Check size={15} />
                              Round-trip cost
                            </span>
                            <span>
                              <Check size={15} />
                              Class-aware ranking
                            </span>
                            <span>
                              <Check size={15} />
                              Clear tradeoffs
                            </span>
                          </div>
                        </div>
                      )}
                      {history.length > 0 && (
                        <details className="recent">
                          <summary>Recent searches ({history.length})</summary>
                          {history.map((h) => (
                            <button
                              key={h.id}
                              onClick={() => {
                                setResult(h);
                                setStale(true);
                              }}
                            >
                              {dateLabel(h.created_at)} ·{" "}
                              {h.results[0]
                                ? `${h.results[0].itinerary.outbound[0].origin} → ${h.results[0].itinerary.outbound.at(-1)?.destination}`
                                : "No matches"}{" "}
                              · {h.results.length} results{" "}
                              <ArrowUpRight size={14} />
                            </button>
                          ))}
                        </details>
                      )}
                    </section>
                  </div>
                </>
              )}
              {page === "schedule" && (
                <div className="schedule-page">
                  <section className="panel">
                    <div className="section-title">
                      <h2>Your weekly classes</h2>
                      <span className="badge">
                        {schedule.classes.length} recurring
                      </span>
                    </div>
                    <div className="week-grid">
                      {days.map((day, i) => (
                        <div className="day-column" key={day}>
                          <h3>
                            {day.slice(0, 3)}
                            <small>
                              {
                                schedule.classes.filter((c) => c.weekday === i)
                                  .length
                              }{" "}
                              classes
                            </small>
                          </h3>
                          {schedule.classes
                            .filter((c) => c.weekday === i)
                            .sort((a, b) =>
                              a.start_time.localeCompare(b.start_time),
                            )
                            .map((c) => (
                              <button
                                className="class-block"
                                key={c.id}
                                onClick={() => edit(c)}
                              >
                                <strong>{c.title}</strong>
                                <span>
                                  {c.start_time.slice(0, 5)}–
                                  {c.end_time.slice(0, 5)}
                                  {c.end_time < c.start_time ? " +1 day" : ""}
                                </span>
                                <small>Edit class</small>
                              </button>
                            ))}
                          {!schedule.classes.some((c) => c.weekday === i) && (
                            <span className="free-day">No classes</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                  <div className="two-col">
                    <form
                      className="panel"
                      onSubmit={(e) => {
                        e.preventDefault();
                        classSubmit();
                      }}
                    >
                      <h2>{editClass ? "Edit class" : "Add a class"}</h2>
                      <Field label="Class name">
                        <input
                          required
                          maxLength={100}
                          value={classDraft.title}
                          placeholder="e.g. Data Structures"
                          onChange={(e) =>
                            setClassDraft({
                              ...classDraft,
                              title: e.target.value,
                            })
                          }
                        />
                      </Field>
                      <Field label="Day of week">
                        <select
                          value={classDraft.weekday}
                          onChange={(e) =>
                            setClassDraft({
                              ...classDraft,
                              weekday: +e.target.value,
                            })
                          }
                        >
                          {days.map((d, i) => (
                            <option key={d} value={i}>
                              {d}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <div className="field-grid">
                        <Field label="Class starts">
                          <input
                            required
                            type="time"
                            value={classDraft.start_time}
                            onChange={(e) =>
                              setClassDraft({
                                ...classDraft,
                                start_time: e.target.value,
                              })
                            }
                          />
                        </Field>
                        <Field label="Class ends">
                          <input
                            required
                            type="time"
                            value={classDraft.end_time}
                            onChange={(e) =>
                              setClassDraft({
                                ...classDraft,
                                end_time: e.target.value,
                              })
                            }
                          />
                        </Field>
                      </div>
                      <p className="helper">
                        An earlier end time means the class finishes the next
                        day.
                      </p>
                      <div className="button-row">
                        <button className="button primary" disabled={busy}>
                          <Plus size={17} />
                          {editClass ? "Update class" : "Add class"}
                        </button>
                        {editClass && (
                          <>
                            <button
                              type="button"
                              className="button secondary"
                              onClick={() => {
                                setEditClass(null);
                                setClassDraft(emptyClass);
                              }}
                            >
                              Cancel edit
                            </button>
                            <button
                              type="button"
                              className="button danger"
                              disabled={busy}
                              onClick={() =>
                                void action(async () => {
                                  await api(`/classes/${editClass}`, "DELETE");
                                  await refreshSchedule();
                                  setEditClass(null);
                                  setClassDraft(emptyClass);
                                }, "Class and its cancellations removed.")
                              }
                            >
                              <Trash2 size={16} />
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    </form>
                    <form
                      className="panel"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void action(async () => {
                          await api("/exceptions", "POST", {
                            kind: exception.kind,
                            date: exception.date,
                            class_id:
                              exception.kind === "cancel"
                                ? +exception.class_id
                                : null,
                            title: exception.title || "Extra class",
                            start_time:
                              exception.kind === "add"
                                ? exception.start_time
                                : null,
                            end_time:
                              exception.kind === "add"
                                ? exception.end_time
                                : null,
                          });
                          await refreshSchedule();
                        }, "Schedule exception added.");
                      }}
                    >
                      <h2>One-time changes</h2>
                      <Field label="Change type">
                        <select
                          value={exception.kind}
                          onChange={(e) =>
                            setException({
                              ...exception,
                              kind: e.target.value as "cancel" | "add",
                            })
                          }
                        >
                          <option value="cancel">
                            Cancel a class occurrence
                          </option>
                          <option value="add">Add an extra class</option>
                        </select>
                      </Field>
                      <Field label="Exception date">
                        <input
                          required
                          type="date"
                          value={exception.date}
                          onChange={(e) =>
                            setException({ ...exception, date: e.target.value })
                          }
                        />
                      </Field>
                      {exception.kind === "cancel" ? (
                        <Field label="Class to cancel">
                          <select
                            required
                            value={exception.class_id}
                            onChange={(e) =>
                              setException({
                                ...exception,
                                class_id: e.target.value,
                              })
                            }
                          >
                            <option value="">Choose class</option>
                            {schedule.classes.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.title} · {days[c.weekday]}
                              </option>
                            ))}
                          </select>
                        </Field>
                      ) : (
                        <>
                          <Field label="Extra class name">
                            <input
                              required
                              value={exception.title}
                              onChange={(e) =>
                                setException({
                                  ...exception,
                                  title: e.target.value,
                                })
                              }
                            />
                          </Field>
                          <div className="field-grid">
                            <Field label="Extra class starts">
                              <input
                                type="time"
                                required
                                value={exception.start_time}
                                onChange={(e) =>
                                  setException({
                                    ...exception,
                                    start_time: e.target.value,
                                  })
                                }
                              />
                            </Field>
                            <Field label="Extra class ends">
                              <input
                                type="time"
                                required
                                value={exception.end_time}
                                onChange={(e) =>
                                  setException({
                                    ...exception,
                                    end_time: e.target.value,
                                  })
                                }
                              />
                            </Field>
                          </div>
                        </>
                      )}
                      <button className="button primary" disabled={busy}>
                        Add exception
                      </button>
                      <div className="exception-list">
                        {schedule.exceptions.map((e: ExceptionItem) => (
                          <div key={e.id}>
                            <span>
                              <strong>
                                {e.kind === "cancel"
                                  ? `Cancelled: ${schedule.classes.find((c) => c.id === e.class_id)?.title || "Class"}`
                                  : e.title}
                              </strong>
                              <small>{dateLabel(e.date)}</small>
                            </span>
                            <button
                              type="button"
                              aria-label={`Remove exception ${e.id}`}
                              disabled={busy}
                              onClick={() =>
                                void action(async () => {
                                  await api(`/exceptions/${e.id}`, "DELETE");
                                  await refreshSchedule();
                                }, "Exception removed.")
                              }
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </form>
                  </div>
                </div>
              )}
              {page === "preferences" && draftPrefs && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void action(async () => {
                      const p = await api<Preferences>(
                        "/preferences",
                        "PUT",
                        draftPrefs,
                      );
                      setPrefs(p);
                      setDraftPrefs(p);
                      setQuery((q) => ({
                        ...q,
                        origin: p.home_airport,
                        weights: p.weights,
                        departure_start: p.departure_start,
                        departure_end: p.departure_end,
                        arrival_start: p.arrival_start,
                        arrival_end: p.arrival_end,
                      }));
                      setStale(true);
                    }, "Preferences saved. New searches will use these settings.");
                  }}
                >
                  <div className="two-col">
                    <section className="panel">
                      <h2>You & your starting point</h2>
                      <Field label="Student name">
                        <input
                          required
                          maxLength={80}
                          value={draftPrefs.name}
                          onChange={(e) =>
                            setDraftPrefs({
                              ...draftPrefs,
                              name: e.target.value,
                            })
                          }
                        />
                      </Field>
                      <Field
                        label="Class timezone"
                        hint="IANA timezone, e.g. America/Chicago. Classes always use this zone."
                      >
                        <input
                          required
                          list="timezones"
                          value={draftPrefs.timezone}
                          onChange={(e) =>
                            setDraftPrefs({
                              ...draftPrefs,
                              timezone: e.target.value,
                            })
                          }
                        />
                        <datalist id="timezones">
                          {[...new Set(airports.map((a) => a.timezone))].map(
                            (z) => (
                              <option key={z}>{z}</option>
                            ),
                          )}
                        </datalist>
                      </Field>
                      <AirportSelect
                        label="Home airport"
                        value={draftPrefs.home_airport}
                        onChange={(v) =>
                          setDraftPrefs({ ...draftPrefs, home_airport: v })
                        }
                        airports={airports}
                      />
                      <div className="field-grid">
                        <Field label="Home airport transit (min)">
                          <input
                            type="number"
                            required
                            min="0"
                            max="360"
                            value={draftPrefs.transit_minutes}
                            onChange={(e) =>
                              setDraftPrefs({
                                ...draftPrefs,
                                transit_minutes: +e.target.value,
                              })
                            }
                          />
                        </Field>
                        <Field label="Airport arrival buffer (min)">
                          <input
                            type="number"
                            required
                            min="0"
                            max="360"
                            value={draftPrefs.buffer_minutes}
                            onChange={(e) =>
                              setDraftPrefs({
                                ...draftPrefs,
                                buffer_minutes: +e.target.value,
                              })
                            }
                          />
                        </Field>
                      </div>
                      <p className="helper">
                        Transit applies between home and the origin airport in
                        both directions. The arrival buffer applies before both
                        flights. Adjust transit if searching from a different
                        airport.
                      </p>
                      <h2 className="subheading">Your trip budget</h2>
                      {(
                        [
                          ["budget", "Total budget (USD)", 1, 50000],
                          [
                            "baggage_estimate",
                            "Round-trip baggage estimate (USD)",
                            0,
                            2000,
                          ],
                          [
                            "ground_estimate",
                            "All ground transportation estimate (USD)",
                            0,
                            2000,
                          ],
                        ] as const
                      ).map(([key, label, min, max]) => (
                        <Field key={key} label={label}>
                          <input
                            type="number"
                            required
                            min={min}
                            max={max}
                            step="0.01"
                            value={draftPrefs[key]}
                            onChange={(e) =>
                              setDraftPrefs({
                                ...draftPrefs,
                                [key]: +e.target.value,
                              })
                            }
                          />
                        </Field>
                      ))}
                      <p className="helper">
                        Estimated extras are added once per round trip. Total
                        cost excludes lodging and meals.
                      </p>
                    </section>
                    <section className="panel">
                      <h2>Preferred local travel times</h2>
                      <p className="helper">
                        Applies to both journeys in each airport’s local
                        timezone. Windows crossing midnight are supported. Equal
                        times mean any time.
                      </p>
                      <TimeWindows
                        value={draftPrefs}
                        onChange={(k, v) =>
                          setDraftPrefs({ ...draftPrefs, [k]: v })
                        }
                      />
                      <h2 className="subheading">Default ranking priorities</h2>
                      <WeightEditor
                        weights={draftPrefs.weights}
                        onChange={(weights) =>
                          setDraftPrefs({ ...draftPrefs, weights })
                        }
                      />
                      <div className="context-note">
                        <GraduationCap size={22} />
                        <span>
                          This MVP uses one shared demo student profile without
                          sign-in.
                        </span>
                      </div>
                    </section>
                  </div>
                  <button
                    className="button primary save-preferences"
                    disabled={
                      busy || !Object.values(draftPrefs.weights).some(Boolean)
                    }
                  >
                    <Check size={17} />
                    Save preferences
                  </button>
                </form>
              )}
              {page === "saved" && (
                <>
                  {saved.length ? (
                    <>
                      <div className="comparison-toolbar">
                        <span>
                          {compare.length} of 3 selected for comparison
                        </span>
                        <button
                          className="button secondary"
                          disabled={!compare.length}
                          onClick={() => setCompare([])}
                        >
                          Clear selection
                        </button>
                      </div>
                      {chosen.length > 0 && (
                        <section className="panel compare-panel">
                          <h2>Side-by-side comparison</h2>
                          <p className="helper">
                            Saved snapshots reflect the schedule, budget, and
                            priorities at search time. Re-run a search for
                            updated rankings.
                          </p>
                          <div className="table-scroll">
                            <table>
                              <thead>
                                <tr>
                                  <th scope="col">Trip details</th>
                                  {chosen.map((s) => (
                                    <th scope="col" key={s.id}>
                                      {
                                        s.evaluation.itinerary.outbound[0]
                                          .airline
                                      }
                                      <small>
                                        {
                                          s.evaluation.itinerary.outbound[0]
                                            .origin
                                        }{" "}
                                        →{" "}
                                        {
                                          s.evaluation.itinerary.outbound.at(-1)
                                            ?.destination
                                        }{" "}
                                        ·{" "}
                                        {dateLabel(
                                          s.evaluation.itinerary.outbound[0]
                                            .departure,
                                        )}
                                      </small>
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {(
                                  [
                                    "Estimated total",
                                    "Airfare",
                                    "Baggage estimate",
                                    "Ground estimate",
                                    "Overall fit",
                                    "Class conflicts",
                                    "Total travel",
                                    "Total stops",
                                    "Days away",
                                  ] as const
                                ).map((label, i) => (
                                  <tr key={label}>
                                    <th scope="row">{label}</th>
                                    {chosen.map((s) => {
                                      const e = s.evaluation;
                                      return (
                                        <td key={s.id}>
                                          {
                                            [
                                              money(e.cost.total),
                                              money(e.cost.airfare),
                                              money(e.cost.baggage_estimate),
                                              money(e.cost.ground_estimate),
                                              `${e.score.toFixed(0)}/100`,
                                              `${e.conflicts.length} (${e.conflict_minutes} min)`,
                                              duration(e.travel_minutes),
                                              e.stops,
                                              e.trip_days.toFixed(1),
                                            ][i]
                                          }
                                        </td>
                                      );
                                    })}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </section>
                      )}
                      <div className="saved-list">
                        {saved.map((s) => (
                          <div key={s.id}>
                            <div className="saved-actions">
                              <label>
                                <input
                                  type="checkbox"
                                  checked={compare.includes(s.id)}
                                  disabled={
                                    !compare.includes(s.id) &&
                                    compare.length >= 3
                                  }
                                  onChange={(e) =>
                                    setCompare((c) =>
                                      e.target.checked
                                        ? [...c, s.id]
                                        : c.filter((id) => id !== s.id),
                                    )
                                  }
                                />
                                Compare{" "}
                                {s.evaluation.itinerary.outbound[0].airline} ·{" "}
                                {dateLabel(
                                  s.evaluation.itinerary.outbound[0].departure,
                                )}
                              </label>
                              <button
                                className="text-button"
                                disabled={busy}
                                onClick={() =>
                                  void action(async () => {
                                    await api(`/saved/${s.id}`, "DELETE");
                                    setSaved((v) =>
                                      v.filter((x) => x.id !== s.id),
                                    );
                                    setCompare((c) =>
                                      c.filter((id) => id !== s.id),
                                    );
                                  }, "Saved flight removed.")
                                }
                              >
                                <Trash2 size={15} />
                                Remove
                              </button>
                            </div>
                            <FlightCard
                              item={s.evaluation}
                              saved
                              onSave={() => {}}
                            />
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="empty">
                      <Bookmark size={35} />
                      <h2>Your shortlist is waiting</h2>
                      <p>
                        Save flights from your results to compare them here.
                      </p>
                      <button
                        className="button primary"
                        onClick={() => setPage("search")}
                      >
                        Find flights <ArrowRight size={16} />
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
          <footer>
            <span>STUDENT FLIGHT PLANNER</span>
            <p>
              {mock
                ? "Demo itineraries · Prices are illustrative · No booking or payments"
                : "Provider inventory · Estimated extras · No booking or payments"}
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}
type WindowKey =
  "departure_start" | "departure_end" | "arrival_start" | "arrival_end";
function TimeWindows({
  value,
  onChange,
}: {
  value: Record<WindowKey, string>;
  onChange: (key: WindowKey, value: string) => void;
}) {
  return (
    <div className="field-grid">
      {(
        [
          ["departure_start", "Depart after"],
          ["departure_end", "Depart before"],
          ["arrival_start", "Arrive after"],
          ["arrival_end", "Arrive before"],
        ] as const
      ).map(([key, label]) => (
        <Field key={key} label={label}>
          <input
            type="time"
            required
            value={value[key].slice(0, 5)}
            onChange={(e) => onChange(key, e.target.value)}
          />
        </Field>
      ))}
    </div>
  );
}
