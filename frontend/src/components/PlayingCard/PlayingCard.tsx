import type { CardToken } from "../../lib/cards";
import "./PlayingCard.css";

const SUIT_SYMBOLS: Record<string, string> = {
  s: "♠",
  h: "♥",
  d: "♦",
  c: "♣",
};

const RED_SUITS = new Set(["h", "d"]);

export function PlayingCard({ card }: { card: CardToken }) {
  const isRed = RED_SUITS.has(card.suit);
  return (
    <div className={`playing-card ${isRed ? "red" : "black"}`}>
      <span className="rank">{card.rank}</span>
      <span className="suit">{SUIT_SYMBOLS[card.suit]}</span>
    </div>
  );
}

export function CardRow({ cards }: { cards: CardToken[] }) {
  return (
    <div className="card-row">
      {cards.map((card) => (
        <PlayingCard key={`${card.rank}${card.suit}`} card={card} />
      ))}
    </div>
  );
}
