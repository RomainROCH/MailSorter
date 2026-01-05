import re

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class PrivacyGuard:
    """
    Responsable de la sanitization des données avant envoi au LLM.
    Implémente les règles de minimisation RGPD.
    """

    def __init__(self):
        # Regex simples pour la détection.
        # TODO: Améliorer avec une librairie spécialisée comme Microsoft Presidio pour plus de robustesse.
        self.email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        self.phone_regex = (
            r"\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b"
        )
        self.ip_regex = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"

        # Limite de caractères pour le body (Minimisation)
        self.MAX_BODY_LENGTH = 2000

    def sanitize(self, text: str) -> str:
        """
        Nettoie le texte des PII (Personal Identifiable Information).
        """
        if not text:
            return ""

        # 1. Troncature (Minimisation)
        # RGPD: On ne traite que ce qui est nécessaire.
        if len(text) > self.MAX_BODY_LENGTH:
            text = text[: self.MAX_BODY_LENGTH] + "... [TRUNCATED]"

        # 2. Masquage (Pseudonymisation)
        text = re.sub(self.email_regex, "<EMAIL_REDACTED>", text)
        text = re.sub(self.phone_regex, "<PHONE_REDACTED>", text)
        text = re.sub(self.ip_regex, "<IP_REDACTED>", text)

        return text

    def sanitize_payload(self, payload: dict) -> dict:
        """
        Nettoie un payload complet (sujet, body).
        """
        clean_payload = payload.copy()

        if "subject" in clean_payload:
            clean_payload["subject"] = self.sanitize(clean_payload["subject"])

        if "body" in clean_payload:
            clean_payload["body"] = self.sanitize(clean_payload["body"])

        # ATTENTION: On ne touche pas aux IDs ou métadonnées techniques nécessaires au routing

        return clean_payload
import re

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class PrivacyGuard:
    """
    Responsable de la sanitization des données avant envoi au LLM.
    Implémente les règles de minimisation RGPD.
    """

    def __init__(self):
        # Regex simples pour la détection.
        # TODO: Améliorer avec une librairie spécialisée comme Microsoft Presidio pour plus de robustesse.
        self.email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        self.phone_regex = (
            r"\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b"
        )
        self.ip_regex = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"

        # Limite de caractères pour le body (Minimisation)
        self.MAX_BODY_LENGTH = 2000

    def sanitize(self, text: str) -> str:
        """
        Nettoie le texte des PII (Personal Identifiable Information).
        """
        if not text:
            return ""

        # 1. Troncature (Minimisation)
        # RGPD: On ne traite que ce qui est nécessaire.
        if len(text) > self.MAX_BODY_LENGTH:
            text = text[: self.MAX_BODY_LENGTH] + "... [TRUNCATED]"

        # 2. Masquage (Pseudonymisation)
        text = re.sub(self.email_regex, "<EMAIL_REDACTED>", text)
        text = re.sub(self.phone_regex, "<PHONE_REDACTED>", text)
        text = re.sub(self.ip_regex, "<IP_REDACTED>", text)

        return text

    def sanitize_payload(self, payload: dict) -> dict:
        """
        Nettoie un payload complet (sujet, body).
        """
        clean_payload = payload.copy()

        if "subject" in clean_payload:
            clean_payload["subject"] = self.sanitize(clean_payload["subject"])

        if "body" in clean_payload:
            clean_payload["body"] = self.sanitize(clean_payload["body"])

        # ATTENTION: On ne touche pas aux IDs ou métadonnées techniques nécessaires au routing

        return clean_payload
