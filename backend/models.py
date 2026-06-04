from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResponse:
    answer: str
    confidence: float
    source: str
    missing_data: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence": max(0.0, min(1.0, float(self.confidence))),
            "source": self.source if self.source in {"resume", "inference"} else "inference",
            "missing_data": self.missing_data,
        }

