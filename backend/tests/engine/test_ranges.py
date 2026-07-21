from pokerpete.engine.cards import Card
from pokerpete.engine.ranges import combo_count, intersect, parse, remove_blockers, scale, union


def test_parse_pocket_pair_has_six_combos() -> None:
    r = parse("AA")
    assert len(r) == 6
    assert all(weight == 1.0 for weight in r.values())


def test_parse_suited_has_four_combos() -> None:
    assert len(parse("AKs")) == 4


def test_parse_offsuit_has_twelve_combos() -> None:
    assert len(parse("AKo")) == 12


def test_parse_exact_combo() -> None:
    r = parse("AsAd")
    assert len(r) == 1
    (combo,) = r.keys()
    assert combo == frozenset({Card.from_str("As"), Card.from_str("Ad")})


def test_parse_is_cached() -> None:
    assert parse("AA") is parse("AA")


def test_combo_count() -> None:
    assert combo_count(parse("AA")) == 6.0
    assert combo_count(parse("AKs")) == 4.0
    assert combo_count(parse("AA,AKs")) == 10.0


def test_union_takes_max_weight() -> None:
    a = scale(parse("AA"), 0.5)
    b = parse("AA")
    result = union(a, b)
    assert all(weight == 1.0 for weight in result.values())


def test_intersect_takes_min_weight_and_common_combos() -> None:
    a = parse("AA,KK")
    b = parse("AA,QQ")
    result = intersect(a, b)
    assert len(result) == 6  # only AA is common
    assert combo_count(result) == 6.0


def test_scale_clamps_to_unit_interval() -> None:
    r = scale(parse("AA"), 2.0)
    assert all(weight == 1.0 for weight in r.values())
    r2 = scale(parse("AA"), 0.25)
    assert all(weight == 0.25 for weight in r2.values())


def test_remove_blockers_drops_conflicting_combos() -> None:
    r = remove_blockers(parse("AA"), [Card.from_str("As")])
    # 3 of the 6 AA combos include the As card and should be removed.
    assert len(r) == 3
    assert all(Card.from_str("As") not in combo for combo in r)
