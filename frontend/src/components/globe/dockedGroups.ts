/**
 * Physically docked/co-located object groups — the frontend-side mirror of
 * backend/app/orchestrator/orchestrator.py's `DOCKED_OBJECT_GROUPS` (which in
 * turn cross-references backend/app/data/celestrak.py's `LOCKED_OBJECTS`,
 * the actual curated 20-object set). Keep all three in sync if that set
 * changes.
 *
 * These NORAD IDs propagate to identical (or effectively identical) ECI
 * positions, so their globe labels stack and overlap illegibly if rendered
 * individually. Globe.tsx renders one combined "<label> (<count>)" marker
 * for each group instead — the same root cause as the docked-object false
 * conjunction bug the backend groups fix, just showing up as a label
 * rendering collision instead of a false alert.
 */
export type DockedObjectGroup = {
  label: string;
  ids: Set<string>;
};

export const DOCKED_OBJECT_GROUPS: DockedObjectGroup[] = [
  {
    label: 'ISS COMPLEX',
    ids: new Set(['25544', '36086', '49044', '67796', '68689', '68837']),
  },
  {
    label: 'CSS CLUSTER',
    ids: new Set(['48274', '53239', '54216', '69049', '69180']),
  },
];
