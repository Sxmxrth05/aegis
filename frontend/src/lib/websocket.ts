import { useEffect } from 'react';

import { useNegotiationStore, type WebSocketEnvelope } from '../store/useNegotiationStore';

const DEFAULT_WS_URL = 'ws://localhost:8000/ws/monitor';
const RECONNECT_DELAY_MS = 2000;

/**
 * Connects to Dev B's live /ws/monitor route, per architecture.md's Client
 * Pattern:
 * - discards/reorders anything arriving out of sequence
 * - requests (by virtue of reconnecting at all — the backend always sends
 *   one on connect) a full snapshot on every reconnect, never assuming
 *   delta continuity (invariant 6)
 *
 * Call this once near the app root (App.tsx), not per-page — the
 * connection and its status should persist across route changes, since the
 * NavBar's live indicator needs it regardless of which page is mounted.
 */
export function useAegisSocket(url: string = import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL) {
  const updateFromSocket = useNegotiationStore((s) => s.updateFromSocket);
  const setConnectionStatus = useNegotiationStore((s) => s.setConnectionStatus);

  useEffect(() => {
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

        updateFromSocket(envelope);
        setConnectionStatus('connected');
      };

      socket.onclose = () => {
        if (cancelled) return;
        // Retries forever at a fixed interval — no attempt cap. Status goes
        // straight to 'reconnecting' and stays there for the whole outage;
        // 'disconnected' is reserved for a possible future explicit/user-
        // initiated disconnect and is never set by this retry loop, so a
        // brief backend blip during a demo never looks like it gave up.
        setConnectionStatus('reconnecting');
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
  }, [url, updateFromSocket, setConnectionStatus]);
}
