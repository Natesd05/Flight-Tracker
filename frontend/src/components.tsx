import { useState, type ReactNode } from "react";
import {
  ArrowRight,
  Bookmark,
  Check,
  ChevronDown,
  Clock,
  Plane,
  AlertTriangle,
} from "lucide-react";
import type { Airport, Evaluation, Segment, Weights } from "./types";
export const money = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
export const duration = (n: number) =>
  `${Math.floor(n / 60)}h ${Math.round(n % 60)}m`;
export const dateLabel = (s: string) =>
  new Date(`${s.slice(0, 10)}T12:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
export const localClock = (s: string) => s.slice(11, 16);
export const weightLabels: Record<keyof Weights, string> = {
  cost: "Total cost",
  conflicts: "Class schedule",
  layovers: "Fewer stops",
  windows: "Travel windows",
  travel: "Travel time",
};
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function AirportSelect({
  label,
  value,
  onChange,
  airports,
}: {
  label: string;
  value: string;
  onChange: (s: string) => void;
  airports: Airport[];
}) {
  return (
    <Field label={label}>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {airports.map((a) => (
          <option value={a.code} key={a.code}>
            {a.code} · {a.name}
          </option>
        ))}
      </select>
    </Field>
  );
}
export function WeightEditor({
  weights,
  onChange,
}: {
  weights: Weights;
  onChange: (w: Weights) => void;
}) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  return (
    <div className="weights">
      {(Object.keys(weightLabels) as (keyof Weights)[]).map((k) => (
        <label key={k}>
          <span>
            {weightLabels[k]}{" "}
            <b>{total ? Math.round((weights[k] / total) * 100) : 0}%</b>
          </span>
          <input
            aria-label={`${weightLabels[k]} weight`}
            type="range"
            min="0"
            max="100"
            step="5"
            value={weights[k]}
            onChange={(e) => onChange({ ...weights, [k]: +e.target.value })}
          />
        </label>
      ))}
      {!total && (
        <p className="warning">At least one priority must be above zero.</p>
      )}
    </div>
  );
}
function Leg({ segments, label }: { segments: Segment[]; label: string }) {
  const first = segments[0],
    last = segments[segments.length - 1];
  const minutes =
    (Date.parse(last.arrival) - Date.parse(first.departure)) / 60000;
  return (
    <div className="leg">
      <span className="leg-label">
        {label}
        <small>{dateLabel(first.departure)}</small>
      </span>
      <div className="endpoint">
        <strong>{localClock(first.departure)}</strong>
        <span>{first.origin}</span>
      </div>
      <div className="flight-line">
        <small>
          {duration(minutes)} ·{" "}
          {segments.length === 1
            ? "Nonstop"
            : `${segments.length - 1} stop${segments.length > 2 ? "s" : ""}`}
        </small>
        <div>
          <i />
          <span />
          <Plane size={15} />
          <span />
          <i />
        </div>
        <small>
          {segments
            .slice(0, -1)
            .map((s) => s.destination)
            .join(" · ") || "No connection"}
        </small>
      </div>
      <div className="endpoint">
        <strong>{localClock(last.arrival)}</strong>
        <span>
          {last.destination}
          {first.departure.slice(0, 10) !== last.arrival.slice(0, 10) && (
            <small> · {dateLabel(last.arrival)}</small>
          )}
        </span>
      </div>
    </div>
  );
}
export function FlightCard({
  item,
  rank,
  saved,
  onSave,
  pending,
}: {
  item: Evaluation;
  rank?: number;
  saved: boolean;
  onSave: () => void;
  pending?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className={`flight-card ${rank === 1 ? "best" : ""}`}>
      <div className="card-top">
        <div className="airline">
          <span className="airline-icon">
            {rank ? String(rank).padStart(2, "0") : <Bookmark size={17} />}
          </span>
          <strong>
            {[
              ...new Set(
                [...item.itinerary.outbound, ...item.itinerary.inbound].map(
                  (s) => s.airline,
                ),
              ),
            ].join(" / ")}
          </strong>
          <span className="muted">Round trip · Economy</span>
          {item.itinerary.provider !== "mock" && (
            <span className="badge">
              {item.itinerary.provider === "duffel-test"
                ? "Test offers"
                : "Live offers"}
            </span>
          )}
        </div>
        {rank === 1 && <span className="badge">Highest ranked</span>}
        <span className="score">
          {item.score.toFixed(0)}
          <small>/100 fit</small>
        </span>
      </div>
      <div className="card-main">
        <div className="legs">
          <Leg segments={item.itinerary.outbound} label="OUTBOUND" />
          <Leg segments={item.itinerary.inbound} label="RETURN" />
        </div>
        <div className="price">
          <span>Estimated total</span>
          <strong>{money(item.cost.total)}</strong>
          <small>
            {money(item.cost.airfare)} airfare +{" "}
            {money(item.cost.baggage_estimate + item.cost.ground_estimate)}{" "}
            extras
          </small>
          <button
            className={saved ? "button saved" : "button primary"}
            onClick={onSave}
            disabled={saved || pending}
          >
            {saved ? <Check size={16} /> : <Bookmark size={16} />}
            {saved ? "Saved" : "Save flight"}
          </button>
        </div>
      </div>
      <div className="card-bottom">
        <span className={item.conflicts.length ? "conflict-tag" : "clear-tag"}>
          {item.conflicts.length ? (
            <AlertTriangle size={15} />
          ) : (
            <Check size={15} />
          )}
          {item.conflicts.length
            ? `${item.conflicts.length} class conflict${item.conflicts.length === 1 ? "" : "s"} · ${Math.round(item.conflict_minutes)} min missed`
            : "No class conflicts"}
        </span>
        <span>
          <Clock size={14} /> {item.trip_days.toFixed(1)} days away
        </span>
        <button
          className="text-button"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          Why this flight{" "}
          <ChevronDown size={16} className={expanded ? "rotate" : ""} />
        </button>
      </div>
      {expanded && (
        <div className="flight-details">
          <h4>The tradeoffs</h4>
          <ul>
            {item.explanations.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <div className="penalties">
            {(Object.keys(weightLabels) as (keyof Weights)[]).map((k) => (
              <div key={k}>
                <span>{weightLabels[k]}</span>
                <meter
                  aria-label={`${weightLabels[k]} fit`}
                  min="0"
                  max="1"
                  value={1 - item.penalties[k]}
                />
                <b>{Math.round((1 - item.penalties[k]) * 100)}%</b>
              </div>
            ))}
          </div>
          <small>
            Each bar shows fit for that factor. The overall score combines them
            using the priorities from this search; higher is better.
          </small>
          <h4>Flight details · all times local to each airport</h4>
          {[...item.itinerary.outbound, ...item.itinerary.inbound].map(
            (s, i) => (
              <div className="segment" key={i}>
                <span>
                  {s.airline} {s.flight_number}
                </span>
                <span>
                  {s.origin} {dateLabel(s.departure)} {localClock(s.departure)}{" "}
                  <ArrowRight size={13} /> {s.destination}{" "}
                  {dateLabel(s.arrival)} {localClock(s.arrival)}
                </span>
              </div>
            ),
          )}
          {[item.itinerary.outbound, item.itinerary.inbound].flatMap((leg) =>
            leg.slice(0, -1).map((s, i) => (
              <p key={`${s.flight_number}-${s.departure}`} className="muted">
                Layover at {s.destination}:{" "}
                {duration(
                  (Date.parse(leg[i + 1].departure) - Date.parse(s.arrival)) /
                    60000,
                )}
              </p>
            )),
          )}
          {item.conflicts.length > 0 && (
            <div className="conflict-box">
              <h4>Classes affected</h4>
              {item.conflicts.map((c, i) => (
                <p key={i}>
                  {c.title} · {dateLabel(c.start)} {localClock(c.start)}–
                  {localClock(c.end)} · {Math.round(c.overlap_minutes)} min
                  missed
                </p>
              ))}
              <small>Class times use your profile timezone.</small>
            </div>
          )}
          <p className="muted">
            Extras are round-trip estimates: baggage{" "}
            {money(item.cost.baggage_estimate)} and ground transportation{" "}
            {money(item.cost.ground_estimate)}. Lodging and meals are excluded.
          </p>
        </div>
      )}
    </article>
  );
}
