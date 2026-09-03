"""Contract interfaces for TASK-6G Grounded Answer Generation."""

from abc import ABC, abstractmethod

from llm.answer_config import AnswerGenerationConfig
from llm.answer_models import GeneratedAnswer
from llm.budget_models import PackedContext
from llm.planner_models import QueryPlan


class AnswerGeneratorContract(ABC):
    """Abstract interface contract for generating answers from packed context."""

    @abstractmethod
    def generate(
        self,
        query_plan: QueryPlan,
        packed_context: PackedContext,
        config: AnswerGenerationConfig,
    ) -> GeneratedAnswer:
        """Deterministically format prompt and generate answer using provider abstraction.

        Args:
            query_plan: Orchestration details covering intent, scope, and entities.
            packed_context: The bounded context package containing evidence.
            config: Generation configuration parameters.

        Returns:
            GeneratedAnswer representation containing result text and metadata.

        Raises:
            AnswerGenerationError: If orchestration, validation, or invocation fails.
        """
        pass
