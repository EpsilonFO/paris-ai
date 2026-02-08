"""
Text-to-Speech service using Gradium for the Werewolf game
"""
import asyncio
import gradium
import numpy as np
from typing import AsyncGenerator
import os


class TTSService:
    """Text-to-speech service with Gradium"""

    def __init__(self):
        self.client = None
        self.sample_rate = 48000
        self.chunk_size = 3840  # 80ms @ 48kHz

    def _get_client(self):
        """Get or create Gradium client"""
        if not gradium:
            raise RuntimeError("Gradium is not installed")
        if self.client is None:
            api_key = os.environ.get("GRADIUM_API_KEY", "gsk_1de33236e6c36ec2379faf64378a9067931f304a598028a32157558a11439d36")
            self.client = gradium.client.GradiumClient(api_key=api_key)
        return self.client

    def set_api_key(self, api_key: str):
        """Configure Gradium API key"""
        self.client = gradium.client.GradiumClient(api_key=api_key)

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: str = "YTpq7expH9539ERJ"
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate audio stream from text

        Args:
            text: Text to synthesize
            voice_id: Gradium voice ID to use

        Yields:
            audio chunks in PCM int16 format
        """
        client = self._get_client()
        print(f"[TTS] START - Generating audio for text: {text[:100]}..." if len(text) > 100 else f"[TTS] START - Generating audio for text: {text}")

        try:
            stream = await client.tts_stream(
                setup={
                    "model_name": "default",
                    "voice_id": voice_id,
                    "output_format": "pcm",
                    'json_config':{'padding_bonus':-3}
                },
                text=text
            )

            chunk_count = 0
            async for chunk in stream.iter_bytes():
                chunk_count += 1
                yield chunk

            print(f"[TTS] END - Audio generated successfully ({chunk_count} chunks, {len(text)} characters)")

        except Exception as e:
            print(f"[TTS] ERROR - TTS error: {e}")
            raise

    async def text_to_speech_bytes(
        self,
        text: str,
        voice_id: str = "YTpq7expH9539ERJ"
    ) -> bytes:
        """
        Generate complete audio from text

        Args:
            text: Text to synthesize
            voice_id: Gradium voice ID to use

        Returns:
            audio bytes in PCM int16 format
        """
        print(f"[TTS_BYTES] Collecting complete audio...")
        chunks = []
        async for chunk in self.text_to_speech_stream(text, voice_id):
            chunks.append(chunk)
        audio_bytes = b''.join(chunks)
        print(f"[TTS_BYTES] Audio ready to play: {len(audio_bytes)} bytes")
        return audio_bytes


# Global TTS service instance
_tts_service: TTSService | None = None


def get_tts_service():
    """Get or create TTS service (returns None if gradium is not installed)"""
    if not gradium:
        return None
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


def set_gradium_api_key(api_key: str):
    """Configure Gradium API key"""
    if not gradium:
        raise RuntimeError("Gradium is not installed")
    service = get_tts_service()
    if service:
        service.set_api_key(api_key)