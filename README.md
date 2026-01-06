# MailSorter (Plan V5)

![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange) ![License](https://img.shields.io/badge/license-MIT-blue) ![Status](https://img.shields.io/badge/status-alpha-red)

**Version:** 0.1.0-alpha | [Changelog](CHANGELOG.md) | [Versioning Strategy](docs/VERSIONING.md)

## Description
Système de tri d'emails intelligent pour Thunderbird/Betterbird, utilisant des LLM locaux (Ollama) ou Cloud.
Conçu avec une approche "Privacy First" et une architecture robuste (WebExtension + Native Messaging).

**Performance observée** : 92-98% de précision sur dataset public en conditions contrôlées (voir [Plan V5](docs/PLAN_V5.md) pour méthodologie).

## Documentation
*   **[Plan V5](docs/PLAN_V5.md)** - Source de vérité du projet (spec complète)
*   [Architecture Technique](docs/ARCHITECTURE.md)
*   [Conformité RGPD & Sécurité](docs/RGPD.md)

## Prérequis
*   Thunderbird 115+ ou Betterbird.
*   Python 3.10+.
*   Ollama (pour le mode local) installé et tournant (`ollama serve`).
*   **Sur Windows : pour le développement et l'exécution des tests, exécuter l'environnement dans WSL (ex : Ubuntu).**

## Installation

### 1. Backend (Python)
```bash
cd backend
pip install -r requirements.txt
```

### 2. Enregistrement Native Messaging
Il faut déclarer le script Python à Thunderbird via une clé de registre (Windows) ou un fichier JSON (Linux/Mac).
*   Éditez `backend/app_manifest.json` pour mettre le chemin absolu correct vers `main.py`.
*   **Windows**: Ajoutez une clé de registre dans `HKCU\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend` pointant vers le fichier manifest.

### 3. Extension (Thunderbird)
*   Zippez le contenu du dossier `extension/`.
*   Installez le `.xpi` ou chargez le dossier en mode "Debug Addons" dans Thunderbird.

## Usage
1.  Lancez Ollama : `ollama run llama3` (ou autre modèle).
2.  Ouvrez Thunderbird.
3.  Les nouveaux emails seront analysés et déplacés automatiquement.
4.  Consultez les logs dans `~/.mailsorter/logs/` pour le debug.

## ⚠️ Avertissement
Ce code est une implémentation de référence du Plan V5.
**Ne pas utiliser en production critique sans audit préalable.**

**Statut actuel (v0.1.0-alpha)** :
- ✅ Architecture fonctionnelle
- ✅ Ollama provider opérationnel
- ✅ Privacy Guard (scrubbing PII)
- ⚠️ Configuration partiellement hardcodée
- ⚠️ Parsing MIME simplifié
- ❌ Pas d'installateur Windows automatique
- ❌ Tests incomplets

## Contributing
Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

## License
MIT License - voir [LICENSE](LICENSE)
