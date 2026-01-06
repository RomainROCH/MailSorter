"""
Orchestrator module - Core email classification pipeline.

This module coordinates the flow: Input -> Sanitize -> Privacy -> Rate Limit -> LLM -> Sign -> Response.
Implements Plan V5 with full GDPR compliance and security hardening.
"""

from .privacy import PrivacyGuard
from .rate_limiter import check_rate_limit, get_rate_limiter
from ..providers.ollama_provider import OllamaProvider
from ..utils.logger import logger
from ..utils.config import load_config
from ..utils.sanitize import sanitize_email_payload
from ..utils.security import create_signed_result

# Ce code applique le Plan V5 du projet de tri d'emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class Orchestrator:
    """
    Coordonne le flux de traitement : Réception -> Privacy -> LLM -> Réponse.
    Supports headers-only mode for maximum privacy.
    """

    def __init__(self):
        self.privacy_guard = PrivacyGuard()
        self.config = load_config()
        
        # Analysis mode: 'full' or 'headers_only'
        self.analysis_mode = self.config.get("analysis_mode", "full")
        
        # Thresholds per folder
        self.thresholds = self.config.get("thresholds", {})
        self.default_threshold = 0.5
        
        # Initialize provider based on config
        provider_name = self.config.get("provider", "ollama")
        self.provider = self._init_provider(provider_name)
        self.provider_name = provider_name

        # Cache simple pour éviter de spammer le health check
        self.is_provider_healthy = True
    
    def _init_provider(self, provider_name: str):
        """Initialize the appropriate LLM provider."""
        provider_config = self.config.get("providers", {}).get(provider_name, {})
        
        if provider_name == "ollama":
            return OllamaProvider(
                base_url=provider_config.get("base_url", "http://localhost:11434"),
                model=provider_config.get("model", "llama3")
            )
        # TODO: Add other providers (OpenAI, Anthropic, Gemini)
        else:
            logger.warning(f"Unknown provider '{provider_name}', falling back to Ollama")
            return OllamaProvider()

    def handle_message(self, message: dict) -> dict:
        """
        Traite un message JSON venant de l'extension.
        """
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == "ping":
            return {"type": "pong", "status": "ok"}

        if msg_type == "classify":
            return self._handle_classify(payload)
        
        if msg_type == "health":
            return self._handle_health()

        return {"status": "error", "error": "Unknown message type"}
    
    def _handle_health(self) -> dict:
        """Return health status of the system."""
        provider_healthy = self.provider.health_check()
        rate_status = get_rate_limiter().get_status(self.provider_name)
        
        return {
            "status": "ok" if provider_healthy else "degraded",
            "provider": self.provider_name,
            "provider_healthy": provider_healthy,
            "analysis_mode": self.analysis_mode,
            "rate_limit": rate_status
        }

    def _handle_classify(self, payload: dict) -> dict:
        """
        Logique de classification with full security pipeline.
        """
        # 0. Input sanitization (SEC-003)
        payload = sanitize_email_payload(payload)
        
        email_id = payload.get("id")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        sender = payload.get("from", "")
        folders = payload.get("folders", [])

        logger.info(f"Processing email ID: {email_id}")

        # 1. Rate limiting check (SEC-002)
        if not check_rate_limit(self.provider_name, block=True):
            logger.warning(f"Rate limited for email {email_id}")
            return {
                "id": email_id, 
                "action": "none", 
                "reason": "rate_limited"
            }

        # 2. Privacy Guard (GDPR) - only if not headers_only
        if self.analysis_mode == "headers_only":
            # V5-004: Headers-only mode - don't send body to LLM
            clean_subject = self.privacy_guard.sanitize(subject)
            clean_body = ""  # Never send body in headers-only mode
            logger.info(f"Headers-only mode: body excluded for email {email_id}")
        else:
            clean_subject = self.privacy_guard.sanitize(subject)
            clean_body = self.privacy_guard.sanitize(body)

        # 3. Feature Detection / Health Check
        if not self.provider.health_check():
            logger.error("Provider unavailable. Fallback to Inbox.")
            self.is_provider_healthy = False
            return {"id": email_id, "action": "none", "reason": "provider_down"}
        
        self.is_provider_healthy = True

        # 4. Inférence
        target_folder = self.provider.classify_email(clean_subject, clean_body, folders)

        if target_folder:
            # 5. Check confidence threshold (V5-005)
            # For now, we don't have confidence scores from Ollama, so skip threshold check
            # TODO: Implement confidence scoring when providers return scores
            
            logger.info(f"Decision for {email_id}: Move to '{target_folder}'")
            
            # 6. Sign the result (V5-007)
            signed_result = create_signed_result(
                message_id=str(email_id),
                category=target_folder,
                score=0.8  # Placeholder until we have real confidence scores
            )
            
            return {
                "id": email_id, 
                "action": "move", 
                "target": target_folder,
                "signature": signed_result.get("signature"),
                "signed": signed_result.get("signed", False)
            }
        else:
            logger.info(f"No decision for {email_id}. Keeping in Inbox.")
            return {"id": email_id, "action": "none", "reason": "uncertainty_or_error"}
