"""
Privacy Guard module - GDPR-compliant PII detection and sanitization.

Implements data minimization (truncation) and pseudonymization (PII masking).
Supports optional Microsoft Presidio integration for enhanced NER-based detection.
"""

import re
from typing import Optional

from ..utils.logger import logger

# Try to import Presidio for enhanced PII detection
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.info("Presidio not installed. Using regex-based PII detection.")

# Ce code applique le Plan V5 du projet de tri d'emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class PrivacyGuard:
    """
    Responsable de la sanitization des données avant envoi au LLM.
    Implémente les règles de minimisation RGPD.
    
    Uses Microsoft Presidio when available for enhanced NER-based detection,
    falls back to regex patterns otherwise.
    """

    # PII entity types to detect with Presidio
    PRESIDIO_ENTITIES = [
        "EMAIL_ADDRESS",
        "PHONE_NUMBER", 
        "IP_ADDRESS",
        "CREDIT_CARD",
        "IBAN_CODE",
        "PERSON",
        "LOCATION",
        "DATE_TIME",
        "NRP",  # Nationality, Religion, Political group
        "MEDICAL_LICENSE",
        "URL",
    ]

    def __init__(self, use_presidio: Optional[bool] = None):
        """
        Initialize the PrivacyGuard.
        
        Args:
            use_presidio: Force Presidio on/off. If None, auto-detect availability.
        """
        # Determine if we should use Presidio
        if use_presidio is None:
            self.use_presidio = PRESIDIO_AVAILABLE
        else:
            self.use_presidio = use_presidio and PRESIDIO_AVAILABLE
        
        # Initialize Presidio engines if available
        if self.use_presidio:
            self._init_presidio()
        else:
            self._init_regex()
        
        # Limite de caractères pour le body (Minimisation)
        self.MAX_BODY_LENGTH = 2000
        
        logger.info(f"PrivacyGuard initialized with {'Presidio' if self.use_presidio else 'regex'} mode")
    
    def _init_presidio(self):
        """Initialize Presidio analyzer and anonymizer engines."""
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            
            # Define operators for anonymization
            self.operators = {
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL_REDACTED>"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE_REDACTED>"}),
                "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP_REDACTED>"}),
                "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CARD_REDACTED>"}),
                "IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN_REDACTED>"}),
                "PERSON": OperatorConfig("replace", {"new_value": "<NAME_REDACTED>"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION_REDACTED>"}),
                "DATE_TIME": OperatorConfig("keep"),  # Keep dates, they're usually relevant for classification
                "NRP": OperatorConfig("replace", {"new_value": "<PII_REDACTED>"}),
                "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "<LICENSE_REDACTED>"}),
                "URL": OperatorConfig("keep"),  # Keep URLs, they're useful for context
                "DEFAULT": OperatorConfig("replace", {"new_value": "<PII_REDACTED>"}),
            }
            logger.debug("Presidio engines initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}. Falling back to regex.")
            self.use_presidio = False
            self._init_regex()
    
    def _init_regex(self):
        """Initialize regex patterns for basic PII detection."""
        # Regex patterns for fallback detection
        self.patterns = {
            "email": (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "<EMAIL_REDACTED>"),
            "phone": (r"\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b", "<PHONE_REDACTED>"),
            "ip": (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP_REDACTED>"),
            "credit_card": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "<CARD_REDACTED>"),
            "iban": (r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b", "<IBAN_REDACTED>"),
            "ssn_fr": (r"\b[12][0-9]{2}(0[1-9]|1[0-2])[0-9]{2}[0-9]{3}[0-9]{3}[0-9]{2}\b", "<SSN_REDACTED>"),
        }
        
        # Compile patterns
        self.compiled_patterns = {
            name: (re.compile(pattern, re.IGNORECASE), replacement)
            for name, (pattern, replacement) in self.patterns.items()
        }

    def sanitize(self, text: str) -> str:
        """
        Nettoie le texte des PII (Personal Identifiable Information).
        
        Args:
            text: Raw text to sanitize
            
        Returns:
            Sanitized text with PII redacted
        """
        if not text:
            return ""

        # 1. Troncature (Minimisation)
        # RGPD: On ne traite que ce qui est nécessaire.
        truncated = False
        if len(text) > self.MAX_BODY_LENGTH:
            text = text[: self.MAX_BODY_LENGTH]
            truncated = True

        # 2. PII Detection & Anonymization
        if self.use_presidio:
            text = self._sanitize_with_presidio(text)
        else:
            text = self._sanitize_with_regex(text)
        
        # 3. Add truncation marker if needed
        if truncated:
            text += "... [TRUNCATED]"

        return text
    
    def _sanitize_with_presidio(self, text: str) -> str:
        """Use Presidio NER-based detection for PII sanitization."""
        try:
            # Analyze text for PII entities
            results = self.analyzer.analyze(
                text=text,
                entities=self.PRESIDIO_ENTITIES,
                language="en"  # Primary language; Presidio supports multi-lang
            )
            
            if not results:
                return text
            
            # Anonymize detected entities
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=self.operators
            )
            
            logger.debug(f"Presidio redacted {len(results)} PII entities")
            return anonymized.text
            
        except Exception as e:
            logger.warning(f"Presidio anonymization failed: {e}. Using regex fallback.")
            return self._sanitize_with_regex(text)
    
    def _sanitize_with_regex(self, text: str) -> str:
        """Use regex patterns for basic PII sanitization."""
        for name, (pattern, replacement) in self.compiled_patterns.items():
            text = pattern.sub(replacement, text)
        return text

    def sanitize_payload(self, payload: dict) -> dict:
        """
        Nettoie un payload complet (sujet, body).
        
        Args:
            payload: Email payload dictionary
            
        Returns:
            Sanitized payload with PII redacted
        """
        clean_payload = payload.copy()

        if "subject" in clean_payload:
            clean_payload["subject"] = self.sanitize(clean_payload["subject"])

        if "body" in clean_payload:
            clean_payload["body"] = self.sanitize(clean_payload["body"])

        # ATTENTION: On ne touche pas aux IDs ou métadonnées techniques nécessaires au routing

        return clean_payload
    
    def get_pii_stats(self, text: str) -> dict:
        """
        Analyze text and return PII detection statistics without modifying text.
        Useful for auditing and compliance reporting.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with PII detection statistics
        """
        if not text:
            return {"entities_found": 0, "entity_types": []}
        
        if self.use_presidio:
            try:
                results = self.analyzer.analyze(
                    text=text,
                    entities=self.PRESIDIO_ENTITIES,
                    language="en"
                )
                return {
                    "entities_found": len(results),
                    "entity_types": list(set(r.entity_type for r in results)),
                    "engine": "presidio"
                }
            except Exception as e:
                logger.warning(f"Presidio analysis failed: {e}")
        
        # Fallback to regex count
        count = 0
        types = []
        for name, (pattern, _) in self.compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                types.append(name)
        
        return {
            "entities_found": count,
            "entity_types": types,
            "engine": "regex"
        }
