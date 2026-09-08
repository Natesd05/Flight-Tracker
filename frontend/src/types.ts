export type Weights = {
  cost: number;
  conflicts: number;
  layovers: number;
  windows: number;
  travel: number;
};
export type Preferences = {
  name: string;
  timezone: string;
  home_airport: string;
  transit_minutes: number;
  buffer_minutes: number;
  budget: number;
  baggage_estimate: number;
  ground_estimate: number;
  departure_start: string;
  departure_end: string;
  arrival_start: string;
  arrival_end: string;
  weights: Weights;
};
export type ClassItem = {
  id: number;
  title: string;
  weekday: number;
  start_time: string;
  end_time: string;
};
export type ExceptionItem = {
  id: number;
  date: string;
  kind: "cancel" | "add";
  class_id: number | null;
  title: string;
  start_time: string | null;
  end_time: string | null;
};
export type Schedule = { classes: ClassItem[]; exceptions: ExceptionItem[] };
export type Airport = { code: string; name: string; timezone: string };
export type Segment = {
  origin: string;
  destination: string;
  departure: string;
  arrival: string;
  airline: string;
  flight_number: string;
};
export type Evaluation = {
  itinerary: {
    id: string;
    provider: string;
    airfare: number;
    currency: string;
    outbound: Segment[];
    inbound: Segment[];
  };
  cost: {
    airfare: number;
    baggage_estimate: number;
    ground_estimate: number;
    total: number;
  };
  score: number;
  penalties: Weights;
  weights: Weights;
  conflicts: {
    title: string;
    start: string;
    end: string;
    overlap_minutes: number;
  }[];
  conflict_minutes: number;
  travel_minutes: number;
  trip_days: number;
  stops: number;
  window_violations: number;
  away_start: string;
  away_end: string;
  explanations: string[];
};
export type SearchResult = {
  id: number;
  provider: string;
  evaluated_count: number;
  rejected: Record<string, number>;
  suggestions: string[];
  results: Evaluation[];
  created_at: string;
};
export type Saved = {
  id: number;
  search_id: number;
  itinerary_id: string;
  evaluation: Evaluation;
  created_at: string;
};
export type Query = {
  origin: string;
  destination: string;
  departure_from: string;
  departure_to: string;
  return_from: string;
  return_to: string;
  min_trip_days: number;
  max_trip_days: number;
  hard_budget: boolean;
  hard_conflicts: boolean;
  hard_windows: boolean;
  max_stops: number | null;
  weights: Weights;
  departure_start: string;
  departure_end: string;
  arrival_start: string;
  arrival_end: string;
};
