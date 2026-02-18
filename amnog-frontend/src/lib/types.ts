export const THERAPY_AREAS = [
  "Augenerkrankungen",
  "Haut",
  "Herz-Kreislauf",
  "Infektionen",
  "Atmung",
  "Blut/Blutbildend",
  "Muskel-Skelett",
  "Nervensystem",
  "Urogenital",
  "Verdauung",
  "Onkologie",
  "Psychische",
  "Stoffwechsel",
  "Sonstiges",
] as const;

export const SETTINGS = ["ambulant", "stationär", "beides", "unklar"] as const;
export const ROLES = ["replacement", "add-on", "monotherapy", "unklar"] as const;
export const LINES = ["1L", "2L", "später", "switch", "unklar"] as const;
export const COMPARATOR_TYPES = ["aktiv", "placebo", "BSC", "physician's choice", "unklar"] as const;

export type ReferenceItem = {
  decision_id: string;
  product_name: string;
  decision_date: string;
  url: string;
  snippet: string;
  score: number;
};

export type CandidateResult = {
  rank: number;
  candidate_text: string;
  support_score: number;
  confidence: "hoch" | "mittel" | "niedrig";
  support_cases: number;
  references: ReferenceItem[];
};

export type ShortlistResponse = {
  run_id: string;
  candidates: CandidateResult[];
  ambiguity: "hoch" | "mittel" | "niedrig";
  generated_at: string;
  notices: string[];
  status: "ok" | "needs_clarification" | "no_result";
  reasons: string[];
  diagnostics?: Record<string, unknown>;
};

export type RunResponse = {
  run_id: string;
  request_payload: Record<string, unknown>;
  response_payload: ShortlistResponse;
  created_at: string;
};
