# Architecture Technique - MailSorter (Plan V5)

## Vue d'ensemble
MailSorter utilise une architecture hybride **WebExtension + Native Messaging Host** pour contourner les limitations des extensions de navigateur (CORS, accès système) et permettre un traitement IA local robuste et sécurisé.

**Principe clé** : Architecture **model-agnostic** garantissant la portabilité future et la compatibilité avec de nouveaux LLMs sans refonte majeure.

```ascii
+-----------------------+          +-----------------------+          +-----------------------+
|  Thunderbird (Client) |          |  Native Host (Python) |          |      LLM Provider     |
|                       |  STDIO   |                       |   HTTP   |                       |
| [Background Script]   |<-------->| [Main Loop]           |<-------->| [Ollama / OpenAI]     |
| - Listen New Mail     |   JSON   | - Protocol Handler    |   JSON   |                       |
| - Extract Content     |          | - Privacy Guard       |          |                       |
| - Apply Move/Tag      |          | - Orchestrator        |          |                       |
+-----------------------+          +-----------------------+          +-----------------------+
```

## Composants

### 1. Extension Thunderbird (Frontend)
*   **`manifest.json`**: Déclare les permissions (`messagesRead`, `messagesModify`, `nativeMessaging`).
*   **`background.js`**:
    *   Écoute l'événement `browser.messages.onNewMailReceived`.
    *   Extrait les métadonnées (Sujet, Expéditeur, Extrait du corps).
    *   Envoie une requête de classification au Native Host.
    *   Reçoit la décision et déplace le message via `browser.messages.move`.
*   **`options/`**: Interface de configuration (Choix du modèle, URL API, Whitelist).

### 2. Native Messaging Host (Backend)
*   **`main.py`**: Point d'entrée. Gère la boucle de lecture/écriture sur `stdin`/`stdout` selon le protocole de longueur préfixée (4 octets).
*   **`core/privacy.py`**: **CRITIQUE**. Nettoie les données avant tout envoi au LLM.
    *   Suppression d'emails, téléphones, IPs via Regex.
    *   Troncature du corps du message (ex: 2000 chars).
*   **`core/orchestrator.py`**: Coordonne le flux. Charge la config, appelle le Privacy Guard, interroge le Provider.
*   **`providers/`**: Interface abstraite pour les LLMs.
    *   `OllamaProvider`: Pour l'inférence locale (Llama3, Mistral).
    *   `OpenAIProvider`: Pour l'inférence cloud (GPT-4o-mini).

## Flux de Données (Data Flow)

1.  **Réception**: Un email arrive. `background.js` capture l'ID.
2.  **Extraction**: Le script récupère les headers et le body (texte brut).
3.  **Transmission**: Envoi JSON au script Python via `runtime.sendNativeMessage`.
4.  **Sanitization**: Python reçoit, `PrivacyGuard` anonymise le texte.
5.  **Inférence**: `LLMProvider` construit le prompt avec la liste des dossiers disponibles.
6.  **Décision**: Le LLM retourne le nom du dossier cible.
7.  **Action**: Python renvoie la cible à Thunderbird. Thunderbird déplace le message.

## Sécurité & Robustesse

*   **Isolation**: Le script Python tourne avec les droits de l'utilisateur mais est isolé du réseau global sauf pour l'API LLM configurée.
*   **Fallback**: Si le LLM est inaccessible ou hallucine un dossier inexistant, l'email reste dans "Inbox" et une erreur est loggée.
*   **Anti-Hallucination**: Le prompt système force le LLM à choisir *uniquement* parmi une liste JSON fournie.
*   **Feature Detection** : Avant d'utiliser une API Thunderbird (ex : `messages.update({ headers })`), le code vérifie sa disponibilité dynamiquement.
*   **Fallback IMAP** : Si modification des headers non supportée, utilisation de flags IMAP ou tags internes (à documenter selon versions TB/BB).

## Éléments du Plan V5 Implémentés

### ✅ Déjà Implémenté
- Architecture model-agnostic (interface `LLMProvider`)
- Privacy Guard avec scrubbing PII
- Minimisation données (troncature 2000 chars)
- Gestion des timeouts et erreurs
- Logs sécurisés (stderr only)
- Documentation RGPD avec base légale et DPIA

### 🔄 En Développement (Modules à créer)
- **Feature Detection** : `extension/background/feature_detection.js`
- **Mode Headers-Only** : Configuration `backend/config.json` → `"analysis_mode": "headers_only"`
- **Seuil Dynamique** : Configuration par dossier → `"thresholds": { "Factures": 0.85 }`
- **Gestion Attachments** : `backend/core/attachment_heuristic.py` (hash, MIME, heuristique)
- **Sécurité Headers** : `backend/utils/security.py` (signature HMAC)
- **Feedback Loop Local** : `backend/core/feedback_loop.py` (fine-tuning Ollama)
- **OpenAI Provider** : `backend/providers/openai_provider.py`
- **Batch vs Temps Réel** : Détection automatique du contexte

### ⚠️ Limitations Actuelles
- Corps du message extrait de manière simplifiée (voir TODO dans `background.js`)
- Configuration hardcodée (modèle, URL Ollama) → À externaliser dans `config.json`
- Pas d'analyse du contenu des pièces jointes (par design, conforme Plan V5)
