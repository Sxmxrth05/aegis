import { Badge } from '../shared/Badge';
import { Card } from '../shared/Card';
import type { NegotiationMessage } from '../globe/types';

export function NegotiationConsole({ messages }: { messages: NegotiationMessage[] }) {
  if (messages.length === 0) return null;

  return (
    <div className="mt-6 space-y-4">
      <h3 className="text-sm font-semibold text-text-primary">Live Transcript</h3>
      
      <div className="flex flex-col gap-4">
        {messages.map((msg) => {
          const isA = msg.agent_id === 'operator_A';
          const isValidation = msg.agent_id === 'validation';
          
          return (
            <div
              key={msg.id}
              className={`flex w-full ${isValidation ? 'justify-center' : isA ? 'justify-start' : 'justify-end'}`}
            >
              <Card className={`max-w-[80%] p-4 ${isValidation ? 'border-warning-light bg-warning-muted/10' : ''}`}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Badge status={isValidation ? 'warning' : isA ? 'active' : 'success'}>
                      {isValidation ? 'Validation Agent' : isA ? 'Operator A' : 'Operator B'}
                    </Badge>
                    <span className="text-xs text-text-muted">Round {msg.round}</span>
                  </div>
                  
                  {msg.yield_score !== null && (
                    <span className="font-mono text-xs text-text-secondary">
                      Yield Score: <span className="font-semibold text-text-primary">{msg.yield_score.toFixed(4)}</span>
                    </span>
                  )}
                </div>
                
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                  {msg.justification_text}
                </p>
                
                <div className="mt-3 flex justify-end">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
                    Proposed: <span className="font-bold text-text-secondary">{msg.proposed_action}</span>
                  </span>
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
