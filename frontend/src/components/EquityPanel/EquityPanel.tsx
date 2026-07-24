import { useEffect, useState } from "react";
import { api, unwrap } from "../../api/client";
import { CardRow } from "../PlayingCard/PlayingCard";
import { parseCardList, parseExactHand } from "../../lib/cards";

const VALID_BOARD_LENGTHS = new Set([0, 3, 4, 5]);

function HandDisplay({ label, value }: { label: string; value: string }) {
  const cards = parseExactHand(value);
  return (
    <div className="hand-display">
      <span className="hand-display-label">{label}</span>
      {cards ? <CardRow cards={cards} /> : <span className="range-badge">{value || "—"}</span>}
    </div>
  );
}

function BoardDisplay({ value }: { value: string }) {
  const cards = parseCardList(value);
  return (
    <div className="hand-display">
      <span className="hand-display-label">Board</span>
      {cards === null ? (
        <span className="range-badge">{value}</span>
      ) : cards.length > 0 ? (
        <CardRow cards={cards} />
      ) : (
        <span className="range-badge">preflop</span>
      )}
    </div>
  );
}

export function EquityPanel() {
  const [hero, setHero] = useState("AsAd");
  const [villain, setVillain] = useState("KK");
  const [board, setBoard] = useState("");
  const [result, setResult] = useState<{ win: number; tie: number; lose: number; equity: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Auto-calculates once hero, villain, and board all form a playable state
  // (board is preflop/flop/turn/river length) -- no manual "Calculate" click
  // required, mirroring RangeExplorer's live-parse-on-type pattern.
  useEffect(() => {
    const heroTrimmed = hero.trim();
    const villainTrimmed = villain.trim();
    const boardCards = parseCardList(board);
    const boardReady = boardCards !== null && VALID_BOARD_LENGTHS.has(boardCards.length);

    if (!heroTrimmed || !villainTrimmed || !boardReady) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await api.POST("/equity/calculate", {
          body: { hero: heroTrimmed, villain: villainTrimmed, board, iterations: 5000 },
        });
        if (cancelled) return;
        setResult(unwrap(response));
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setResult(null);
        setError(err instanceof Error ? err.message : "failed to calculate equity");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [hero, villain, board]);

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
      </div>

      {loading && <p className="equity-status">Calculating…</p>}

      <div className="equity-visual">
        <div className="equity-hands">
          <HandDisplay label="Hero" value={hero} />
          <span className="vs-label">vs</span>
          <HandDisplay label="Villain" value={villain} />
        </div>
        <BoardDisplay value={board} />
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
