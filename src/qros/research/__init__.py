"""QROS Empirical Research, Stylized Facts, and Hypothesis Generation Package."""

from qros.research.capabilities import (
    evaluate_data_sufficiency,
    ClassSufficiencyResult,
)
from qros.research.stylized_facts import (
    StylizedFactsScanner,
    StylizedFactObservation,
)
from qros.research.hypothesis_generator import (
    generate_preregistered_hypotheses,
    persist_hypotheses_and_registry,
)
from qros.research.tester import (
    HypothesisTester,
    TradeEvent,
)
from qros.research.pattern_miner import (
    ConditionalPatternMiner,
    ConditionalPattern,
)

__all__ = [
    "evaluate_data_sufficiency",
    "ClassSufficiencyResult",
    "StylizedFactsScanner",
    "StylizedFactObservation",
    "generate_preregistered_hypotheses",
    "persist_hypotheses_and_registry",
    "HypothesisTester",
    "TradeEvent",
    "ConditionalPatternMiner",
    "ConditionalPattern",
]
