const RANKS = "23456789TJQKA";
const SUITS = "cdhs";

export interface CardToken {
  rank: string;
  suit: string;
}

function parseCardToken(token: string): CardToken | null {
  if (token.length !== 2) return null;
  const rank = token[0].toUpperCase();
  const suit = token[1].toLowerCase();
  if (!RANKS.includes(rank) || !SUITS.includes(suit)) return null;
  return { rank, suit };
}

/**
 * Parses a free-text card list, accepting both space/comma-separated tokens
 * ("As Kd", "As, Kd") and bare concatenated tokens ("AsKd"). Returns null if
 * any token fails to parse as a card.
 */
export function parseCardList(value: string): CardToken[] | null {
  const trimmed = value.trim();
  if (trimmed === "") return [];
  const parts = /[\s,]/.test(trimmed) ? trimmed.split(/[\s,]+/) : (trimmed.match(/.{1,2}/g) ?? []);
  const cards: CardToken[] = [];
  for (const part of parts) {
    const card = parseCardToken(part);
    if (!card) return null;
    cards.push(card);
  }
  return cards;
}

/**
 * Parses hero/villain-style input as an exact two-card hand. Range notation
 * ("AA", "AKs+") never parses as a card token pair, so this returns null for
 * anything that isn't a specific combo.
 */
export function parseExactHand(value: string): CardToken[] | null {
  const cards = parseCardList(value);
  if (!cards || cards.length !== 2) return null;
  const [a, b] = cards;
  if (a.rank === b.rank && a.suit === b.suit) return null;
  return cards;
}
