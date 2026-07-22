import { useCallback, useEffect, useState } from "react";
import { api, unwrap } from "../../api/client";

interface Spot {
  stack_bb: number;
  hero_class: string;
  hero_combo: string;
}

interface Grade {
  correct: boolean;
  correct_action: "shove" | "fold";
  shove_frequency: number;
}

export function Trainer() {
  const [spot, setSpot] = useState<Spot | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const nextSpot = useCallback(async () => {
    setLoading(true);
    setError(null);
    setGrade(null);
    try {
      const response = await api.GET("/trainer/push-fold/spot");
      setSpot(unwrap(response));
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to fetch a spot");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void nextSpot();
  }, [nextSpot]);

  async function answer(action: "shove" | "fold") {
    if (!spot || loading) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.POST("/trainer/push-fold/grade", {
        body: { stack_bb: spot.stack_bb, hero_class: spot.hero_class, action },
      });
      const result = unwrap(response);
      setGrade(result);
      setScore((s) => ({ correct: s.correct + (result.correct ? 1 : 0), total: s.total + 1 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to grade answer");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <p className="backend-status">
        Score: {score.correct} / {score.total}
      </p>

      {error && <p className="error-text">{error}</p>}

      {spot && (
        <>
          <div className="stat-row">
            <div className="stat">
              <span className="value">{spot.hero_combo}</span>
              <span className="label">Hand (SB)</span>
            </div>
            <div className="stat">
              <span className="value">{spot.stack_bb}bb</span>
              <span className="label">Effective stack</span>
            </div>
          </div>

          {!grade ? (
            <div className="field-row" style={{ marginTop: 16 }}>
              <button className="primary" onClick={() => answer("shove")} disabled={loading}>
                Shove
              </button>
              <button className="secondary" onClick={() => answer("fold")} disabled={loading}>
                Fold
              </button>
            </div>
          ) : (
            <div style={{ marginTop: 16 }}>
              <p style={{ color: grade.correct ? "var(--status-good)" : "var(--status-critical)" }}>
                {grade.correct ? "Correct" : "Incorrect"} — GTO action: {grade.correct_action} (
                {(grade.shove_frequency * 100).toFixed(0)}% shove frequency)
              </p>
              <button className="primary" onClick={() => void nextSpot()} disabled={loading}>
                Next spot
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
