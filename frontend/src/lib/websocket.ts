import { useEffect, useRef } from 'react';

import { useNegotiationStore, type WebSocketEnvelope } from '../store/useNegotiationStore';

const DEFAULT_WS_URL = 'ws://localhost:8000/ws/monitor';
const RECONNECT_DELAY_MS = 2000;

type UseAegisSocketOptions = {
  /** Defaults to the monitor route (VITE_WS_URL or the hardcoded default). */
  url?: string;
  /** Set false to skip connecting entirely — e.g. a connection that should
   * only open on a user action, not on mount. Defaults to true. */
  enabled?: boolean;
  /** Called with every in-order, post-snapshot envelope this socket
   * receives, in addition to (or instead of) the global store update. */
  onEnvelope?: (envelope: WebSocketEnvelope) => void;
  /** Whether this connection should write into the shared
   * useNegotiationStore (trackedObjects/activeConjunctionAlert/
   * connectionStatus). Defaults to true — the one persistent /ws/monitor
   * connection mounted in App.tsx should stay the source of truth for
   * NavBar's status pill. Set false for secondary/one-off connections
   * (e.g. a per-negotiation socket) so they don't cross-talk with it. */
  updateStore?: boolean;
};

/**
 * Connects to one of Dev B's live WebSocket routes, per architecture.md's
 * Client Pattern:
 * - discards/reorders anything arriving out of sequence
 * - requests (by virtue of reconnecting at all — the backend always sends
 *   one on connect) a full snapshot on every reconnect, never assuming
 *   delta continuity (invariant 6)
 *
 * Called with no args, this mounts the persistent /ws/monitor connection —
 * do that once near the app root (App.tsx), not per-page, since the
 * connection and its status should persist across route changes. Pass
 * `{ url, updateStore: false, onEnvelope }` for a secondary, page-local
 * connection to a different route (e.g. /ws/negotiation/{id}) that
 * shouldn't affect the global store or NavBar's status pill.
 */
export function useAegisSocket(options: UseAegisSocketOptions = {}): void {
  const {
    url = import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL,
    enabled = true,
    updateStore = true,
  } = options;

  const updateFromSocket = useNegotiationStore((s) => s.updateFromSocket);
  const setConnectionStatus = useNegotiationStore((s) => s.setConnectionStatus);

  // Held in a ref so a fresh inline callback each render doesn't tear down
  // and reconnect the socket — only url/enabled/updateStore should do that.
  const onEnvelopeRef = useRef(options.onEnvelope);
  onEnvelopeRef.current = options.onEnvelope;

  useEffect(() => {
    if (!enabled) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      // Reset per-connection sequence tracking on every fresh attempt — a
      // message from the *previous* socket must never be compared against
      // the new one's sequence numbers (invariant 6: no assumed continuity).
      let hasSnapshot = false;
      let lastSequence = -1;

      socket = new WebSocket(url);

      socket.onmessage = (event: MessageEvent<string>) => {
        let envelope: WebSocketEnvelope;
        try {
          envelope = JSON.parse(event.data);
        } catch {
          console.error('[useAegisSocket] received non-JSON message, ignoring:', event.data);
          return;
        }

        if (!hasSnapshot) {
          if (envelope.type !== 'snapshot') {
            console.error(
              `[useAegisSocket] expected a snapshot first, got "${envelope.type}" instead — ` +
                'ignoring until a snapshot arrives (invariant 6)',
            );
            return;
          }
          hasSnapshot = true;
        }

        if (envelope.sequence <= lastSequence) {
          console.warn(
            `[useAegisSocket] discarding out-of-order message (sequence ${envelope.sequence} <= last seen ${lastSequence})`,
          );
          return;
        }
        lastSequence = envelope.sequence;

        if (updateStore) {
          updateFromSocket(envelope);
          setConnectionStatus('connected');
        }
        onEnvelopeRef.current?.(envelope);
      };

      socket.onclose = () => {
        if (cancelled) return;
        // Retries forever at a fixed interval — no attempt cap. Status goes
        // straight to 'reconnecting' and stays there for the whole outage;
        // 'disconnected' is reserved for a possible future explicit/user-
        // initiated disconnect and is never set by this retry loop, so a
        // brief backend blip during a demo never looks like it gave up.
        if (updateStore) setConnectionStatus('reconnecting');
        reconnectTimer = setTimeout(() => {
          if (cancelled) return;
          connect();
        }, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => {
        // onclose fires right after for a browser WebSocket and owns the
        // actual reconnect scheduling — this is just for console visibility.
        console.error('[useAegisSocket] socket error');
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [url, enabled, updateStore, updateFromSocket, setConnectionStatus]);
}

/**
 * Derives the /ws/negotiation/{conjunctionId} URL from wherever the
 * monitor socket points (VITE_WS_URL or the hardcoded default), so both
 * routes stay pointed at the same host/port from one source of truth.
 */
export function buildNegotiationWsUrl(conjunctionId: string): string {
  const monitorUrl: string = import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL;
  const base = monitorUrl.replace(/\/ws\/monitor\/?$/, '');
  return `${base}/ws/negotiation/${encodeURIComponent(conjunctionId)}`;
}
