import type { CSSProperties } from "react";
import "./RangeGrid.css";

const RANKS_DESC = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

function handClassAt(row: number, col: number): string {
  if (row === col) return RANKS_DESC[row] + RANKS_DESC[row];
  if (row < col) return RANKS_DESC[row] + RANKS_DESC[col] + "s";
  return RANKS_DESC[col] + RANKS_DESC[row] + "o";
}

// Sequential blue ramp, light -> dark, one hue for magnitude (weight 0..1).
function cellStyle(weight: number): CSSProperties | undefined {
  if (weight <= 0) return undefined;
  return {
    background: `color-mix(in oklab, var(--seq-150) ${(1 - weight) * 100}%, var(--seq-700))`,
    color: weight >= 0.5 ? "#ffffff" : "var(--text-primary)",
  };
}

interface RangeGridProps {
  /** hand-class ("AA", "AKs", "AKo", ...) -> weight in [0, 1] */
  weights: Record<string, number>;
}

export function RangeGrid({ weights }: RangeGridProps) {
  return (
    <div className="range-grid" role="img" aria-label="13 by 13 starting hand range grid">
      {RANKS_DESC.flatMap((_, row) =>
        RANKS_DESC.map((_, col) => {
          const handClass = handClassAt(row, col);
          const weight = weights[handClass] ?? 0;
          return (
            <div
              key={handClass}
              className="range-cell"
              style={cellStyle(weight)}
              title={`${handClass} — ${Math.round(weight * 100)}%`}
            >
              {handClass}
            </div>
          );
        }),
      )}
    </div>
  );
}
