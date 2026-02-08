# 🐺 Werewolf Game

Play the classic social deduction game "Werewolf" against AI opponents with unique personalities powered by OpenAI models.

## 📋 Description

Werewolf is a strategic social deduction game where players belong to hidden factions and must work together (or against each other) to eliminate their enemies. This implementation features an intelligent AI with distinct personalities, day/night cycles with special actions, dynamic discussions, and text-to-speech voices.

You'll face 8 unique AI characters, each with their own reasoning style and tactics. Can you outwit them?

## 🎮 Features

- **4 distinct roles**: Villager, Werewolf, Seer, Witch
- **8 unique AI personalities** with different traits and strategies
- **Complete day/night cycles** with special actions and voting phases
- **Text-to-speech voices** for immersive AI interactions
- **Real-time discussions** with AI agents responding to your messages
- **Web-based interface** for easy gameplay

## 🛠️ Installation

### Prerequisites

- Python 3.12+
- Node.js (for frontend)
- pip or uv

### Setup

```bash
# Install Python dependencies
pip install -e .

# Or with uv
uv pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Running the Game

```bash
# Start the backend API server
uv run uvicorn backend.api:app --reload

# In another terminal, start the frontend
cd frontend
npm run dev
```

The game will be available at `http://localhost:5173` (frontend) and the API at `http://localhost:8000`.

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/games` | Create a new game |
| GET | `/api/v1/games/{game_id}` | Get current game state |
| POST | `/api/v1/games/{game_id}/actions` | Submit a player action |
| POST | `/api/v1/games/{game_id}/message` | Send message during discussions |
| GET | `/api/v1/games/{game_id}/discussions` | Get AI discussions |
| GET | `/api/v1/games/{game_id}/summary` | Get game summary |
| GET | `/api/v1/tts/stream` | Stream text-to-speech audio |
| POST | `/api/v1/config/openai` | Configure OpenAI API key |
| POST | `/api/v1/config/gradium` | Configure Gradium TTS API key |

## 📚 Project Structure

```
paris-ai/
├── backend/
│   ├── models.py          # Data models (Player, GameState, etc.)
│   ├── ai_players.py      # AI personalities and behaviors
│   ├── game_engine.py     # Core game logic
│   ├── api.py             # FastAPI routes
│   ├── app.py             # Server entry point
│   └── tts_services.py    # Text-to-speech integration
├── frontend/              # React web interface
├── openapi.yaml           # API documentation
├── pyproject.toml
└── README.md
```

## 🎭 AI Personalities

| Name | Background | Style |
|------|------------|-------|
| Marie | Retired teacher | Analytical, suspicious |
| Pierre | Former soldier | Direct, impulsive |
| Sophie | Psychology student | Manipulative, cunning |
| Jean | Baker | Cheerful, naive |
| Élise | Forensic doctor | Cold, logical |
| Lucas | Teenager | Rebellious, unpredictable |
| Margot | Librarian | Mysterious, observant |
| Henri | Mayor | Political, calculating |

## 🎯 Gameplay Example

```
Night falls over the village...
You are the SEER!
6 players gathered: Marie, Pierre, Sophie, Jean, Élise and you.

[You choose to investigate Pierre]

Your visions reveal... Pierre is a WEREWOLF! 🐺

The sun rises. Jean has been killed...

[Day discussion begins]
Marie: "Something suspicious about Pierre!"
Henri: "I agree, he's been quiet..."
[You speak up about your findings...]
```

## 📜 Game Rules

### Factions
- **Village**: Must eliminate all werewolves
- **Werewolves**: Must equal or outnumber the villagers

### Roles
- **Villager**: Vote to eliminate suspects (no special powers)
- **Werewolf**: Choose a victim each night (work with other wolves)
- **Seer**: Discover the true role of one player per night
- **Witch**: Use life potion to save victims or death potion to eliminate players (one use each)

### Game Flow
1. **Night Phase**: Werewolves attack, special roles use their powers
2. **Day Phase**: Discussion and voting to eliminate a suspect

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or pull request.

## 📄 License

MIT License - see LICENSE file for details.
