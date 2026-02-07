"""
API FastAPI pour le jeu du Loup-Garou
Compatible avec les ChatGPT Custom Actions
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from .game_engine import engine
from .models import Role

app = FastAPI(
    title="Loup-Garou Game API",
    description="API pour jouer au Loup-Garou avec des IA",
    version="1.0.0"
)

# CORS pour permettre les appels depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modèles Pydantic ---

class CreateGameRequest(BaseModel):
    player_name: str = Field(..., description="Nom du joueur humain")
    num_players: int = Field(default=6, ge=4, le=10, description="Nombre total de joueurs")
    num_wolves: int = Field(default=2, ge=1, le=3, description="Nombre de loups-garous")
    include_seer: bool = Field(default=True, description="Inclure la Voyante")
    include_witch: bool = Field(default=True, description="Inclure la Sorcière")


class PlayerActionRequest(BaseModel):
    action: str = Field(..., description="Type d'action")
    target: Optional[str] = Field(default=None, description="Cible de l'action")
    save: Optional[bool] = Field(default=False, description="Sauver la victime (Sorcière)")
    kill: Optional[str] = Field(default=None, description="Tuer un joueur (Sorcière)")


# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Bienvenue dans l'API Loup-Garou", "version": "1.0.0"}


@app.post("/api/v1/games")
async def create_game(request: CreateGameRequest):
    """Crée une nouvelle partie de Loup-Garou"""
    game = engine.create_game(
        human_name=request.player_name,
        num_players=request.num_players,
        num_wolves=request.num_wolves,
        include_seer=request.include_seer,
        include_witch=request.include_witch
    )

    human_player = next(p for p in game.players if p.is_human)

    response = {
        "game_id": game.game_id,
        "your_role": human_player.role.display_name,
        "your_faction": human_player.role.faction.value,
        "players": [
            {
                "name": p.name,
                "is_human": p.is_human,
                "personality": p.personality
            }
            for p in game.players
        ],
        "message": _generate_intro_message(human_player.role)
    }

    # Si le joueur est loup, révéler les alliés
    if human_player.role == Role.LOUP_GAROU:
        other_wolves = [p.name for p in game.get_wolves() if p.name != human_player.name]
        response["fellow_wolves"] = other_wolves

    return response


@app.get("/api/v1/games/{game_id}")
async def get_game_state(game_id: str):
    """Récupère l'état actuel de la partie"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    human_player = next((p for p in game.players if p.is_human), None)
    player_name = human_player.name if human_player else None

    return game.to_dict(player_perspective=player_name)


@app.post("/api/v1/games/{game_id}/actions")
async def process_action(game_id: str, request: PlayerActionRequest):
    """Traite une action du joueur humain"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    action = {
        "action": request.action,
        "target": request.target,
        "save": request.save,
        "kill": request.kill
    }

    result = engine.process_human_action(game_id, action)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/discussions")
async def get_discussions(game_id: str):
    """Génère les discussions des joueurs IA"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    discussions = engine.generate_ai_discussion(game_id)
    return {"discussions": discussions}


@app.get("/api/v1/games/{game_id}/summary")
async def get_game_summary(game_id: str, player_name: str):
    """Récupère un résumé du jeu pour un joueur"""
    result = engine.get_game_summary(game_id, player_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


def _generate_intro_message(role: Role) -> str:
    """Génère le message d'introduction selon le rôle"""
    messages = {
        Role.VILLAGEOIS: (
            "Vous êtes un simple Villageois. Vous n'avez pas de pouvoir spécial, "
            "mais votre vote est crucial pour démasquer les loups. "
            "Observez attentivement les comportements suspects !"
        ),
        Role.LOUP_GAROU: (
            "Vous êtes un Loup-Garou ! Chaque nuit, vous choisirez une victime "
            "avec vos complices. Le jour, fondez-vous parmi les villageois "
            "et détournez les soupçons. La survie de la meute dépend de vous."
        ),
        Role.VOYANTE: (
            "Vous êtes la Voyante. Chaque nuit, vous pouvez découvrir "
            "le véritable rôle d'un joueur. Utilisez ce pouvoir avec sagesse "
            "pour guider le village vers la victoire."
        ),
        Role.SORCIERE: (
            "Vous êtes la Sorcière. Vous possédez deux potions : "
            "une de vie pour sauver la victime des loups, "
            "une de mort pour éliminer un suspect. "
            "Chaque potion ne peut être utilisée qu'une seule fois."
        ),
    }
    return messages.get(role, "Bienvenue dans la partie !")


# Pour exécuter avec uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
