from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI(
    title="Loup-Garou API",
    description="Backend pour un jeu Loup-Garou avec génération d'images IA",
    version="1.0.0"
)

# État global du jeu
players = ["Moi", "BotA", "BotB", "BotC", "BotD"]

class KillRequest(BaseModel):
    name: str

@app.get("/etat", summary="État du jeu", description="Renvoie la liste des joueurs vivants")
def get_state():
    return {"joueurs_vivants": players, "nombre": len(players)}

@app.post("/tuer", summary="Éliminer un joueur", description="Retire un joueur et génère une image de la scène")
async def kill_player(request: KillRequest):
    if request.name not in players:
        raise HTTPException(status_code=404, detail=f"Joueur '{request.name}' non trouvé")
    
    players.remove(request.name)
    
    # Appel à Fal.ai
    fal_api_key = os.getenv("FAL_KEY")
    if not fal_api_key:
        raise HTTPException(status_code=500, detail="FAL_KEY non configurée")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://fal.run/fal-ai/flux/dev",
            headers={"Authorization": f"Key {fal_api_key}", "Content-Type": "application/json"},
            json={"prompt": f"Cyberpunk crime scene, neon lights, {request.name} eliminated, dark alley, rain, dramatic lighting, cinematic"},
            timeout=60.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur génération image")
        
        image_url = response.json().get("images", [{}])[0].get("url", "")
    
    return {"message": f"{request.name} a été éliminé", "joueurs_restants": players, "image_url": image_url}

@app.post("/reset", summary="Réinitialiser", description="Remet tous les joueurs en vie")
def reset_game():
    global players
    players = ["Moi", "BotA", "BotB", "BotC", "BotD"]
    return {"message": "Partie réinitialisée", "joueurs": players}
