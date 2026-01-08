# Agent Context Rules

## Objectif
L'agent DOIT avoir accès au fichier `.instructions/tasks.md` pour le suivi des tâches du projet.

## Problème
Le fichier `tasks.md` est dans le `.gitignore` (pour éviter qu'il soit poussé sur le cloud). Par défaut, Antigravity respecte le `.gitignore` et refuse d'accéder à ces fichiers.

## Solutions Explorées (Ne fonctionnent PAS au runtime)

| Approche | Fichier créé | Résultat |
|----------|-------------|----------|
| Pattern de négation `.gitignore` | `!.instructions/tasks.md` | ❌ Fonctionne pour l'agent mais **PAS ACCEPTABLE** car le fichier serait poussé sur Git |
| `.aiexclude` avec négation | `.aiexclude` | ❌ Ne fonctionne pas au runtime |
| `.geminiignore` avec négation | `.geminiignore` | ❌ Ne fonctionne pas au runtime |
| Gemini CLI settings | `.gemini/settings.json` | ❌ Ne fonctionne pas pour cet agent |
| Gemini config.yaml | `.gemini/config.yaml` | ❌ Ne fonctionne pas pour cet agent |
| VS Code workspace settings | `.vscode/settings.json` | ❌ Bloqué par .gitignore lui-même |

## Solution Qui Fonctionne

**Action requise de l'utilisateur** : Modifier le paramètre dans l'interface Antigravity.

### Instructions
1. Ouvrir Antigravity (ou VS Code avec Gemini Code Assist)
2. Aller dans **Settings** (`Ctrl + ,` ou `Cmd + ,`)
3. Chercher **"Allow Gitignored Files"** (pour Antigravity) ou **"Context Exclusion Gitignore"** (pour Gemini Code Assist)
4. **Activer** "Allow Gitignored Files" ou **Désactiver** "Context Exclusion Gitignore"

### Effet
- Git continuera d'ignorer les fichiers (ils ne seront pas poussés)
- L'agent pourra lire ces fichiers normalement

## Fichiers de configuration créés (peuvent être supprimés)
Ces fichiers ont été créés lors de la recherche mais ne sont pas nécessaires :
- `.aiexclude`
- `.geminiignore`
- `.gemini/settings.json`
- `.gemini/config.yaml`

