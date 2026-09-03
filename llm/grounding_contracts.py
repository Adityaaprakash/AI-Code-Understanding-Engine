"""Contract interfaces for Grounding Verification Engine (Phase 6H)."""

from abc import ABC, abstractmethod

from llm.answer_models import GeneratedAnswer
from llm.budget_models import PackedContext
from llm.grounding_config import GroundingVerificationConfig
from llm.grounding_models import GroundingVerificationResult


class GroundingEngineContract(ABC):
    """Abstraction interface defining deterministic parsing and verification boundaries."""

    @abstractmethod
    def verify(
        self,
        answer: GeneratedAnswer,
        context: PackedContext,
        config: GroundingVerificationConfig | None = None,
    ) -> GroundingVerificationResult:
        """
        Produce a deterministic verification representation mapped securely bounding
        factual claims parsed from 'answer' correlating against 'context'.
        """
        pass
