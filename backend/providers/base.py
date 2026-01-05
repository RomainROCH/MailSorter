from abc import ABC, abstractmethod
from typing import List, Optional

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


class LLMProvider(ABC):
    """
    Interface abstraite pour les fournisseurs de LLM (Model Agnostic).
    """

    @abstractmethod
    def classify_email(
        self, subject: str, body: str, available_folders: List[str]
    ) -> Optional[str]:
        """
        Analyse un email et retourne le nom du dossier le plus approprié.
        Doit retourner None si aucune correspondance fiable n'est trouvée (Fallback).
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Vérifie si le service est disponible.
        """
        pass
