/**
 * Mirrors backend/app/schemas/tracked_object.py's TrackedObject and
 * backend/app/schemas/conjunction.py's ConjunctionAlert field-for-field.
 * Dev B owns the canonical schemas; if those change, update these too.
 */
export type TrackedObject = {
  norad_id: string;
  name: string;
  tle_line1: string;
  tle_line2: string;
  timestamp_utc: string;
  position_km: [number, number, number];
  velocity_kmps: [number, number, number];
};

export type ConjunctionStatus =
  | 'alerted'
  | 'negotiating'
  | 'resolved'
  | 'escalated'
  | 'stood_down';

export type ConjunctionAlert = {
  id: string;
  primary_id: string;
  secondary_id: string;
  tca_utc: string;
  miss_distance_km: number;
  relative_velocity_kmps: number;
  status: ConjunctionStatus;
  created_at: string;
};
