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

export type AgentId = 'operator_A' | 'operator_B' | 'validation';
export type ProposedAction = 'maneuver' | 'stand_down' | 'reject' | 'approve';

export type NegotiationMessage = {
  id: string;
  conjunction_id: string;
  agent_id: AgentId;
  round: number;
  yield_score: number | null;
  justification_text: string;
  proposed_action: ProposedAction;
  created_at: string;
};

export type ResolutionStatus = 'approved' | 'approved_no_action' | 'no_safe_maneuver_found';

export type Resolution = {
  id: string;
  conjunction_id: string;
  maneuvering_agent: string;
  maneuver_type: string;
  delta_v_mps: number;
  execution_time_utc: string;
  expected_min_distance_km: number;
  residual_risk: number;
  rationale_text: string;
  status: ResolutionStatus;
};

export type TrajectoryWaypoint = {
  timestamp_utc: string;
  t_seconds: number;
  position_km: [number, number, number];
  velocity_kmps: [number, number, number];
  lat: number;
  lng: number;
  alt_km: number;
};

export type TrajectoryStep = {
  timestamp_utc: string;
  t_seconds: number;
  is_post_burn: boolean;
  nominal_primary: TrajectoryWaypoint;
  nominal_secondary: TrajectoryWaypoint;
  nominal_distance_km: number;
  maneuvered_primary: TrajectoryWaypoint;
  maneuvered_secondary: TrajectoryWaypoint;
  maneuvered_distance_km: number;
};

export type ManeuverTrajectoryResult = {
  conjunction_id: string;
  primary_norad_id: string;
  primary_name: string;
  secondary_norad_id: string;
  secondary_name: string;
  maneuvering_norad_id: string;
  maneuver_type: string;
  delta_v_mps: number;
  execution_time_utc: string;
  tca_nominal_utc: string;
  min_distance_nominal_km: number;
  tca_maneuvered_utc: string;
  min_distance_maneuvered_km: number;
  cleared_threshold: boolean;
  steps: TrajectoryStep[];
  nominal_path_primary: [number, number, number][];
  nominal_path_secondary: [number, number, number][];
  maneuvered_path: [number, number, number][];
};
