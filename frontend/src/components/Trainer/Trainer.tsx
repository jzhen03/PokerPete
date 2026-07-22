import { useCallback, useEffect, useState } from "react";
import { api, unwrap } from "../../api/client";

type Mode = "push-fold" | "tree";
type Action = "fold" | "open" | "shove";

interface Spot {
  stack_bb: number;
  hero_class: string;
  hero_combo: string;
}

interface Grade {
  correct: boolean;
  correct_action: Action;
  frequencies: Partial<Record<Action, number>>;
  caveat?: string;
}

const ACTIONS_BY_MODE: Record<Mode, Action[]> = {
  "push-fold": ["fold", "shove"],
  tree: ["fold", "open", "shove"],
};

export function Trainer() {
  const [mode, setMode] = useState<Mode>("push-fold");
  const [spot, setSpot] = useState<Spot | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const nextSpot = useCallback(async (m: Mode) => {
    setLoading(true);
    setError(null);
    setGrade(null);
    try {
      const path = m === "push-fold" ? "/trainer/push-fold/spot" : "/trainer/preflop-tree/spot";
      const response = await api.GET(path);
      setSpot(unwrap(response));
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to fetch a spot");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setScore({ correct: 0, total: 0 });
    void nextSpot(mode);
  }, [mode, nextSpot]);

  async function answer(action: Action) {
    if (!spot || loading) return;
    setLoading(true);
    setError(null);
    try {
      let result: Grade;
      if (mode === "push-fold") {
        if (action === "open") return; // not a valid push/fold action
        const response = await api.POST("/trainer/push-fold/grade", {
          body: { stack_bb: spot.stack_bb, hero_class: spot.hero_class, action },
        });
        const body = unwrap(response);
        result = {
          correct: body.correct,
          correct_action: body.correct_action,
          frequencies: { shove: body.shove_frequency },
        };
      } else {
        const response = await api.POST("/trainer/preflop-tree/grade", {
          body: { stack_bb: spot.stack_bb, hero_class: spot.hero_class, action },
        });
        const body = unwrap(response);
        result = {
          correct: body.correct,
          correct_action: body.correct_action,
          frequencies: body.action_frequencies as Partial<Record<Action, number>>,
          caveat: body.caveat,
        };
      }
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
      <div className="field-row">
        <div className="field">
          <label htmlFor="mode">Mode</label>
          <select id="mode" value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            <option value="push-fold">Push/Fold (shallow stacks)</option>
            <option value="tree">Open / 3bet / Shove (deeper stacks)</option>
          </select>
        </div>
      </div>

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
              {ACTIONS_BY_MODE[mode].map((action) => (
                <button
                  key={action}
                  className={action === "fold" ? "secondary" : "primary"}
                  onClick={() => void answer(action)}
                  disabled={loading}
                >
                  {action[0].toUpperCase() + action.slice(1)}
                </button>
              ))}
            </div>
          ) : (
            <div style={{ marginTop: 16 }}>
              <p style={{ color: grade.correct ? "var(--status-good)" : "var(--status-critical)" }}>
                {grade.correct ? "Correct" : "Incorrect"} — GTO action: {grade.correct_action} (
                {Object.entries(grade.frequencies)
                  .map(([action, freq]) => `${action} ${((freq ?? 0) * 100).toFixed(0)}%`)
                  .join(", ")}
                )
              </p>
              {grade.caveat && <p className="backend-status">{grade.caveat}</p>}
              <button className="primary" onClick={() => void nextSpot(mode)} disabled={loading}>
                Next spot
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
