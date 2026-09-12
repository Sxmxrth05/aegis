import { create } from 'zustand';
import type {
  ConjunctionAlert,
  TrackedObject,
  NegotiationMessage,
  Resolution,
} from '../components/globe/types';

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
 * Snapshot payload for /ws/monitor vs /ws/negotiation/{id}
 */
type SnapshotPayload = {
  trackedObjects?: TrackedObject[];
  conjunctions?: ConjunctionAlert[];
  messages?: NegotiationMessage[];
  resolution?: Resolution | null;
};

type NegotiationState = {
  trackedObjects: TrackedObject[];
  activeConjunctionAlert: ConjunctionAlert | null;
  connectionStatus: ConnectionStatus;
  
  // Phase 2 fields
  messages: NegotiationMessage[];
  resolution: Resolution | null;
  
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
  messages: [],
  resolution: null,

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  updateFromSocket: (envelope) => {
    switch (envelope.type) {
      case 'snapshot': {
        const payload = envelope.payload as SnapshotPayload;
        // The snapshot might be from /ws/monitor OR /ws/negotiation/{id}.
        // Only replace fields that are actually provided in this payload
        // so we don't clobber the global monitor state with an empty
        // negotiation snapshot.
        set((state) => ({
          trackedObjects: payload.trackedObjects !== undefined ? payload.trackedObjects : state.trackedObjects,
          activeConjunctionAlert: payload.conjunctions !== undefined ? (payload.conjunctions[0] ?? null) : state.activeConjunctionAlert,
          messages: payload.messages !== undefined ? payload.messages : state.messages,
          resolution: payload.resolution !== undefined ? payload.resolution : state.resolution,
        }));
        break;
      }
      case 'conjunction_alert': {
        set({ activeConjunctionAlert: envelope.payload as ConjunctionAlert });
        break;
      }
      case 'negotiation_message': {
        const msg = envelope.payload as NegotiationMessage;
        set((state) => ({ messages: [...state.messages, msg] }));
        break;
      }
      case 'resolution': {
        set({ resolution: envelope.payload as Resolution });
        break;
      }
      case 'error':
        console.error('[useNegotiationStore] server error event:', envelope.payload);
        break;
      default:
        console.warn('[useNegotiationStore] unknown envelope type:', envelope);
    }
  },
}));
