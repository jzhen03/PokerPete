import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, unwrap } from "../../api/client";
import { RangeGrid } from "../RangeGrid/RangeGrid";
import type { components } from "../../api/schema";

type Position = components["schemas"]["RangePredictRequest"]["position"];
type Action = components["schemas"]["RangePredictRequest"]["action"];
type PlayerType = components["schemas"]["RangePredictRequest"]["player_type"];
type SizingBucket = NonNullable<components["schemas"]["RangePredictRequest"]["sizing_bucket"]>;

const POSITIONS: { value: Position; label: string }[] = [
  { value: "SB", label: "SB" },
  { value: "BB", label: "BB" },
];

const ACTIONS: { value: Action; label: string }[] = [
  { value: "open", label: "Open raise" },
  { value: "threebet", label: "3-bet" },
  { value: "fourbet", label: "4-bet" },
  { value: "coldcall", label: "Cold call" },
  { value: "limp", label: "Limp" },
];

const PLAYER_TYPES: { value: PlayerType; label: string }[] = [
  { value: "loose_passive", label: "Loose-Passive (calling station)" },
  { value: "tight_passive", label: "Tight-Passive (nit)" },
  { value: "loose_aggressive", label: "Loose-Aggressive (LAG)" },
  { value: "tight_aggressive", label: "Tight-Aggressive (TAG)" },
  { value: "balanced", label: "Balanced / solver-influenced" },
];

const SIZING_BUCKETS: { value: SizingBucket; label: string }[] = [
  { value: "small", label: "Small (<33% pot)" },
  { value: "medium", label: "Medium (33-66%)" },
  { value: "large", label: "Large (66-100%+)" },
];

const NON_SIZING_ACTIONS = new Set<Action>(["coldcall", "limp"]);

export function RangePredictor() {
  const [position, setPosition] = useState<Position>("SB");
  const [action, setAction] = useState<Action>("open");
  const [playerType, setPlayerType] = useState<PlayerType>("balanced");
  const [sizingBucket, setSizingBucket] = useState<SizingBucket | null>(null);
  const [reliability, setReliability] = useState<number | null>(null);

  const [weights, setWeights] = useState<Record<string, number>>({});
  const [comboCount, setComboCount] = useState(0);
  const [reliabilityUsed, setReliabilityUsed] = useState(0);
  const [reliabilityDefault, setReliabilityDefault] = useState(0);
  const [isCustomized, setIsCustomized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [saveName, setSaveName] = useState("");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const sizingDisabled = NON_SIZING_ACTIONS.has(action);

  useEffect(() => {
    if (sizingDisabled) {
      setSizingBucket(null);
      setReliability(null);
    }
  }, [sizingDisabled]);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const response = await api.POST("/ranges/predict", {
          body: {
            position,
            action,
            player_type: playerType,
            sizing_bucket: sizingDisabled ? null : sizingBucket,
            reliability: sizingDisabled ? null : reliability,
          },
        });
        if (cancelled) return;
        const body = unwrap(response);
        setWeights(body.classes);
        setComboCount(body.combo_count);
        setReliabilityUsed(body.reliability_used);
        setReliabilityDefault(body.reliability_default);
        setIsCustomized(body.reliability_is_customized);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "failed to predict range");
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [position, action, playerType, sizingBucket, reliability, sizingDisabled]);

  const savedRanges = useQuery({
    queryKey: ["saved-ranges"],
    queryFn: async () => unwrap(await api.GET("/ranges")),
  });

  async function handleSave() {
    if (!saveName.trim()) return;
    try {
      await unwrap(
        await api.POST("/ranges", {
          body: {
            name: saveName.trim(),
            source: "predictor",
            classes: weights,
            position,
            factors: {
              position,
              action,
              player_type: playerType,
              sizing_bucket: sizingDisabled ? null : sizingBucket,
              reliability: reliabilityUsed,
            },
          },
        }),
      );
      setSaveMessage(`Saved "${saveName.trim()}"`);
      setSaveName("");
      queryClient.invalidateQueries({ queryKey: ["saved-ranges"] });
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "failed to save range");
    }
  }

  async function handleLoad(rangeId: number) {
    try {
      const detail = unwrap(await api.GET("/ranges/{range_id}", { params: { path: { range_id: rangeId } } }));
      const factors = detail.factors as Partial<components["schemas"]["RangePredictRequest"]> | null;
      if (factors) {
        if (factors.position) setPosition(factors.position);
        if (factors.action) setAction(factors.action);
        if (factors.player_type) setPlayerType(factors.player_type);
        setSizingBucket((factors.sizing_bucket as SizingBucket | null) ?? null);
        setReliability(factors.reliability ?? null);
      }
      setWeights(detail.classes);
      setComboCount(detail.combo_count);
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "failed to load range");
    }
  }

  function resetReliability() {
    setReliability(null);
  }

  return (
    <div className="panel">
      <div className="field-row">
        <div className="field">
          <label htmlFor="position">Position</label>
          <select id="position" value={position} onChange={(e) => setPosition(e.target.value as Position)}>
            {POSITIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="action">Action</label>
          <select id="action" value={action} onChange={(e) => setAction(e.target.value as Action)}>
            {ACTIONS.map((a) => (
              <option key={a.value} value={a.value}>
                {a.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="player-type">Player type</label>
          <select
            id="player-type"
            value={playerType}
            onChange={(e) => setPlayerType(e.target.value as PlayerType)}
          >
            {PLAYER_TYPES.map((pt) => (
              <option key={pt.value} value={pt.value}>
                {pt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label htmlFor="sizing-bucket">Bet sizing</label>
          <select
            id="sizing-bucket"
            disabled={sizingDisabled}
            value={sizingBucket ?? ""}
            onChange={(e) => setSizingBucket((e.target.value || null) as SizingBucket | null)}
          >
            <option value="">No sizing (n/a)</option>
            {SIZING_BUCKETS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ flex: 1, minWidth: 220 }}>
          <label htmlFor="reliability">
            Bet-sizing reliability{" "}
            {isCustomized && !sizingDisabled && <span className="customized-badge">customized</span>}
          </label>
          <div className="slider-row">
            <input
              id="reliability"
              type="range"
              min={0}
              max={100}
              disabled={sizingDisabled || !sizingBucket}
              value={reliabilityUsed}
              onChange={(e) => setReliability(Number(e.target.value))}
            />
            <span className="backend-status">{reliabilityUsed}</span>
            {isCustomized && !sizingDisabled && (
              <button type="button" className="secondary" onClick={resetReliability}>
                Reset to default ({reliabilityDefault})
              </button>
            )}
          </div>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <p className="backend-status">{comboCount.toFixed(1)} / 1326 combos</p>
      <RangeGrid weights={weights} />

      <div className="field-row" style={{ marginTop: 16 }}>
        <div className="field">
          <label htmlFor="save-name">Save this range as</label>
          <input id="save-name" value={saveName} onChange={(e) => setSaveName(e.target.value)} />
        </div>
        <button type="button" className="primary" onClick={handleSave} disabled={!saveName.trim()}>
          Save
        </button>
        <div className="field" style={{ flex: 1, minWidth: 220 }}>
          <label htmlFor="load-range">Load a saved range</label>
          <select
            id="load-range"
            value=""
            onChange={(e) => {
              const id = Number(e.target.value);
              if (id) handleLoad(id);
            }}
          >
            <option value="">Select a saved range…</option>
            {(savedRanges.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {saveMessage && <p className="backend-status">{saveMessage}</p>}
    </div>
  );
}
