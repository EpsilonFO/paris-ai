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
    title="Werewolf Game API",
    description="API to play Werewolf with Anthropic Claude AI agents",
    version="2.0.0"
)

# CORS to allow calls from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class SetApiKeyRequest(BaseModel):
    api_key: str = Field(..., description="Anthropic API key")


class CreateGameRequest(BaseModel):
    player_name: str = Field(..., description="Human player name")
    num_players: int = Field(default=6, ge=4, le=10, description="Total number of players")
    num_wolves: int = Field(default=2, ge=1, le=3, description="Number of werewolves")
    include_seer: bool = Field(default=True, description="Include the Seer")
    include_witch: bool = Field(default=True, description="Include the Witch")


class PlayerActionRequest(BaseModel):
    action: str = Field(..., description="Action type")
    target: Optional[str] = Field(default=None, description="Action target")
    save: Optional[bool] = Field(default=False, description="Save the victim (Witch)")
    kill: Optional[str] = Field(default=None, description="Kill a player (Witch)")


class SendMessageRequest(BaseModel):
    message: str = Field(..., description="Human player message during discussions")

class SetGradiumKeyRequest(BaseModel):
    api_key: str = Field(..., description="Gradium API key for TTS")
# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Welcome to the Werewolf API", "version": "2.0.0"}


@app.post("/api/v1/config/anthropic")
async def set_api_key(request: SetApiKeyRequest):
    """Configure Anthropic API key"""
    try:
        set_anthropic_api_key(request.api_key)
        return {"success": True, "message": "Anthropic API key configured"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/config/gradium")
async def set_gradium_key(request: SetGradiumKeyRequest):
    """Configure Gradium API key for TTS"""
    try:
        set_gradium_api_key(request.api_key)
        return {"success": True, "message": "Gradium API key configured"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/api/v1/games")
async def create_game(request: CreateGameRequest):
    """Create a new Werewolf game"""
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
    """Get current game state"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    human_player = next((p for p in game.players if p.is_human), None)
    player_name = human_player.name if human_player else None

    return game.to_dict(player_perspective=player_name)


@app.post("/api/v1/games/{game_id}/actions")
async def process_action(game_id: str, request: PlayerActionRequest):
    """Process human player action"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    action = {
        "action": request.action,
        "target": request.target,
        "save": request.save,
        "kill": request.kill
    }

    # Use async version
    result = await engine.process_human_action_async(game_id, action)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/discussions")
async def get_discussions(game_id: str):
    """Get discussions from cache (or generate initial discussions if empty)"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get discussions from cache
    discussions = engine.get_cached_discussions(game_id)

    # If cache is empty and in day phase, generate initial discussions
    if not discussions and game.phase.value == 'jour':
        discussions = await engine.generate_ai_discussion_async(game_id)

    return {"discussions": discussions}


@app.post("/api/v1/games/{game_id}/message")
async def send_message(game_id: str, request: SendMessageRequest):
    """Send human player message during discussions"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Use async version
    result = await engine.send_human_message_async(game_id, request.message)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/summary")
async def get_game_summary(game_id: str, player_name: str):
    """Get game summary for a player"""
    result = engine.get_game_summary(game_id, player_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@app.get("/api/v1/tts/stream")
async def tts_stream(text: str, voice_id: str = "YTpq7expH9539ERJ"):
    """
    Stream audio TTS for given text
    Only used during DAY phase for AI discussions
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    print(f"[API_TTS] TTS request received for: {text[:100]}..." if len(text) > 100 else f"[API_TTS] TTS request received for: {text}")

    tts_service = get_tts_service()

    if not tts_service:
        raise HTTPException(status_code=503, detail="TTS service unavailable")

    try:
        async def audio_generator():
            print(f"[API_TTS] Audio streaming started...")
            async for chunk in tts_service.text_to_speech_stream(text, voice_id):
                yield chunk
            print(f"[API_TTS] Audio streaming completed")

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
        print(f"[API_TTS] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

def _generate_intro_message(role: Role) -> str:
    """Generate introduction message based on role"""
    messages = {
        Role.VILLAGEOIS: (
            "You are a simple Villager. You have no special power, "
            "but your vote is crucial to unmask the werewolves. "
            "Observe suspicious behaviors carefully!"
        ),
        Role.LOUP_GAROU: (
            "You are a Werewolf! Each night, you will choose a victim "
            "with your accomplices. During the day, blend in with the villagers "
            "and divert suspicion. The pack's survival depends on you."
        ),
        Role.VOYANTE: (
            "You are the Seer. Each night, you can discover "
            "the true role of a player. Use this power wisely "
            "to guide the village to victory."
        ),
        Role.SORCIERE: (
            "You are the Witch. You possess two potions: "
            "one of life to save the werewolves' victim, "
            "one of death to eliminate a suspect. "
            "Each potion can only be used once."
        ),
    }
    return messages.get(role, "Welcome to the game!")


# To run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
