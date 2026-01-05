# Conformité RGPD & Sécurité (Plan V5)

## 1. Base Légale et Finalité
*   **Finalité**: Tri automatique des emails pour l'organisation personnelle ou professionnelle.
*   **Base Légale**: 
    *   **Intérêt légitime (Art. 6.1.f RGPD)** : Pour un usage individuel (organisation personnelle).
    *   **Consentement explicite** : Requis si déployé dans un contexte professionnel avec traitement de données tierces.
*   **DPIA (Étude d'Impact)** : Toute organisation souhaitant déployer MailSorter sur plus de 10 utilisateurs ou traitant des données sensibles (santé, juridique) doit réaliser une **DPIA (Data Protection Impact Assessment)** selon l'Art. 35 RGPD.

## 2. Minimisation des Données (Data Minimization)
Le système applique une politique stricte de minimisation **avant** tout traitement par le modèle d'IA (surtout pour les modèles Cloud).

*   **Filtrage PII**: Les entités suivantes sont masquées par le module `PrivacyGuard` :
    *   Adresses email -> `<EMAIL_REDACTED>`
    *   Numéros de téléphone -> `<PHONE_REDACTED>`
    *   Adresses IP -> `<IP_REDACTED>`
*   **Troncature**: Le corps du message est tronqué à 2000 caractères pour limiter l'exposition du contexte.
*   **Pièces Jointes**: **NON TRAITÉES**. Seuls les noms de fichiers et types MIME sont analysés.

## 3. Stockage et Rétention
*   **Local (Ollama)**: 
    *   Aucune donnée ne quitte la machine de l'utilisateur. 
    *   Les logs d'inférence sont éphémères ou désactivés par défaut.
    *   **Feedback & Adaptation** : Le réentraînement/fine-tuning local est possible avec consentement explicite.
*   **Cloud (OpenAI/Autre)**:
    *   Les données envoyées sont soumises à la politique de confidentialité du fournisseur tiers.
    *   MailSorter n'ajoute aucune rétention intermédiaire.
    *   Les clés API sont stockées dans le gestionnaire de mots de passe du système (Keyring), jamais en clair dans les fichiers de config.
    *   **Feedback & Adaptation** : Aucun fine-tuning cloud. Seule l'adaptation indirecte (règles, seuils, allow/deny lists) est possible.
    *   **Transferts hors UE** : Vérifier les clauses contractuelles standard (SCC) ou le Data Privacy Framework (DPF) du fournisseur.

## 4. Droits des Utilisateurs
*   **Droit d'accès/rectification**: L'utilisateur a accès à tous les logs via le dossier `.instructions-output/` (si activé).
*   **Droit d'opposition**: Le système peut être désactivé instantanément via l'icône de l'extension ("Mode Passif").

## 5. Analyse d'Impact (DPIA) Simplifiée
*   **Risque**: Fuite de données confidentielles vers un tiers (LLM Cloud).
*   **Mesure**:
    1.  Support prioritaire des LLM Locaux (Ollama).
    2.  Sanitization regex stricte par défaut.
    3.  Avertissement clair lors de la configuration d'un provider Cloud.

## 6. Sécurité Technique
*   **Communication**: Utilisation exclusive de `Native Messaging` (stdio) entre Thunderbird et Python. Pas de serveur HTTP local ouvert sur le réseau.
*   **Dépendances**: Scan régulier des vulnérabilités Python (`pip-audit`).
*   **Headers personnalisés** : Recommandation de signature HMAC pour éviter la falsification locale (voir Plan V5).

## 7. Checklist de Conformité
- [x] **Minimisation des données** : Troncature à 2000 caractères, scrubbing PII.
- [x] **DPA (Data Processing Agreement)** : Si utilisation d'un modèle Cloud, vérifier le contrat du fournisseur.
- [ ] **SCC/DPF (Standard Contractual Clauses / Data Privacy Framework)** : Pour les transferts hors UE (ex : OpenAI USA).
- [ ] **Audits réguliers** : Logs, revue des décisions du modèle.
- [x] **Droit d'opposition** : Possibilité de désactiver le tri automatique (Mode Passif).
- [ ] **DPIA** : Si déploiement professionnel > 10 utilisateurs ou données sensibles.
