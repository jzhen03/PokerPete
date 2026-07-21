import random

import pytest

from pokerpete.engine.cards import Card, Deck, parse_cards


def test_from_str_roundtrip() -> None:
    for text in ["As", "Kd", "Th", "2c"]:
        assert str(Card.from_str(text)) == text


def test_from_str_case_insensitive_rank_and_suit() -> None:
    assert Card.from_str("as") == Card.from_str("As")


@pytest.mark.parametrize("text", ["A", "Asx", "1s", "Ax", ""])
def test_from_str_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        Card.from_str(text)


def test_equality_and_hash() -> None:
    assert Card.from_str("As") == Card.from_str("As")
    assert len({Card.from_str("As"), Card.from_str("As"), Card.from_str("Ad")}) == 2


def test_parse_cards_spaced_and_unspaced() -> None:
    expected = (Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h"))
    assert parse_cards("As Kd 7h") == expected
    assert parse_cards("AsKd7h") == expected
    assert parse_cards("As, Kd, 7h") == expected


def test_deck_remove_and_remaining() -> None:
    deck = Deck(dead=[Card.from_str("As"), Card.from_str("Kd")])
    remaining = deck.remaining()
    assert len(remaining) == 50
    assert Card.from_str("As") not in remaining
    assert Card.from_str("Kd") not in remaining


def test_deck_draw_no_duplicates_and_excludes_dead() -> None:
    dead = [Card.from_str("As"), Card.from_str("Kd")]
    deck = Deck(dead=dead)
    drawn = deck.draw(5, random.Random(0))
    assert len(drawn) == 5
    assert len(set(drawn)) == 5
    assert not set(drawn) & set(dead)
