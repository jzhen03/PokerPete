"""Hand-authored HU preflop baseline ranges by (position, action) -- the seed
of the Range Predictor pipeline (engine/range_predictor.py).

These are NOT solver output: preflop_solver.py/preflop_tree_solver.py compute
equilibria for a specific stack depth via fictitious play, not a
stack-depth-independent "reasonable range" table, and no such baseline table
exists elsewhere in the repo. These are commonly-cited ~100bb HU cash
approximations, hand-typed as range notation and parsed on demand via
engine.ranges.parse (which is itself lru_cached). Treat as a tunable starting
point for a heuristic study tool, not ground truth -- editing these strings
is the intended way to retune the Position stage without touching any
pipeline logic.

BB "open" represents isolating over an SB limp (BB acts second preflop in HU,
so it never opens in the strict sense); BB "limp" represents BB's checking
range when SB limps. Kept under the same 5-action vocabulary as SB for a
simpler, symmetric UI rather than modeling exact HU action-order legality.
"""

from pokerpete.engine import ranges

BASELINE_NOTATION: dict[tuple[str, str], str] = {
    ("SB", "open"): "22+,A2s+,A2o+,K2s+,K5o+,Q6s+,Q8o+,J7s+,J9o+,T7s+,98s,87s,76s,65s,54s",
    ("SB", "limp"): "22-66,A2s-A9s,A2o-A9o,K2s-K9s,76s,65s,54s",
    ("SB", "threebet"): "TT+,AQs+,AKo,A2s-A5s,K9s+,QTs+,JTs",
    ("SB", "fourbet"): "QQ+,AKs,AKo,A5s",
    ("SB", "coldcall"): "77-JJ,ATs-AQs,AJo+,KTs+,QJs",
    ("BB", "open"): "22+,A2s+,A7o+,K8s+,KTo+,Q9s+,QTo+,J9s+,T8s+,97s,87s,76s,65s",
    ("BB", "limp"): "22-99,A2s-A9s,K7s+,QTs+",
    ("BB", "threebet"): "88+,ATs+,KJs+,AJo+,A2s-A5s,K9s+",
    ("BB", "fourbet"): "JJ+,AKs,AKo,A2s-A4s",
    ("BB", "coldcall"): "22+,A2s+,A8o+,K9s+,KJo+,QTs+,JTs,T9s,98s,87s",
}


def baseline_range(position: str, action: str) -> dict[str, float]:
    """Hand-class weights (0-1 each) for this position+action baseline."""
    notation = BASELINE_NOTATION[(position, action)]
    return dict(ranges.class_weights(ranges.parse(notation)))
