"""
Core modules for MailSorter backend.

This package contains the core classification pipeline:
- orchestrator: Main email processing coordinator
- privacy: PII detection and redaction
- rate_limiter: API rate limiting
- circuit_breaker: Provider resilience
- prompt_engine: Template-based prompts with i18n
- confidence: Threshold management and calibration
- smart_cache: Cost optimization caching
- batch_processor: Batch vs real-time mode
- feedback_loop: User correction collection
- attachment_heuristic: Attachment analysis
"""

from .circuit_breaker import CircuitBreaker, get_circuit_breaker
from .confidence import ConfidenceCalibrator, get_calibrator
from .smart_cache import SmartCache, get_smart_cache
from .prompt_engine import PromptEngine, get_prompt_engine
from .batch_processor import BatchProcessor, ProcessingMode, get_batch_processor
from .feedback_loop import FeedbackLoop, get_feedback_loop

__all__ = [
    "orchestrator",
    "privacy",
    "rate_limiter",
    "attachment_heuristic",
    "CircuitBreaker",
    "get_circuit_breaker",
    "ConfidenceCalibrator",
    "get_calibrator",
    "SmartCache",
    "get_smart_cache",
    "PromptEngine",
    "get_prompt_engine",
    "BatchProcessor",
    "ProcessingMode",
    "get_batch_processor",
    "FeedbackLoop",
    "get_feedback_loop",
]
