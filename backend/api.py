"""
API FastAPI pour le jeu du Loup-Garou
Avec agents IA Anthropic Claude
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from .game_engine import engine
from .models import Role
from .ai_players import set_anthropic_api_key
from .tts_services import get_tts_service, set_gradium_api_key


app = FastAPI(
    title="Loup-Garou Game API",
    description="API pour jouer au Loup-Garou avec des agents IA Anthropic Claude",
    version="2.0.0"
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

class SetApiKeyRequest(BaseModel):
    api_key: str = Field(..., description="Clé API Anthropic")


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


class SendMessageRequest(BaseModel):
    message: str = Field(..., description="Message du joueur humain pendant les discussions")

class SetGradiumKeyRequest(BaseModel):
    api_key: str = Field(..., description="Clé API Gradium pour le TTS")
# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Bienvenue dans l'API Loup-Garou", "version": "2.0.0"}


@app.post("/api/v1/config/anthropic")
async def set_api_key(request: SetApiKeyRequest):
    """Configure la clé API Anthropic"""
    try:
        set_anthropic_api_key(request.api_key)
        return {"success": True, "message": "Clé API Anthropic configurée"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/config/gradium")
async def set_gradium_key(request: SetGradiumKeyRequest):
    """Configure la clé API Gradium pour le TTS"""
    try:
        set_gradium_api_key(request.api_key)
        return {"success": True, "message": "Clé API Gradium configurée"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
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

    # Utiliser la version async
    result = await engine.process_human_action_async(game_id, action)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/discussions")
async def get_discussions(game_id: str):
    """Récupère les discussions du cache (ou génère les discussions initiales si vide)"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    # Récupérer les discussions du cache
    discussions = engine.get_cached_discussions(game_id)

    # Si le cache est vide et on est en phase jour, générer les discussions initiales
    if not discussions and game.phase.value == 'jour':
        discussions = await engine.generate_ai_discussion_async(game_id)

    return {"discussions": discussions}


@app.post("/api/v1/games/{game_id}/message")
async def send_message(game_id: str, request: SendMessageRequest):
    """Envoie un message du joueur humain pendant les discussions"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    # Utiliser la version async
    result = await engine.send_human_message_async(game_id, request.message)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/summary")
async def get_game_summary(game_id: str, player_name: str):
    """Récupère un résumé du jeu pour un joueur"""
    result = engine.get_game_summary(game_id, player_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@app.get("/api/v1/tts/stream")
async def tts_stream(text: str, voice_id: str = "YTpq7expH9539ERJ"):
    """
    Stream audio TTS pour un texte donné
    Utilisé uniquement pendant la phase JOUR pour les discussions des IA
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Le texte ne peut pas être vide")

    tts_service = get_tts_service()

    if not tts_service:
        raise HTTPException(status_code=503, detail="Service TTS non disponible")

    try:
        async def audio_generator():
            async for chunk in tts_service.text_to_speech_stream(text, voice_id):
                yield chunk

        return StreamingResponse(
            audio_generator(),
            media_type="audio/pcm",
            headers={
                "Content-Type": "audio/pcm",
                "X-Sample-Rate": "48000",
                "X-Channels": "1",
                "X-Bit-Depth": "16"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur TTS: {str(e)}")
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
