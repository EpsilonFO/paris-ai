# 🐺 Loup-Garou - Serveur MCP

Un serveur MCP (Model Context Protocol) pour jouer au Loup-Garou contre des IA avec des personnalités uniques. Compatible avec Claude, Alpic et tout client MCP.

## 📋 Description

Ce projet implémente le jeu de société Loup-Garou de Thiercelieux sous forme de serveur MCP. L'utilisateur joue contre plusieurs joueurs IA, chacun ayant une personnalité distincte qui influence leur comportement, leurs accusations et leurs stratégies.

## 🎮 Fonctionnalités

- **4 rôles** : Villageois, Loup-Garou, Voyante, Sorcière
- **8 personnalités IA** uniques avec des traits de caractère différents
- **Cycles jour/nuit** complets avec actions nocturnes et votes
- **Serveur MCP** compatible avec Claude et Alpic

## 🛠️ Installation

### Prérequis

- Python 3.10+
- pip ou uv

### Installation locale

```bash
cd loup-garou

# Avec pip
pip install -e .

# Ou avec uv
uv pip install -e .
```

### Lancer le serveur MCP

```bash
python -m src.mcp_server
```

## 🔧 Configuration MCP

### Pour Claude Desktop

Ajouter dans `~/.claude/claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "loup-garou": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/chemin/vers/loup-garou"
    }
  }
}
```

### Pour Alpic

Déployer le serveur MCP et configurer l'URL dans Alpic.

### Outils MCP disponibles

| Outil | Description |
|-------|-------------|
| `create_game` | Créer une nouvelle partie |
| `get_game_state` | Obtenir l'état actuel du jeu |
| `wolf_attack` | Choisir une victime (Loup-Garou) |
| `seer_observe` | Observer un joueur (Voyante) |
| `witch_action` | Utiliser les potions (Sorcière) |
| `skip_night` | Passer la nuit (Villageois) |
| `get_discussions` | Obtenir les discussions IA |
| `vote` | Voter pour éliminer un joueur |

## 📚 Structure du Projet

```
loup-garou/
├── src/
│   ├── __init__.py
│   ├── models.py          # Modèles de données (Player, GameState, etc.)
│   ├── ai_players.py      # Personnalités et comportements IA
│   ├── game_engine.py     # Moteur de jeu principal
│   └── api.py             # API FastAPI
├── chatgpt_instructions.md # Instructions pour le GPT
├── openapi.yaml           # Schéma OpenAPI pour les Actions
├── requirements.txt
└── README.md
```

## 🎭 Personnalités IA

| Nom | Description | Style |
|-----|-------------|-------|
| Marie | Institutrice retraitée | Analytique, méfiante |
| Pierre | Ancien militaire | Direct, impulsif |
| Sophie | Étudiante en psycho | Manipulatrice |
| Jean | Boulanger | Jovial, naïf |
| Élise | Médecin légiste | Froide, logique |
| Lucas | Adolescent | Rebelle, imprévisible |
| Margot | Libraire | Mystérieuse, observatrice |
| Henri | Maire | Politique, calculateur |

## 🔌 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/games` | Créer une nouvelle partie |
| GET | `/api/v1/games/{id}` | État actuel du jeu |
| POST | `/api/v1/games/{id}/actions` | Soumettre une action |
| GET | `/api/v1/games/{id}/discussions` | Discussions IA |
| GET | `/api/v1/games/{id}/summary` | Résumé pour un joueur |

## 🎯 Exemple de Partie

```
Utilisateur: Je veux jouer au Loup-Garou !

GPT: 🐺 Bienvenue dans le village de Thiercelieux !
     Quel est votre nom, voyageur ?

Utilisateur: Alexandre

GPT: 🌙 La nuit tombe sur le village...
     Vous êtes la VOYANTE !
     6 joueurs sont réunis : Marie, Pierre, Sophie, Jean, Élise et vous.
     Qui souhaitez-vous observer cette nuit ?

Utilisateur: Je veux observer Pierre

GPT: Vos visions vous révèlent... Pierre est un LOUP-GAROU ! 🐺
     Le soleil se lève. Jean a été dévoré cette nuit...
```

## 📜 Règles du Jeu

### Factions
- **Village** : Doit éliminer tous les loups
- **Loups-Garous** : Doivent égaler ou dépasser le nombre de villageois

### Rôles
- **Villageois** : Vote pour éliminer les suspects
- **Loup-Garou** : Choisit une victime chaque nuit
- **Voyante** : Observe le rôle d'un joueur par nuit
- **Sorcière** : Possède une potion de vie et une de mort

### Déroulement
1. **Nuit** : Les loups attaquent, les rôles spéciaux agissent
2. **Jour** : Discussion puis vote pour éliminer un suspect

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

MIT License - voir le fichier LICENSE pour plus de détails.
