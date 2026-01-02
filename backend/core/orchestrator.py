from .privacy import PrivacyGuard
from ..providers.ollama_provider import OllamaProvider
from ..utils.logger import logger

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.

class Orchestrator:
    """
    Coordonne le flux de traitement : Réception -> Privacy -> LLM -> Réponse.
    """

    def __init__(self):
        self.privacy_guard = PrivacyGuard()
        
        # TODO: Charger la config depuis un fichier JSON (backend/config.json)
        # Pour l'instant, on hardcode Ollama par défaut comme demandé (Local First)
        self.provider = OllamaProvider() 
        
        # Cache simple pour éviter de spammer le health check
        self.is_provider_healthy = True 

    def handle_message(self, message: dict) -> dict:
        """
        Traite un message JSON venant de l'extension.
        """
        msg_type = message.get('type')
        payload = message.get('payload', {})

        if msg_type == 'ping':
            return {"type": "pong", "status": "ok"}

        if msg_type == 'classify':
            return self._handle_classify(payload)

        return {"status": "error", "error": "Unknown message type"}

    def _handle_classify(self, payload: dict) -> dict:
        """
        Logique de classification.
        """
        email_id = payload.get('id')
        subject = payload.get('subject', '')
        body = payload.get('body', '')
        folders = payload.get('folders', [])

        logger.info(f"Processing email ID: {email_id}")

        # 1. Privacy Guard (GDPR)
        # On nettoie AVANT d'envoyer au provider
        clean_subject = self.privacy_guard.sanitize(subject)
        clean_body = self.privacy_guard.sanitize(body)

        # 2. Feature Detection / Health Check
        # Si le provider est down, on fallback immédiatement
        # TODO: Implémenter un circuit breaker plus sophistiqué
        if not self.provider.health_check():
            logger.error("Provider unavailable. Fallback to Inbox.")
            return {"id": email_id, "action": "none", "reason": "provider_down"}

        # 3. Inférence
        target_folder = self.provider.classify_email(clean_subject, clean_body, folders)

        if target_folder:
            logger.info(f"Decision for {email_id}: Move to '{target_folder}'")
            return {
                "id": email_id,
                "action": "move",
                "target": target_folder
            }
        else:
            logger.info(f"No decision for {email_id}. Keeping in Inbox.")
            return {
                "id": email_id,
                "action": "none",
                "reason": "uncertainty_or_error"
            }
