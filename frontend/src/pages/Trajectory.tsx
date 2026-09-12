import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Globe } from '../components/globe/Globe';
import { Card } from '../components/shared/Card';
import { Badge } from '../components/shared/Badge';
import { Button } from '../components/shared/Button';
import type { ManeuverTrajectoryResult } from '../components/globe/types';

export default function Trajectory() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ManeuverTrajectoryResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!id) return;
    let canceled = false;
    async function fetchData() {
      setLoading(true);
      try {
        const res = await fetch(`/api/trajectory/${id}`);
        if (!res.ok) throw new Error('Failed to fetch trajectory');
        const json = await res.json();
        if (!canceled) {
          setData(json);
          setStepIndex(0);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!canceled) setLoading(false);
      }
    }
    fetchData();
    return () => { canceled = true; };
  }, [id]);

  if (loading) {
    return <div className="p-8 text-text-muted">Loading trajectory data...</div>;
  }

  if (!data) {
    return <div className="p-8 text-danger">Failed to load trajectory data.</div>;
  }

  const step = data.steps[stepIndex];
  
  const trackedObjects = [
    {
      norad_id: data.primary_norad_id,
      name: data.primary_name,
      tle_line1: '', tle_line2: '',
      timestamp_utc: step.timestamp_utc,
      position_km: step.maneuvered_primary.position_km,
      velocity_kmps: step.maneuvered_primary.velocity_kmps
    },
    {
      norad_id: data.secondary_norad_id,
      name: data.secondary_name,
      tle_line1: '', tle_line2: '',
      timestamp_utc: step.timestamp_utc,
      position_km: step.maneuvered_secondary.position_km,
      velocity_kmps: step.maneuvered_secondary.velocity_kmps
    }
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full flex-col md:flex-row relative">
      <Globe 
        trackedObjects={trackedObjects}
        mode="trajectory"
        trajectoryResult={data}
        className="flex-1"
      />
      
      {/* Overlay panel */}
      <div className="absolute top-6 right-6 w-80 space-y-4">
        <Card className="bg-surface/90 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">Trajectory Simulation</h3>
            <Link to={`/negotiate/${id}`}>
              <Button variant="secondary" className="px-2 py-1 text-[10px]">Back</Button>
            </Link>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider">Maneuver</p>
              <div className="mt-1 font-mono text-sm text-text-primary">{data.maneuvering_norad_id} — {data.maneuver_type}</div>
              <div className="text-xs text-text-secondary mt-1">{data.delta_v_mps.toFixed(2)} m/s at {new Date(data.execution_time_utc).toLocaleTimeString()}</div>
            </div>
            
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider">Distance (km)</p>
              <div className="mt-1 flex justify-between font-mono text-sm">
                <span className="text-text-secondary line-through">{step.nominal_distance_km.toFixed(2)}</span>
                <span className={step.maneuvered_distance_km < 5.0 ? "text-danger" : "text-success-light"}>
                  {step.maneuvered_distance_km.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-border-muted">
              <label className="text-xs text-text-muted uppercase tracking-wider flex justify-between">
                <span>Timeline</span>
                <span className="font-mono text-text-primary">{new Date(step.timestamp_utc).toLocaleTimeString()}</span>
              </label>
              {data.steps.length > 1 ? (
                <>
                  <input
                    type="range"
                    className="w-full mt-2 accent-accent"
                    min={0}
                    max={data.steps.length - 1}
                    value={stepIndex}
                    onChange={e => setStepIndex(parseInt(e.target.value, 10))}
                  />
                  <div className="flex justify-between text-[10px] text-text-muted font-mono mt-1">
                    <span>-{Math.abs(data.steps[0].t_seconds / 60).toFixed(0)}m</span>
                    {step.is_post_burn && <Badge status="success">Post-Burn</Badge>}
                    <span>+{(data.steps[data.steps.length - 1].t_seconds / 60).toFixed(0)}m</span>
                  </div>
                </>
              ) : (
                <div className="mt-4 text-center text-xs text-text-muted">
                  Timeline unavailable
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
