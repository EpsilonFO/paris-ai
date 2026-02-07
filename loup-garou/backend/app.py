#!/usr/bin/env python3
"""
Lance le serveur API FastAPI pour le frontend du Loup-Garou
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
