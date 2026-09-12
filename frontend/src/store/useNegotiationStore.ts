import { create } from 'zustand';
import type { ConjunctionAlert, TrackedObject } from '../components/globe/types';

/**
 * Mirrors the backend envelope contract in
 * backend/app/schemas/websocket.py (EventType, WebSocketEnvelope) — Dev B's
 * locked contract, field-for-field.
 */
export type EventType =
  | 'snapshot'
  | 'conjunction_alert'
  | 'negotiation_message'
  | 'resolution'
  | 'error';

export type WebSocketEnvelope<T = unknown> = {
  type: EventType;
  sequence: number;
  payload: T;
};

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

/**
 * The backend's /ws/monitor snapshot payload doesn't carry trackedObjects
 * yet (only `{ conjunctions: [] }` today — Dev A/B haven't wired real
 * tracked-object state into the snapshot). Both fields are optional so this
 * type stays correct as that payload grows.
 */
type SnapshotPayload = {
  trackedObjects?: TrackedObject[];
  conjunctions?: ConjunctionAlert[];
};

type NegotiationState = {
  trackedObjects: TrackedObject[];
  activeConjunctionAlert: ConjunctionAlert | null;
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (status: ConnectionStatus) => void;
  /**
   * The single funnel for all WebSocket message handling, per
   * code-standards.md — every event type is handled here, not scattered
   * across components.
   */
  updateFromSocket: (envelope: WebSocketEnvelope) => void;
};

export const useNegotiationStore = create<NegotiationState>((set) => ({
  trackedObjects: [],
  activeConjunctionAlert: null,
  connectionStatus: 'connecting',

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  updateFromSocket: (envelope) => {
    switch (envelope.type) {
      case 'snapshot': {
        const payload = envelope.payload as SnapshotPayload;
        // Snapshot always replaces state wholesale — never patches — per
        // architecture.md invariant 6 (no assumed delta continuity).
        set({
          trackedObjects: payload.trackedObjects ?? [],
          activeConjunctionAlert: payload.conjunctions?.[0] ?? null,
        });
        break;
      }
      case 'conjunction_alert': {
        set({ activeConjunctionAlert: envelope.payload as ConjunctionAlert });
        break;
      }
      case 'negotiation_message':
      case 'resolution':
        // Phase 2's negotiation state machine / result UI will extend this
        // store with the fields these need — no-op for now, not a bug.
        break;
      case 'error':
        console.error('[useNegotiationStore] server error event:', envelope.payload);
        break;
      default:
        console.warn('[useNegotiationStore] unknown envelope type:', envelope);
    }
  },
}));
