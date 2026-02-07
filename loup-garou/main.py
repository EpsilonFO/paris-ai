#!/usr/bin/env python3
"""
Point d'entrée pour le serveur Loup-Garou
Compatible avec Alpic - Lance l'API FastAPI avec le frontend
"""
import uvicorn

if __name__ == "__main__":
    # Lance le serveur FastAPI qui sert à la fois l'API et le frontend
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
