"""
Orchestrator module - Core email classification pipeline.

This module coordinates the flow:
Input -> Sanitize -> Privacy -> Cache -> CircuitBreaker -> RateLimit -> LLM -> Confidence -> Sign -> Response

Implements Plan V5 with Phase 4 Intelligence & Adaptation features:
- Provider factory pattern (INT-001)
- Dynamic thresholds (V5-005)
- Circuit breaker (AUDIT-003)
- Smart caching (cost optimization)
- Prompt templates (INT-002)
- Confidence calibration (INT-003)
- Batch processing (V5-015)
"""

from typing import Dict, Optional

from .privacy import PrivacyGuard
from .rate_limiter import check_rate_limit, get_rate_limiter
from .circuit_breaker import get_circuit_breaker, CircuitBreaker
from .smart_cache import get_smart_cache, SmartCache
from .confidence import get_calibrator, ConfidenceCalibrator
from .prompt_engine import get_prompt_engine, PromptEngine
from .batch_processor import get_batch_processor, ProcessingMode
from .feedback_loop import get_feedback_loop
from ..providers.factory import ProviderFactory
from ..providers.base import ClassificationResult, LLMProvider
from ..utils.logger import logger
from ..utils.config import load_config
from ..utils.sanitize import sanitize_email_payload
from ..utils.security import create_signed_result


