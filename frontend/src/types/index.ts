export type Tier = "hot" | "warm" | "cold";
export type SignalType = "tax_delinquency" | "foreclosure" | "absentee";

export interface ScoreBreakdown {
  tax: number;
  foreclosure: number;
  absentee: number;
  bonus: number;
  penalty: number;
}

export interface SignalDetail {
  signal_type: SignalType;
  severity: number;
  detected_at: string;
  raw_data: Record<string, unknown>;
}

export interface PropertySummary {
  id: string;
  address: string;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  latitude: number | null;
  longitude: number | null;
  score: number;
  tier: Tier;
  signals: SignalType[];
  property_type: string;
  assessed_value: number | null;
  updated_at: string;
}

export interface PropertyDetail extends PropertySummary {
  parcel_id: string;
  county: string;
  owner_name: string | null;
  owner_mailing_address: string | null;
  is_absentee: boolean;
  score_breakdown: ScoreBreakdown;
  signal_details: SignalDetail[];
}

export interface PropertyListResponse {
  results: PropertySummary[];
  total: number;
  page: number;
  limit: number;
}

export interface Filters {
  min_score: number | null;
  county: string | null;
  property_type: string | null;
  distress_types: SignalType[];
  bbox: [number, number, number, number] | null;
}
