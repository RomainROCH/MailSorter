"""
Prompt engine with template system and language detection.

Implements:
- INT-002: Externalized, testable prompt templates
- INT-004: Multi-language prompt support with auto-detection
"""

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import langdetect, fallback to simple detection if unavailable
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.debug("langdetect not available, using fallback language detection")

# Try to import Jinja2, fallback to string formatting if unavailable
try:
    from jinja2 import Environment, BaseLoader, TemplateNotFound
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.debug("Jinja2 not available, using simple string formatting")


class PromptEngine:
    """
    Template-based prompt engine with language detection.
    
    Features:
    - Jinja2 templates for flexible prompt formatting
    - Automatic language detection for multi-language support
    - Sender-based language caching for consistency
    - Fallback to English for unsupported languages
    - Simple string formatting fallback if Jinja2 unavailable
    """
    
    # Supported languages with their prompt templates
    SUPPORTED_LANGUAGES = {"en", "fr", "de", "es", "it", "pt"}
    DEFAULT_LANGUAGE = "en"
    
    # Default templates (embedded, no file dependencies)
    DEFAULT_TEMPLATES = {
        "system_en": """You are an email classification assistant. Analyze emails and categorize them into folders.

You MUST respond with valid JSON only. Format:
{"folder": "exact_folder_name", "confidence": 0.85, "reasoning": "brief explanation"}

Rules:
1. "folder" MUST be exactly one of the provided folder names
2. "confidence" is a number between 0.0 (uncertain) and 1.0 (certain)
3. If no folder fits well, use "Inbox" with low confidence
4. Keep "reasoning" brief (under 50 words)""",

        "system_fr": """Vous êtes un assistant de classification d'emails. Analysez les emails et classez-les dans des dossiers.

Vous DEVEZ répondre uniquement avec du JSON valide. Format:
{"folder": "nom_exact_du_dossier", "confidence": 0.85, "reasoning": "brève explication"}

Règles:
1. "folder" DOIT être exactement l'un des noms de dossiers fournis
2. "confidence" est un nombre entre 0.0 (incertain) et 1.0 (certain)
3. Si aucun dossier ne convient, utilisez "Inbox" avec une confiance basse
4. Gardez "reasoning" bref (moins de 50 mots)""",

        "system_de": """Sie sind ein E-Mail-Klassifizierungsassistent. Analysieren Sie E-Mails und ordnen Sie sie Ordnern zu.

Sie MÜSSEN nur mit gültigem JSON antworten. Format:
{"folder": "exakter_ordnername", "confidence": 0.85, "reasoning": "kurze Erklärung"}

Regeln:
1. "folder" MUSS genau einer der angegebenen Ordnernamen sein
2. "confidence" ist eine Zahl zwischen 0.0 (unsicher) und 1.0 (sicher)
3. Wenn kein Ordner passt, verwenden Sie "Inbox" mit niedriger Konfidenz
4. Halten Sie "reasoning" kurz (unter 50 Wörtern)""",

        "classify_en": """Classify this email into one of the available folders.

Available folders: {{ folders_json }}

Email Subject: {{ subject }}
Email Body: {{ body }}

Respond with JSON only.""",

        "classify_fr": """Classez cet email dans l'un des dossiers disponibles.

Dossiers disponibles: {{ folders_json }}

Sujet de l'email: {{ subject }}
Corps de l'email: {{ body }}

Répondez uniquement en JSON.""",

        "classify_de": """Klassifizieren Sie diese E-Mail in einen der verfügbaren Ordner.

Verfügbare Ordner: {{ folders_json }}

E-Mail-Betreff: {{ subject }}
E-Mail-Text: {{ body }}

Antworten Sie nur mit JSON."""
    }
    
    def __init__(
        self, 
        templates_dir: Optional[str] = None,
        default_language: str = "en"
    ):
        """
        Initialize prompt engine.
        
        Args:
            templates_dir: Optional directory for custom templates
            default_language: Fallback language (default: en)
        """
        self.templates_dir = templates_dir
        self.default_language = default_language
        
        # Sender → language cache for consistency
        self._sender_language_cache: Dict[str, str] = {}
        
        # Initialize Jinja2 if available
        if JINJA2_AVAILABLE:
            self._env = Environment(
                loader=BaseLoader(),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self._env = None
        
        # Load custom templates if directory provided
        self._custom_templates: Dict[str, str] = {}
        if templates_dir and os.path.isdir(templates_dir):
            self._load_custom_templates(templates_dir)
    
    def _load_custom_templates(self, templates_dir: str) -> None:
        """Load custom templates from directory."""
        try:
            for filename in os.listdir(templates_dir):
                if filename.endswith(('.jinja2', '.txt', '.j2')):
                    name = os.path.splitext(filename)[0]
                    path = os.path.join(templates_dir, filename)
                    with open(path, 'r', encoding='utf-8') as f:
                        self._custom_templates[name] = f.read()
                    logger.debug(f"Loaded custom template: {name}")
        except Exception as e:
            logger.warning(f"Failed to load custom templates: {e}")
    
    def detect_language(
        self, 
        text: str, 
        sender: Optional[str] = None
    ) -> str:
        """
        Detect language of text with sender caching.
        
        Uses langdetect if available, otherwise falls back to
        simple keyword-based detection.
        
        Args:
            text: Text to analyze
            sender: Optional sender email for caching
        
        Returns:
            Language code (e.g., 'en', 'fr', 'de')
        """
        # Check sender cache first
        if sender and sender in self._sender_language_cache:
            return self._sender_language_cache[sender]
        
        lang = self._detect_language_impl(text)
        
        # Cache by sender for consistency
        if sender:
            self._sender_language_cache[sender] = lang
        
        return lang
    
    def _detect_language_impl(self, text: str) -> str:
        """Internal language detection implementation."""
        if not text or len(text.strip()) < 10:
            return self.default_language
        
        if LANGDETECT_AVAILABLE:
            try:
                lang = detect(text)
                if lang in self.SUPPORTED_LANGUAGES:
                    return lang
            except Exception:
                pass
        else:
            # Simple keyword-based fallback
            text_lower = text.lower()
            
            # French indicators
            if any(w in text_lower for w in ['bonjour', 'merci', "j'ai", 'vous', 'nous', 'très']):
                return 'fr'
            
            # German indicators
            if any(w in text_lower for w in ['guten', 'danke', 'bitte', 'sehr', 'nicht', 'können']):
                return 'de'
            
            # Spanish indicators
            if any(w in text_lower for w in ['hola', 'gracias', 'buenos', 'usted', 'muy']):
                return 'es'
        
        return self.default_language
    
    def get_template(
        self, 
        template_name: str, 
        language: Optional[str] = None
    ) -> str:
        """
        Get a template by name and language.
        
        Args:
            template_name: Base template name (e.g., 'classify', 'system')
            language: Language code (defaults to default_language)
        
        Returns:
            Template string
        """
        lang = language or self.default_language
        
        # Try custom template first
        key = f"{template_name}_{lang}"
        if key in self._custom_templates:
            return self._custom_templates[key]
        
        # Fall back to built-in templates
        if key in self.DEFAULT_TEMPLATES:
            return self.DEFAULT_TEMPLATES[key]
        
        # Fall back to English
        en_key = f"{template_name}_en"
        if en_key in self.DEFAULT_TEMPLATES:
            return self.DEFAULT_TEMPLATES[en_key]
        
        raise ValueError(f"Template not found: {template_name}")
    
    def render(
        self,
        template_name: str,
        subject: str,
        body: str,
        folders: List[str],
        language: Optional[str] = None,
        sender: Optional[str] = None,
        **extra_context
    ) -> str:
        """
        Render a prompt template with context.
        
        Args:
            template_name: Base template name (e.g., 'classify')
            subject: Email subject
            body: Email body (sanitized)
            folders: Available folders
            language: Force language, or auto-detect
            sender: Sender email (for language caching)
            **extra_context: Additional template variables
        
        Returns:
            Rendered prompt string
        """
        # Auto-detect language if not specified
        if language is None:
            language = self.detect_language(f"{subject} {body}", sender)
        
        # Get template
        template_str = self.get_template(template_name, language)
        
        # Build context
        context = {
            "subject": subject,
            "body": body[:1500] if body else "(no body)",
            "folders": folders,
            "folders_json": json.dumps(folders),
            "language": language,
            **extra_context
        }
        
        # Render template
        if JINJA2_AVAILABLE and self._env:
            try:
                template = self._env.from_string(template_str)
                return template.render(**context)
            except Exception as e:
                logger.warning(f"Jinja2 rendering failed: {e}, using simple format")
        
        # Fallback: simple string replacement
        result = template_str
        for key, value in context.items():
            placeholder = "{{ " + key + " }}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result
    
    def get_system_prompt(self, language: Optional[str] = None) -> str:
        """
        Get the system prompt for the specified language.
        
        Args:
            language: Language code (defaults to default_language)
        
        Returns:
            System prompt string
        """
        return self.get_template("system", language or self.default_language)
    
    def clear_language_cache(self) -> None:
        """Clear the sender → language cache."""
        self._sender_language_cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get language cache statistics."""
        return {
            "cached_senders": len(self._sender_language_cache),
            "languages": list(set(self._sender_language_cache.values()))
        }


# Global prompt engine instance
_prompt_engine: Optional[PromptEngine] = None


def get_prompt_engine(
    templates_dir: Optional[str] = None,
    default_language: str = "en"
) -> PromptEngine:
    """
    Get or create the global prompt engine instance.
    
    Args:
        templates_dir: Optional directory for custom templates
        default_language: Fallback language
    
    Returns:
        Global PromptEngine instance
    """
    global _prompt_engine
    
    if _prompt_engine is None:
        _prompt_engine = PromptEngine(
            templates_dir=templates_dir,
            default_language=default_language
        )
    
    return _prompt_engine
