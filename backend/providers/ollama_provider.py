import requests
from typing import List, Optional
from .base import LLMProvider
from ..utils.logger import logger

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class OllamaProvider(LLMProvider):
    """
    Implémentation pour Ollama (Local LLM).
    Respecte la contrainte "Model Agnostic" et "Privacy First".
    """

    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url
        self.model = model
        self.api_endpoint = f"{base_url}/api/generate"

    def health_check(self) -> bool:
        """
        Check if Ollama is running and the model is available.
        Uses the /api/tags endpoint to verify connectivity.
        """
        try:
            # Ollama exposes /api/tags to list available models
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                logger.warning(f"Ollama health check returned status {response.status_code}")
                return False
            
            # Optionally verify the configured model is available
            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            
            if self.model not in models and f"{self.model}:latest" not in [m.get("name", "") for m in data.get("models", [])]:
                logger.warning(f"Model '{self.model}' not found in Ollama. Available: {models}")
                # Still return True if Ollama is running, just warn about model
            
            return True
        except requests.exceptions.Timeout:
            logger.warning("Ollama health check timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to Ollama - is it running?")
            return False
        except Exception as e:
            logger.warning(f"Ollama Health Check Failed: {e}")
            return False

    def classify_email(
        self, subject: str, body: str, available_folders: List[str]
    ) -> Optional[str]:
        """
        Utilise Ollama pour classifier l'email.
        """
        # Construction du prompt Anti-Hallucination
        folders_str = ", ".join([f'"{f}"' for f in available_folders])

        prompt = f"""
        You are an intelligent email sorting assistant.
        Task: Categorize the following email into ONE of the existing folders.
        
        Constraints:
        1. You must ONLY reply with the exact name of the folder.
        2. Do not add any explanation or punctuation.
        3. If the email does not fit any specific folder, reply "Inbox".
        
        Available Folders: [{folders_str}]
        
        Email Subject: {subject}
        Email Body Snippet: {body}
        
        Folder:
        """

        payload = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            response = requests.post(self.api_endpoint, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            predicted_folder = result.get("response", "").strip()

            # Validation post-traitement (Anti-Hallucination)
            # On vérifie que le dossier prédit existe vraiment
            if predicted_folder in available_folders:
                return predicted_folder
            elif "Inbox" in predicted_folder:  # Fallback soft
                return "Inbox"
            else:
                logger.warning(
                    f"Hallucination detected: '{predicted_folder}' not in {available_folders}"
                )
                return None  # Fallback to Inbox handled by caller

        except requests.exceptions.Timeout:
            logger.error("Ollama Timeout - Fallback to Inbox")
            return None
        except Exception as e:
            logger.error(f"Ollama Inference Error: {e}")
            return None
