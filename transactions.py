"""
CivGraph -- Atomic transaction ledger.

Records every individual agent-to-agent and actant-to-agent interaction
during tick execution. Each transaction captures the source, target,
type, magnitude, and human-readable context.

Transaction types:
  capital_flow        Agent → Agent capital transfer (intergenerational, conversion)
  opinion_shift       Agent → Agent opinion influence via network edge
  norm_enforcement    Norm → Agent compliance pressure
  norm_sanction       Community → Agent social capital penalty for deviance
  media_effect        Media actant → Agent opinion modulation
  echo_chamber        Social media actant → Agent bubble deepening
  task_displacement   Technology actant → Agent task automation
  health_change       Environment → Agent health evolution
  chronic_onset       Age/class → Agent chronic condition onset
  institutional_cap   Institution → Agent capital accumulation
  tie_formed          Agent ⇄ Agent new network edge
  tie_dissolved       Agent ⇄ Agent edge removal
  translation         Agent → Event reframing (Callon)
  env_agent_effect    Environment indicator → Agent capital effect
  agent_env_effect    Agent aggregate → Environment indicator feedback
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TxType(str, Enum):
    CAPITAL_FLOW = "capital_flow"
    OPINION_SHIFT = "opinion_shift"
    NORM_ENFORCEMENT = "norm_enforcement"
    NORM_SANCTION = "norm_sanction"
    MEDIA_EFFECT = "media_effect"
    ECHO_CHAMBER = "echo_chamber"
    TASK_DISPLACEMENT = "task_displacement"
    HEALTH_CHANGE = "health_change"
    CHRONIC_ONSET = "chronic_onset"
    INSTITUTIONAL_CAP = "institutional_cap"
    TIE_FORMED = "tie_formed"
    TIE_DISSOLVED = "tie_dissolved"
    TRANSLATION = "translation"
    ENV_AGENT = "env_agent_effect"
    AGENT_ENV = "agent_env_effect"


# Color palette for each type (matches engraving aesthetic)
TX_COLORS = {
    TxType.CAPITAL_FLOW:      "#3a7d6e",  # verdigris
    TxType.OPINION_SHIFT:     "#2e4057",  # indigo
    TxType.NORM_ENFORCEMENT:  "#6b5b3a",  # sepia
    TxType.NORM_SANCTION:     "#8b3a3a",  # oxide
    TxType.MEDIA_EFFECT:      "#5a4080",  # purple
    TxType.ECHO_CHAMBER:      "#804080",  # magenta
    TxType.TASK_DISPLACEMENT: "#b08f4a",  # ochre
    TxType.HEALTH_CHANGE:     "#3a7d6e",  # verdigris
    TxType.CHRONIC_ONSET:     "#8b3a3a",  # oxide
    TxType.INSTITUTIONAL_CAP: "#b08f4a",  # ochre
    TxType.TIE_FORMED:        "#2e6090",  # blue
    TxType.TIE_DISSOLVED:     "#8b3a3a",  # oxide
    TxType.TRANSLATION:       "#5a6575",  # slate
    TxType.ENV_AGENT:         "#5a6575",  # slate
    TxType.AGENT_ENV:         "#5a6575",  # slate
}

TX_LABELS = {
    TxType.CAPITAL_FLOW:      "capital flow",
    TxType.OPINION_SHIFT:     "opinion shift",
    TxType.NORM_ENFORCEMENT:  "norm pressure",
    TxType.NORM_SANCTION:     "norm sanction",
    TxType.MEDIA_EFFECT:      "media effect",
    TxType.ECHO_CHAMBER:      "echo chamber",
    TxType.TASK_DISPLACEMENT: "task displacement",
    TxType.HEALTH_CHANGE:     "health change",
    TxType.CHRONIC_ONSET:     "chronic onset",
    TxType.INSTITUTIONAL_CAP: "board capital",
    TxType.TIE_FORMED:        "tie formed",
    TxType.TIE_DISSOLVED:     "tie dissolved",
    TxType.TRANSLATION:       "translation",
    TxType.ENV_AGENT:         "env → agent",
    TxType.AGENT_ENV:         "agent → env",
}


@dataclass
class Transaction:
    """A single atomic interaction."""
    tx_type: TxType
    source: str          # agent name, actant name, or indicator name
    source_id: str       # agent id or "" for non-human
    target: str          # agent name or indicator name
    target_id: str       # agent id or ""
    magnitude: float     # signed magnitude of the interaction
    context: str         # human-readable description
    sub_tick: int = 0    # ordering within tick

    def to_dict(self) -> dict:
        return {
            "type": self.tx_type.value,
            "source": self.source,
            "source_id": self.source_id,
            "target": self.target,
            "target_id": self.target_id,
            "magnitude": round(self.magnitude, 4),
            "context": self.context,
            "sub_tick": self.sub_tick,
            "color": TX_COLORS.get(self.tx_type, "#5a6575"),
            "label": TX_LABELS.get(self.tx_type, self.tx_type.value),
        }


class TransactionLedger:
    """Accumulates transactions during a tick, then makes them available."""

    def __init__(self, max_per_tick: int = 5000):
        self.transactions: list[Transaction] = []
        self.max_per_tick = max_per_tick
        self._sub_tick = 0
        self._counts: dict[str, int] = {}
        self._sampling_rates: dict[str, float] = {}
        self._rng_counter = 0

    def clear(self):
        self.transactions = []
        self._sub_tick = 0
        self._counts = {}
        self._sampling_rates = {}

    def _should_record(self, tx_type: TxType) -> bool:
        """Adaptive sampling: record all if under budget, sample if over."""
        type_key = tx_type.value
        self._counts[type_key] = self._counts.get(type_key, 0) + 1

        if len(self.transactions) < self.max_per_tick:
            return True

        # Over budget: sample proportionally (keep rarer types, sample common ones)
        rate = self._sampling_rates.get(type_key)
        if rate is None:
            # First time over budget for this type: compute rate
            count = self._counts[type_key]
            rate = max(0.01, min(1.0, self.max_per_tick / (count * 10)))
            self._sampling_rates[type_key] = rate

        # Deterministic sampling via counter
        self._rng_counter += 1
        return (self._rng_counter * 2654435761) % 1000 < int(rate * 1000)

    def record(self, tx_type: TxType, source: str, source_id: str,
               target: str, target_id: str, magnitude: float, context: str):
        if not self._should_record(tx_type):
            return
        self.transactions.append(Transaction(
            tx_type=tx_type,
            source=source, source_id=source_id,
            target=target, target_id=target_id,
            magnitude=magnitude, context=context,
            sub_tick=self._sub_tick,
        ))
        self._sub_tick += 1

    def summary(self) -> dict:
        """Aggregate counts by type."""
        counts: dict[str, int] = {}
        for tx in self.transactions:
            counts[tx.tx_type.value] = counts.get(tx.tx_type.value, 0) + 1
        # Also report true counts (before sampling)
        return {
            "total_recorded": len(self.transactions),
            "total_actual": sum(self._counts.values()),
            "by_type": counts,
            "actual_by_type": dict(self._counts),
        }

    def to_list(self, limit: int = 2000, offset: int = 0,
                filter_type: str | None = None) -> list[dict]:
        txs = self.transactions
        if filter_type:
            txs = [t for t in txs if t.tx_type.value == filter_type]
        return [t.to_dict() for t in txs[offset:offset + limit]]


# Global ledger instance
LEDGER = TransactionLedger()
