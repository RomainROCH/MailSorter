# Plan V5 – Tri d'emails par LLM dans Thunderbird/Betterbird

> **Document de référence** pour l'implémentation MailSorter.  
> Toute modification du code ou de l'architecture doit être validée par rapport à ce plan.

---

## 1. Précision et Benchmarking

### Scores de Précision
> **Pipeline hybride V5 : 92–98%** (plage observée sur dataset public, **non garantie en production** ; voir méthodologie ci-dessous)

### ⚠️ Avertissement Méthodologique
- **Conditions contrôlées** : Les scores sont mesurés sur un dataset public de référence (ex : Enron Email Dataset, SpamAssassin Corpus).
- **Variabilité en production** : Les résultats peuvent varier selon :
  - La langue des emails (optimisé pour FR/EN).
  - La typologie métier (B2B, newsletters, etc.).
  - Le modèle LLM utilisé (Llama 3 vs GPT-4o-mini).
- **Reproductibilité** : Le protocole d'évaluation complet est disponible dans `tests/benchmark/`.

### Distinction Spam/Phishing/Ham
- **Spam** : Emails publicitaires non sollicités.
- **Phishing** : Tentatives de fraude (usurpation d'identité, liens malveillants).
- **Ham** : Emails légitimes (personnels, professionnels, newsletters opt-in).

---

## 2. Réentraînement et Adaptation

### Modèles Locaux (Ollama, Llama, Mistral)
- **Réentraînement automatique** : Possible via fine-tuning local avec feedback utilisateur.
- **Privacy** : Les données restent sur la machine de l'utilisateur.
- **Implémentation** : Module `backend/core/feedback_loop.py` (à développer).

### Modèles Cloud (OpenAI, Anthropic, Gemini)
- **Pas de fine-tuning** : Les API Cloud ne permettent pas le réentraînement direct.
- **Adaptation indirecte** : 
  - Règles personnalisées (allow/deny lists).
  - Ajustement de seuils de confiance.
  - Historique de décisions pour prompt engineering contextuel (si activé).

### ⚠️ RGPD et Feedback Utilisateur
> "La collecte de feedback utilisateur (actions de tri manuelles) est soumise au RGPD. L'utilisateur doit être informé et consentir explicitement à l'utilisation de ces données pour l'adaptation du modèle (local uniquement)."

---

## 3. Robustesse Manifest V3 et Compatibilité

### Feature Detection
- **Vérification dynamique** : Avant d'utiliser une API Thunderbird (ex : `messages.update({ headers })`), le code doit vérifier sa disponibilité.
- **Implémentation** : Module `extension/background/feature_detection.js` (à développer).

### Fallback IMAP
- **Si API indisponible** : Utiliser les flags IMAP natifs ou les tags internes de Thunderbird.
- **Documentation** : Liste des versions Thunderbird/Betterbird supportées et leurs limitations.

### Exemple de Code (à intégrer)
```javascript
// TODO: Vérifier support de messages.update({ headers })
if (typeof browser.messages.update !== 'undefined') {
    // Utiliser les custom headers
} else {
    // Fallback: IMAP flags ou tags
}
```

---

## 4. RGPD et Conformité

### Base Légale
- **Intérêt légitime (Art. 6.1.f RGPD)** : Pour un usage individuel (organisation personnelle).
- **Consentement explicite** : Requis si déployé dans un contexte professionnel avec traitement de données tierces.

### DPIA (Étude d'Impact)
> **Recommandation** : Toute organisation souhaitant déployer MailSorter sur plus de 10 utilisateurs ou traitant des données sensibles (santé, juridique) doit réaliser une **DPIA (Data Protection Impact Assessment)** selon l'Art. 35 RGPD.

### Checklist Conformité
- [x] **Minimisation des données** : Troncature à 2000 caractères, scrubbing PII.
- [x] **DPA (Data Processing Agreement)** : Si utilisation d'un modèle Cloud, vérifier le contrat du fournisseur.
- [ ] **SCC/DPF (Standard Contractual Clauses / Data Privacy Framework)** : Pour les transferts hors UE (ex : OpenAI USA).
- [ ] **Audits réguliers** : Logs, revue des décisions du modèle.
- [x] **Droit d'opposition** : Possibilité de désactiver le tri automatique (Mode Passif).

---

## 5. Gestion des Pièces Jointes

### ⚠️ Limitation
> **Les pièces jointes ne sont pas analysées en contenu** (raisons : performance, sécurité, RGPD).

### Collecte Minimale
- **Hash SHA256** : Empreinte unique pour détection de doublons/malwares connus.
- **Type MIME** : Pour heuristique (ex : `.exe`, `.pdf`, `.html` joints suspects).
- **Heuristique légère** : 
  - Email avec PJ `.exe` + langage urgent → Score de phishing +0.3.
  - Email avec facture `.pdf` + expéditeur vérifié → Score légitime +0.2.

### Implémentation
- Module `backend/core/attachment_heuristic.py` (à développer).

---

## 6. Modes de Fonctionnement Avancés

### Mode "Headers-Only"
- **Usage** : Environnements ultra-sensibles (juridique, santé).
- **Analyse uniquement** : Sujet, expéditeur, destinataire, date, headers techniques.
- **Corps du message** : Non transmis au LLM.
- **Configuration** : `backend/config.json` → `"analysis_mode": "headers_only"`

### Seuil de Confiance Dynamique
- **Principe** : Le seuil d'acceptation varie selon le dossier cible.
- **Exemple** :
  - Inbox → Archives : Seuil 0.6 (tolérant).
  - Inbox → Factures : Seuil 0.85 (strict, enjeu financier).
  - Inbox → Trash : Seuil 0.95 (très strict, irréversible).
- **Configuration** : `backend/config.json` → `"thresholds": { "Factures": 0.85 }`

---

## 7. Sécurité des Métadonnées

### Problème
Les headers personnalisés (`X-LLM-Category`, `X-LLM-Score`) peuvent être falsifiés localement.

### Solution Recommandée
- **Signature HMAC** : Ajouter un header `X-LLM-Signature` contenant un HMAC-SHA256 des métadonnées avec une clé secrète utilisateur.
- **Vérification** : À chaque lecture, valider la signature avant de faire confiance au tag.
- **Implémentation** : Module `backend/utils/security.py` (à développer).

### Exemple de Header Signé
```
X-LLM-Category: Factures
X-LLM-Score: 0.92
X-LLM-Signature: a3f8e9d2c1b0...
```

---

## 8. Performance et Latence

### Batch API (OpenAI, Anthropic)
> **Latence jusqu'à 24h** : Adapté au tri d'archives ou de messages en masse.

### Mode Temps Réel (API Standard)
> **Latence < 2s** : Recommandé pour les nouveaux emails entrants.

### Configuration
- **Automatique** : Le système détecte les "nouveaux emails" (onNewMailReceived) → Temps réel.
- **Manuel** : L'utilisateur lance un tri d'archives → Batch API (si disponible).

### Documentation Utilisateur
> "Le tri des nouveaux emails se fait en temps réel (1-3 secondes). Le tri des archives peut prendre plusieurs heures selon le volume et le fournisseur LLM."

---

## 9. Architecture Model-Agnostic

### Principe
> **Le pipeline est conçu pour être model-agnostic**, garantissant la portabilité future et la compatibilité avec de nouveaux LLMs sans refonte majeure.

### Implémentation
- **Interface abstraite** : `backend/providers/base.py` définit le contrat.
- **Nouveaux providers** : Ajouter un fichier `backend/providers/<nom>_provider.py` implémentant `LLMProvider`.
- **Configuration** : Sélection du provider dans `backend/config.json` → `"provider": "ollama"` ou `"provider": "openai"`.

### Exemple d'Ajout (Gemini)
```python
# backend/providers/gemini_provider.py
from .base import LLMProvider

class GeminiProvider(LLMProvider):
    def classify_email(self, subject, body, folders):
        # Implémentation avec l'API Gemini
        pass
```

---

## Checklist Finale d'Intégration

- [x] Scores de précision reformulés et contextualisés
- [x] Réentraînement clarifié (local vs cloud)
- [ ] Feature detection et fallback documentés (code à développer)
- [x] RGPD : base légale + DPIA ajoutées
- [ ] Gestion minimale des attachments (code à développer)
- [ ] Mode headers-only et seuil dynamique intégrés (code à développer)
- [ ] Sécurité des headers (chiffrement/signature) (code à développer)
- [x] Latence batch API explicitée
- [x] Architecture model-agnostic documentée

---

**Ce Plan V5 est la source de vérité pour l'implémentation MailSorter. Toute modification doit être validée par audit RGPD et revue technique.**
