import pytest

from pokerpete.engine.cards import parse_cards
from pokerpete.engine.equity import hand_vs_hand, range_vs_range
from pokerpete.engine.ranges import parse


def test_preflop_aa_vs_kk_matches_known_equity() -> None:
    # Published heads-up equity: AA vs KK preflop is ~82.1% for AA.
    result = hand_vs_hand(
        parse_cards("As Ad"), parse_cards("Ks Kd"), iterations=40_000, seed=42
    )
    assert result.equity == pytest.approx(0.821, abs=0.02)


def test_preflop_akss_vs_qq_is_close_to_a_coinflip() -> None:
    # Published heads-up equity: AKs vs QQ preflop is ~46% for AKs.
    result = hand_vs_hand(
        parse_cards("As Ks"), parse_cards("Qd Qc"), iterations=40_000, seed=7
    )
    assert result.equity == pytest.approx(0.46, abs=0.02)


def test_river_is_exact_and_deterministic() -> None:
    # A royal flush on the board plays for both hands regardless of hole cards.
    board = parse_cards("As Ks Qs Js Ts")
    hero = parse_cards("2c 3c")
    villain = parse_cards("4d 5d")
    result = hand_vs_hand(hero, villain, board)
    assert (result.win, result.tie, result.lose) == (0.0, 1.0, 0.0)
    # Re-running must give an identical result, since missing == 0 is exact, not sampled.
    assert hand_vs_hand(hero, villain, board) == result


def test_flop_exact_enumeration_matches_known_matchup() -> None:
    # Flush draw + overcards vs top pair (top kicker) on the flop; missing=2
    # (turn+river) is exact, so this is a deterministic ground-truth check.
    board = parse_cards("2h 7s Jc")
    hero = parse_cards("As Ks")  # nut flush draw + overcards
    villain = parse_cards("Jd Th")  # top pair, top kicker
    result = hand_vs_hand(hero, villain, board)
    assert result.equity == pytest.approx(0.2758, abs=0.001)


def test_hand_vs_hand_rejects_overlapping_cards() -> None:
    with pytest.raises(ValueError):
        hand_vs_hand(parse_cards("As Ad"), parse_cards("As Kd"))


def test_range_vs_range_single_combo_matches_hand_vs_hand() -> None:
    range_a = parse("AsAd")
    range_b = parse("KsKd")
    result = range_vs_range(range_a, range_b, iterations=8_000, seed=1)
    assert result.equity == pytest.approx(0.821, abs=0.03)


def test_range_vs_range_respects_board_blockers() -> None:
    board = parse_cards("Ac 7h 2d")
    result = range_vs_range(parse("AA"), parse("KK"), board, iterations=4_000, seed=3)
    # Hero's range no longer contains any combo with the board's lone ace removed;
    # with one ace on the board, hero's set-of-aces equity should still dominate.
    assert result.equity > 0.6


def test_range_vs_range_raises_when_ranges_fully_blocked() -> None:
    board = parse_cards("As Ad Ah Ac 2c")
    with pytest.raises(ValueError):
        range_vs_range(parse("AA"), parse("KK"), board)