class Orchestrator:
    """
    Core email classification coordinator.
    
    Implements the full processing pipeline with Phase 4 enhancements:
    1. Input sanitization (security)
    2. Smart cache check (cost optimization)
    3. Circuit breaker check (resilience)
    4. Rate limiting (cost control)
    5. Privacy guard (GDPR)
    6. Prompt rendering (i18n)
    7. LLM inference (classification)
    8. Confidence check (quality)
    9. Result signing (integrity)
    10. Calibration logging (improvement)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize orchestrator with all Phase 4 components.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or load_config()
        
        # Core components
        self.privacy_guard = PrivacyGuard()
        
        # Analysis mode: 'full' or 'headers_only'
        self.analysis_mode = self.config.get("analysis_mode", "full")
        
        # Phase 4 components
        self._init_phase4_components()
        
        # Provider initialization
        self.provider_name = self.config.get("provider", "ollama")
        self.provider = self._init_provider(self.provider_name)
        
        # Health tracking
        self.is_provider_healthy = True
    
    def _init_phase4_components(self) -> None:
        """Initialize Phase 4 Intelligence & Adaptation components."""
        # Get configuration sections
        intelligence_config = self.config.get("intelligence", {})
        
        # Circuit breaker (AUDIT-003)
        cb_config = intelligence_config.get("circuit_breaker", {})
        self.circuit_breaker = get_circuit_breaker(
            failure_threshold=cb_config.get("failure_threshold", 3),
            recovery_timeout=cb_config.get("recovery_timeout", 30)
        )
        
        # Smart cache (cost optimization)
        cache_config = intelligence_config.get("smart_cache", {})
        self.smart_cache = get_smart_cache(cache_config)
        
        # Confidence calibrator (V5-005, INT-003)
        calibration_config = intelligence_config.get("calibration", {})
        calibration_config["thresholds"] = self.config.get("thresholds", {})
        self.calibrator = get_calibrator(calibration_config)
        
        # Prompt engine (INT-002, INT-004)
        prompt_config = intelligence_config.get("prompts", {})
        self.prompt_engine = get_prompt_engine(
            default_language=prompt_config.get("language", "en")
        )
        
        # Batch processor (V5-015)
        batch_config = self.config.get("batch_mode", {})
        self.batch_processor = get_batch_processor(batch_config)
        
        # Feedback loop (V5-008)
        feedback_config = self.config.get("feedback_loop", {})
        self.feedback_loop = get_feedback_loop(feedback_config)
    
    def _init_provider(self, provider_name: str) -> LLMProvider:
        """
        Initialize LLM provider using factory pattern (INT-001).
        
        Args:
            provider_name: Provider identifier (ollama, openai, anthropic, gemini)
        
        Returns:
            Initialized LLMProvider instance
        """
        provider_config = self.config.get("providers", {}).get(provider_name, {})
        
        try:
            return ProviderFactory.create(provider_name, provider_config)
        except ValueError as e:
            logger.warning(f"Provider error: {e}. Falling back to Ollama.")
            return ProviderFactory.create("ollama")
    
    def handle_message(self, message: dict) -> dict:
        """
        Process incoming message from extension.
        
        Message types:
        - ping: Health check
        - classify: Email classification
        - health: Detailed health status
        - batch_start: Start batch processing
        - batch_status: Get batch job status
        
        Args:
            message: JSON message from extension
        
        Returns:
            Response dict
        """
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == "ping":
            return {"type": "pong", "status": "ok"}

        if msg_type == "classify":
            return self._handle_classify(payload)
        
        if msg_type == "health":
            return self._handle_health()
        
        if msg_type == "batch_start":
            return self._handle_batch_start(payload)
        
        if msg_type == "batch_status":
            return self._handle_batch_status(payload)
        
        if msg_type == "feedback":
            return self._handle_feedback(payload)
        
        if msg_type == "stats":
            return self._handle_stats()

        return {"status": "error", "error": "Unknown message type"}
    
    def _handle_health(self) -> dict:
        """Return detailed health status of all components."""
        provider_healthy = self.provider.health_check()
        rate_status = get_rate_limiter().get_status(self.provider_name)
        circuit_status = self.circuit_breaker.get_stats(self.provider_name)
        cache_stats = self.smart_cache.get_stats()
        
        return {
            "status": "ok" if provider_healthy else "degraded",
            "provider": {
                "name": self.provider_name,
                "healthy": provider_healthy,
                "is_local": self.provider.is_local
            },
            "analysis_mode": self.analysis_mode,
            "rate_limit": rate_status,
            "circuit_breaker": circuit_status,
            "cache": cache_stats,
            "calibration": self.calibrator.get_all_stats()
        }
    
    def _handle_stats(self) -> dict:
        """Return comprehensive statistics."""
        return {
            "cache": self.smart_cache.get_stats(),
            "calibration": self.calibrator.get_all_stats(),
            "feedback": self.feedback_loop.get_stats(),
            "circuit_breaker": self.circuit_breaker.get_stats(self.provider_name)
        }

    def _handle_classify(self, payload: dict) -> dict:
        """
        Full classification pipeline with Phase 4 enhancements.
        """
        # 0. Input sanitization (SEC-003)
        payload = sanitize_email_payload(payload)
        
        email_id = payload.get("id")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        sender = payload.get("from", "")
        folders = payload.get("folders", [])

        logger.info(f"Processing email ID: {email_id}")

        # 1. Smart cache check (cost optimization)
        cache_result = self.smart_cache.check(subject, body, sender, folders)
        if cache_result:
            logger.info(f"Cache hit ({cache_result.source}): {cache_result.folder}")
            return self._build_response(
                email_id, 
                cache_result, 
                from_cache=True
            )

        # 2. Circuit breaker check (AUDIT-003)
        if not self.circuit_breaker.can_execute(self.provider_name):
            logger.warning(f"Circuit open for {self.provider_name}, using fallback")
            fallback_folder = self.circuit_breaker.get_fallback_folder()
            return {
                "id": email_id,
                "action": "none",
                "reason": "circuit_open",
                "fallback": fallback_folder
            }

        # 3. Rate limiting check (SEC-002)
        if not check_rate_limit(self.provider_name, block=True):
            logger.warning(f"Rate limited for email {email_id}")
            return {
                "id": email_id, 
                "action": "none", 
                "reason": "rate_limited"
            }

        # 4. Privacy Guard (GDPR)
        if self.analysis_mode == "headers_only":
            clean_subject = self.privacy_guard.sanitize(subject)
            clean_body = ""
            logger.debug(f"Headers-only mode: body excluded")
        else:
            clean_subject = self.privacy_guard.sanitize(subject)
            clean_body = self.privacy_guard.sanitize(body)

        # 5. Provider health check
        if not self.provider.health_check():
            logger.error("Provider unavailable. Fallback to Inbox.")
            self.is_provider_healthy = False
            self.circuit_breaker.record_failure(self.provider_name)
            return {"id": email_id, "action": "none", "reason": "provider_down"}
        
        self.is_provider_healthy = True

        # 6. Render prompt (INT-002, INT-004)
        prompt = self.prompt_engine.render(
            template_name="classify",
            subject=clean_subject,
            body=clean_body,
            folders=folders,
            sender=sender
        )

        # 7. LLM inference
        try:
            result = self.provider.classify_email(
                clean_subject, 
                clean_body, 
                folders,
                prompt_template=prompt
            )
            
            if result:
                self.circuit_breaker.record_success(self.provider_name)
            else:
                self.circuit_breaker.record_failure(self.provider_name)
                
        except Exception as e:
            logger.error(f"LLM inference error: {e}")
            self.circuit_breaker.record_failure(self.provider_name)
            return {"id": email_id, "action": "none", "reason": "inference_error"}

        if not result:
            logger.info(f"No decision for {email_id}. Keeping in Inbox.")
            return {"id": email_id, "action": "none", "reason": "no_result"}

        # 8. Confidence threshold check (V5-005)
        if not self.calibrator.passes_threshold(result.folder, result.confidence):
            logger.info(
                f"Confidence {result.confidence:.2f} below threshold for '{result.folder}'"
            )
            # Log for calibration anyway
            self.calibrator.log_prediction(result.folder, result.confidence)
            return {
                "id": email_id,
                "action": "none",
                "reason": "low_confidence",
                "suggested_folder": result.folder,
                "confidence": result.confidence
            }

        # 9. Store in cache for future hits
        self.smart_cache.store(
            subject, body, sender, 
            result.folder, result.confidence
        )

        # 10. Log for calibration (INT-003)
        self.calibrator.log_prediction(result.folder, result.confidence)

        logger.info(
            f"Decision for {email_id}: Move to '{result.folder}' "
            f"(confidence: {result.confidence:.2f})"
        )

        return self._build_response(email_id, result)
    
    def _build_response(
        self, 
        email_id: str, 
        result: ClassificationResult,
        from_cache: bool = False
    ) -> dict:
        """Build the classification response with signing."""
        # Sign the result (V5-007)
        signed_result = create_signed_result(
            message_id=str(email_id),
            category=result.folder,
            score=result.confidence
        )
        
        return {
            "id": email_id,
            "action": "move",
            "target": result.folder,
            "confidence": result.confidence,
            "source": result.source if from_cache else "llm",
            "signature": signed_result.get("signature"),
            "signed": signed_result.get("signed", False),
            "tokens_used": result.tokens_used,
            "latency_ms": result.latency_ms
        }
    
    def _handle_batch_start(self, payload: dict) -> dict:
        """Start a batch processing job."""
        email_ids = payload.get("email_ids", [])
        
        if not email_ids:
            return {"status": "error", "error": "No email IDs provided"}
        
        job_id = self.batch_processor.create_job(email_ids)
        
        # Start processing in background
        # Note: In production, this should use asyncio or threading
        def classify_single(eid):
            return self._handle_classify({"id": eid, **payload.get("template", {})})
        
        self.batch_processor.start_job(job_id, classify_single)
        
        return {
            "status": "started",
            "job_id": job_id,
            "total": len(email_ids)
        }
    
    def _handle_batch_status(self, payload: dict) -> dict:
        """Get batch job status."""
        job_id = payload.get("job_id")
        
        if not job_id:
            return {"status": "error", "error": "No job ID provided"}
        
        status = self.batch_processor.get_status(job_id)
        
        if not status:
            return {"status": "error", "error": "Job not found"}
        
        return status
    
    def _handle_feedback(self, payload: dict) -> dict:
        """Record user feedback for calibration."""
        if not self.feedback_loop.is_enabled():
            return {"status": "disabled"}
        
        success = self.feedback_loop.record_feedback(
            email_id=payload.get("email_id", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            predicted_folder=payload.get("predicted_folder", ""),
            actual_folder=payload.get("actual_folder", ""),
            confidence=payload.get("confidence", 0.5)
        )
        
        # Also invalidate sender cache if correction
        if payload.get("predicted_folder") != payload.get("actual_folder"):
            sender = payload.get("from", "")
            self.smart_cache.invalidate_sender(sender)
            
            # Record correction in calibrator
            self.calibrator.record_correction(
                payload.get("predicted_folder", ""),
                payload.get("actual_folder", ""),
                payload.get("confidence", 0.5)
            )
        
        return {"status": "recorded" if success else "failed"}
    
    def switch_provider(self, provider_name: str) -> bool:
        """
        Switch to a different provider at runtime.
        
        Args:
            provider_name: New provider name
        
        Returns:
            True if switch successful
        """
        try:
            provider_config = self.config.get("providers", {}).get(provider_name, {})
            new_provider = ProviderFactory.create(provider_name, provider_config)
            
            self.provider = new_provider
            self.provider_name = provider_name
            
            logger.info(f"Switched to provider: {provider_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch provider: {e}")
            return False
    
    def get_available_providers(self) -> dict:
        """List available providers and their status."""
        providers = {}
        
        for name in ProviderFactory.list_providers():
            try:
                provider = ProviderFactory.create(name)
                providers[name] = {
                    "available": True,
                    "is_local": provider.is_local,
                    "supports_streaming": provider.supports_streaming,
                    "healthy": provider.health_check() if name == self.provider_name else None
                }
            except Exception as e:
                providers[name] = {
                    "available": False,
                    "error": str(e)
                }
        
        return providers
