import pytest

from pokerpete.engine.cards import parse_cards
from pokerpete.engine.evaluator import compare, hand_type, score


def _score(text: str) -> int:
    return score(parse_cards(text))


@pytest.mark.parametrize(
    "weaker,stronger",
    [
        ("2c 3c 4d 5h 9s", "2c 2d 4d 5h 9s"),  # high card < pair
        ("2c 2d 4d 5h 9s", "2c 2d 4c 4h 9s"),  # pair < two pair
        ("2c 2d 4c 4h 9s", "2c 2d 2h 4h 9s"),  # two pair < trips
        ("6c 7c 8d 9h Th", "6c 2d 2h 2c 2s"),  # straight < quads
        ("2c 2d 2h 4h 9s", "6c 7c 8d 9h Th"),  # trips < straight
        ("6c 7c 8d 9h Th", "2c 4c 6c 8c Tc"),  # straight < flush
        ("2c 4c 6c 8c Tc", "2c 2d 2h 4h 4d"),  # flush < full house
        ("2c 2d 2h 4h 4d", "2c 2d 2h 2s 9c"),  # full house < quads
        ("2c 2d 2h 2s 9c", "6c 7c 8c 9c Tc"),  # quads < straight flush
        ("6c 7c 8c 9c Tc", "9c Tc Jc Qc Kc"),  # straight flush < higher straight flush
    ],
)
def test_hand_rank_ordering(weaker: str, stronger: str) -> None:
    assert _score(weaker) < _score(stronger)


def test_hand_type_labels() -> None:
    assert hand_type(_score("9c Tc Jc Qc Kc")) == "Straight Flush"
    assert hand_type(_score("2c 2d 2h 2s 9c")) == "Quads"
    assert hand_type(_score("2c 2d 2h 4h 4d")) == "Full House"
    assert hand_type(_score("2c 4c 6c 8c Tc")) == "Flush"
    assert hand_type(_score("6c 7d 8c 9h Tc")) == "Straight"
    assert hand_type(_score("2c 2d 2h 4h 9s")) == "Trips"
    assert hand_type(_score("2c 2d 4c 4h 9s")) == "Two Pair"
    assert hand_type(_score("2c 2d 4d 5h 9s")) == "Pair"
    assert hand_type(_score("2c 3d 5h 7s 9c")) == "High Card"


@pytest.mark.parametrize("count", [5, 6, 7])
def test_score_accepts_five_to_seven_cards(count: int) -> None:
    cards = parse_cards("As Kd 7h 2c 9s Jd Tc")[:count]
    score(cards)  # should not raise


@pytest.mark.parametrize("count", [4, 8])
def test_score_rejects_other_counts(count: int) -> None:
    cards = (parse_cards("As Kd 7h 2c 9s Jd Tc") * 2)[:count]
    with pytest.raises(ValueError):
        score(cards)


def test_compare_picks_best_five_of_seven() -> None:
    # Hero has set of kings on this board; villain has top two pair (K7).
    board = parse_cards("Ks 7h 2c 9s Jd")
    hero = parse_cards("Kd Kh")
    villain = parse_cards("7d 9d")
    assert compare(hero, villain, board) == 1
    assert compare(villain, hero, board) == -1


def test_compare_tie() -> None:
    board = parse_cards("As Ks Qs Js Ts")  # board itself is a royal flush
    hero = parse_cards("2c 3c")
    villain = parse_cards("4d 5d")
    assert compare(hero, villain, board) == 0
