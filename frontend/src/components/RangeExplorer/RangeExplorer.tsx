import { useEffect, useState } from "react";
import { api, unwrap } from "../../api/client";
import { RangeGrid } from "../RangeGrid/RangeGrid";

export function RangeExplorer() {
  const [notation, setNotation] = useState("AA-TT,AKs,AQo+,76s");
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [comboCount, setComboCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const trimmed = notation.trim();
    if (!trimmed) {
      setWeights({});
      setComboCount(0);
      setError(null);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const response = await api.POST("/ranges/parse", { body: { notation: trimmed } });
        if (cancelled) return;
        const body = unwrap(response);
        setWeights(body.classes);
        setComboCount(body.combo_count);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "failed to parse range");
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [notation]);

  return (
    <div className="panel">
      <div className="field-row">
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="notation">Range notation</label>
          <input id="notation" value={notation} onChange={(e) => setNotation(e.target.value)} />
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <p className="backend-status">{comboCount.toFixed(1)} / 1326 combos</p>
      <RangeGrid weights={weights} />
    </div>
  );
}
