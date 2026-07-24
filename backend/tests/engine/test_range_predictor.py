import pytest

from pokerpete.engine.data.player_type_modifiers import PLAYER_TYPE_MODIFIERS
from pokerpete.engine.data.range_predictor_baselines import BASELINE_NOTATION, baseline_range
from pokerpete.engine.range_predictor import (
    RangePredictorInputs,
    _narrow,
    _weighted_combo_count,
    apply_bet_sizing,
    apply_player_type,
    compute_range,
    diff_ranges,
)


def test_baseline_covers_all_position_action_pairs() -> None:
    for position in ("SB", "BB"):
        for action in ("open", "threebet", "fourbet", "coldcall", "limp"):
            weights = baseline_range(position, action)
            assert weights, f"no baseline for {(position, action)}"
            assert all(0.0 < w <= 1.0 for w in weights.values())
    assert len(BASELINE_NOTATION) == 10


def test_diff_ranges_added_removed_reweighted() -> None:
    before = {"AA": 1.0, "KK": 1.0, "QQ": 0.5}
    after = {"AA": 1.0, "QQ": 1.0, "JJ": 1.0}
    diff = diff_ranges(before, after)
    assert diff.added == {"JJ": 1.0}
    assert diff.removed == {"KK": 1.0}
    assert diff.reweighted == {"QQ": (0.5, 1.0)}


def test_loose_passive_widens_combo_count() -> None:
    base = baseline_range("SB", "open")
    result = apply_player_type(base, "loose_passive")
    assert _weighted_combo_count(result.range) == pytest.approx(
        _weighted_combo_count(base) * 1.35, rel=0.02
    )
    assert result.diff.added


def test_tight_passive_narrows_combo_count() -> None:
    base = baseline_range("SB", "open")
    result = apply_player_type(base, "tight_passive")
    assert _weighted_combo_count(result.range) == pytest.approx(
        _weighted_combo_count(base) * 0.70, rel=0.02
    )
    assert result.diff.removed


def test_polarized_narrow_protects_speculative_hands() -> None:
    # A hand-built range with a clear top/middle/speculative split: AA/KK
    # (top), QQ/JJ/AQo (middle), 76s/54s (speculative). A "linear" narrow
    # should cut the weakest hands first (76s/54s go before AA/KK); a
    # "polarized" narrow should protect the speculative hands and cut the
    # middle instead.
    base = {"AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "AQo": 1.0, "76s": 1.0, "54s": 1.0}

    linear = _narrow(base, target_count=30.0, shift="linear")
    polarized = _narrow(base, target_count=30.0, shift="polarized")

    assert "76s" not in linear or linear.get("76s", 0) < 1.0  # weakest-first cuts speculative hands
    assert polarized.get("76s", 0) == 1.0
    assert polarized.get("54s", 0) == 1.0
    assert polarized.get("AA", 0) == 1.0


def test_bet_sizing_is_noop_for_coldcall_and_limp() -> None:
    base = baseline_range("SB", "open")
    for action in ("coldcall", "limp"):
        for bucket in (None, "small", "medium", "large"):
            result = apply_bet_sizing(base, action, bucket, reliability=90)
            assert result.range == base
            assert result.diff.added == {}
            assert result.diff.removed == {}
            assert result.diff.reweighted == {}


def test_bet_sizing_is_noop_when_sizing_bucket_is_none() -> None:
    base = baseline_range("SB", "open")
    result = apply_bet_sizing(base, "open", None, reliability=90)
    assert result.range == base


def test_large_threebet_sizing_narrows_more_than_small() -> None:
    base = baseline_range("SB", "threebet")
    small = apply_bet_sizing(base, "threebet", "small", reliability=90)
    large = apply_bet_sizing(base, "threebet", "large", reliability=90)
    assert _weighted_combo_count(large.range) <= _weighted_combo_count(small.range)


def test_high_reliability_narrows_more_than_low_reliability() -> None:
    base = baseline_range("SB", "open")
    low = apply_bet_sizing(base, "open", "large", reliability=10)
    high = apply_bet_sizing(base, "open", "large", reliability=90)
    assert _weighted_combo_count(high.range) < _weighted_combo_count(low.range)

    # a filler (non-value, non-speculative) hand should be barely touched at
    # low reliability but sharply cut at high reliability.
    filler_candidates = set(low.diff.reweighted) & set(high.diff.reweighted)
    assert filler_candidates, "expected at least one filler hand reweighted at both levels"
    sample = next(iter(filler_candidates))
    _, low_after = low.diff.reweighted[sample]
    _, high_after = high.diff.reweighted[sample]
    assert high_after < low_after


def test_reliability_zero_leaves_bet_sizing_unchanged() -> None:
    base = baseline_range("SB", "open")
    result = apply_bet_sizing(base, "open", "large", reliability=0)
    assert result.range == base
    assert result.diff.added == {}
    assert result.diff.removed == {}
    assert result.diff.reweighted == {}


def test_reliability_hundred_fully_drops_filler() -> None:
    base = baseline_range("SB", "open")
    result = apply_bet_sizing(base, "open", "large", reliability=100)
    assert result.diff.removed


@pytest.mark.parametrize(
    ("player_type", "expected_default"),
    [
        ("loose_passive", 80),
        ("tight_passive", 80),
        ("loose_aggressive", 35),
        ("tight_aggressive", 55),
        ("balanced", 15),
    ],
)
def test_default_reliability_matches_spec_table(player_type: str, expected_default: int) -> None:
    assert PLAYER_TYPE_MODIFIERS[player_type].default_reliability == expected_default


def test_compute_range_pipeline_runs_three_named_stages_in_order() -> None:
    result = compute_range(
        RangePredictorInputs(position="SB", action="open", player_type="balanced")
    )
    assert [stage.name for stage in result.stages] == ["position", "player_type", "bet_sizing"]


def test_compute_range_defaults_reliability_from_player_type() -> None:
    result = compute_range(
        RangePredictorInputs(position="SB", action="open", player_type="loose_aggressive")
    )
    assert result.reliability_used == 35
    assert result.reliability_default == 35
    assert result.reliability_is_customized is False


def test_compute_range_reliability_customized_flag() -> None:
    same_as_default = compute_range(
        RangePredictorInputs(
            position="SB", action="open", player_type="loose_aggressive", reliability=35
        )
    )
    assert same_as_default.reliability_is_customized is False

    overridden = compute_range(
        RangePredictorInputs(
            position="SB", action="open", player_type="loose_aggressive", reliability=80
        )
    )
    assert overridden.reliability_used == 80
    assert overridden.reliability_is_customized is True
