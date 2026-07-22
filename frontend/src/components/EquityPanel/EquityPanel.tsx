import { useState } from "react";
import { api, unwrap } from "../../api/client";

export function EquityPanel() {
  const [hero, setHero] = useState("AsAd");
  const [villain, setVillain] = useState("KK");
  const [board, setBoard] = useState("");
  const [result, setResult] = useState<{ win: number; tie: number; lose: number; equity: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.POST("/equity/calculate", {
        body: { hero, villain, board, iterations: 5000 },
      });
      setResult(unwrap(response));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "failed to calculate equity");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="field-row">
        <div className="field">
          <label htmlFor="hero">Hero</label>
          <input id="hero" value={hero} onChange={(e) => setHero(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="villain">Villain</label>
          <input id="villain" value={villain} onChange={(e) => setVillain(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="board">Board (optional)</label>
          <input
            id="board"
            placeholder="e.g. As Kd 7h"
            value={board}
            onChange={(e) => setBoard(e.target.value)}
          />
        </div>
        <button className="primary" onClick={calculate} disabled={loading}>
          {loading ? "Calculating…" : "Calculate"}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <div className="stat-row">
          <div className="stat">
            <span className="value">{(result.equity * 100).toFixed(1)}%</span>
            <span className="label">Hero equity</span>
          </div>
          <div className="stat">
            <span className="value">{(result.win * 100).toFixed(1)}%</span>
            <span className="label">Win</span>
          </div>
          <div className="stat">
            <span className="value">{(result.tie * 100).toFixed(1)}%</span>
            <span className="label">Tie</span>
          </div>
          <div className="stat">
            <span className="value">{(result.lose * 100).toFixed(1)}%</span>
            <span className="label">Lose</span>
          </div>
        </div>
      )}
    </div>
  );
}
