#!/usr/bin/env python3
"""
Point d'entrée pour le serveur MCP Loup-Garou
Compatible avec Alpic
"""
import asyncio
from src.mcp_server import main

if __name__ == "__main__":
    asyncio.run(main())
