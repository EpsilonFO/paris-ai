"""
Service Text-to-Speech utilisant Gradium pour le jeu du Loup-Garou
"""
import asyncio
import gradium
import numpy as np
from typing import AsyncGenerator
import os


class TTSService:
    """Service de synthèse vocale avec Gradium"""

    def __init__(self):
        self.client: gradium.client.GradiumClient | None = None
        self.sample_rate = 48000
        self.chunk_size = 3840  # 80ms @ 48kHz

    def _get_client(self) -> gradium.client.GradiumClient:
        """Récupère ou crée le client Gradium"""
        if self.client is None:
            api_key = os.environ.get("GRADIUM_API_KEY", "gsk_0a60782669fba9008ab402d2431efb1df05140e62395520cfd6f5a81b9e01ae3")
            self.client = gradium.client.GradiumClient(api_key=api_key)
        return self.client

    def set_api_key(self, api_key: str):
        """Configure la clé API Gradium"""
        self.client = gradium.client.GradiumClient(api_key=api_key)

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: str = "YTpq7expH9539ERJ"
    ) -> AsyncGenerator[bytes, None]:
        """
        Génère un stream audio à partir du texte

        Args:
            text: Le texte à synthétiser
            voice_id: L'ID de la voix Gradium à utiliser

        Yields:
            chunks audio en format PCM int16
        """
        client = self._get_client()

        try:
            stream = await client.tts_stream(
                setup={
                    "model_name": "default",
                    "voice_id": voice_id,
                    "output_format": "pcm"
                },
                text=text
            )

            async for chunk in stream.iter_bytes():
                yield chunk

        except Exception as e:
            print(f"Erreur TTS: {e}")
            raise

    async def text_to_speech_bytes(
        self,
        text: str,
        voice_id: str = "YTpq7expH9539ERJ"
    ) -> bytes:
        """
        Génère l'audio complet à partir du texte

        Args:
            text: Le texte à synthétiser
            voice_id: L'ID de la voix Gradium à utiliser

        Returns:
            bytes audio en format PCM int16
        """
        chunks = []
        async for chunk in self.text_to_speech_stream(text, voice_id):
            chunks.append(chunk)
        return b''.join(chunks)


# Instance globale du service TTS
_tts_service: TTSService | None = None


def get_tts_service() -> TTSService:
    """Récupère ou crée le service TTS"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


def set_gradium_api_key(api_key: str):
    """Configure la clé API Gradium"""
    service = get_tts_service()
    service.set_api_key(api_key)
