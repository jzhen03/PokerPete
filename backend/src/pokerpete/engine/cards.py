from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "cdhs"


@dataclass(frozen=True, slots=True)
class Card:
    rank: int  # 0=2 .. 12=A
    suit: int  # 0=c, 1=d, 2=h, 3=s

    def __post_init__(self) -> None:
        if not 0 <= self.rank <= 12:
            raise ValueError(f"invalid rank: {self.rank}")
        if not 0 <= self.suit <= 3:
            raise ValueError(f"invalid suit: {self.suit}")

    @classmethod
    def from_str(cls, text: str) -> Card:
        if len(text) != 2:
            raise ValueError(f"invalid card: {text!r}")
        rank_ch, suit_ch = text[0].upper(), text[1].lower()
        try:
            rank = RANKS.index(rank_ch)
            suit = SUITS.index(suit_ch)
        except ValueError as exc:
            raise ValueError(f"invalid card: {text!r}") from exc
        return cls(rank, suit)

    def __str__(self) -> str:
        return RANKS[self.rank] + SUITS[self.suit]

    def __repr__(self) -> str:
        return f"Card({self!s})"

    @property
    def index(self) -> int:
        """Position 0..51 in a canonical rank-major ordering."""
        return self.rank * 4 + self.suit

    @property
    def bit(self) -> int:
        return 1 << self.index


def parse_cards(text: str) -> tuple[Card, ...]:
    """Parse a card string into Cards. Accepts space/comma-separated groups
    ("As Kd 7h") or unseparated runs ("AsKd7h")."""
    tokens: list[str] = []
    for chunk in text.replace(",", " ").split():
        if len(chunk) % 2 != 0:
            raise ValueError(f"invalid card sequence: {chunk!r}")
        tokens.extend(chunk[i : i + 2] for i in range(0, len(chunk), 2))
    return tuple(Card.from_str(t) for t in tokens)


FULL_DECK: tuple[Card, ...] = tuple(
    Card(rank, suit) for suit in range(4) for rank in range(13)
)
FULL_MASK = (1 << 52) - 1


class Deck:
    """The set of cards not yet accounted for (dealt, exposed, or removed)."""

    def __init__(self, dead: Iterable[Card] = ()) -> None:
        self._mask = FULL_MASK
        for card in dead:
            self.remove(card)

    def remove(self, card: Card) -> None:
        self._mask &= ~card.bit

    def contains(self, card: Card) -> bool:
        return bool(self._mask & card.bit)

    def remaining(self) -> list[Card]:
        return [card for card in FULL_DECK if self._mask & card.bit]

    def draw(self, n: int, rng: random.Random) -> list[Card]:
        return rng.sample(self.remaining(), n)
