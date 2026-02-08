/**
 * Service Text-to-Speech pour jouer l'audio des discussions des IA
 */

const API_BASE_URL = 'http://localhost:8000';

export class TTSService {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private isPlaying = false;

  constructor() {
    // Initialiser l'AudioContext au premier appel pour éviter les problèmes d'autoplay
    this.initAudioContext();
  }

  private initAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }

  /**
   * Joue le texte en utilisant le TTS Gradium
   */
  async playText(text: string, voiceId: string = 'YTpq7expH9539ERJ'): Promise<void> {
    if (!text || !text.trim()) {
      return;
    }

    // Arrêter l'audio en cours si nécessaire
    this.stop();

    try {
      this.initAudioContext();

      // Récupérer le stream audio depuis l'API
      const response = await fetch(
        `${API_BASE_URL}/api/v1/tts/stream?text=${encodeURIComponent(text)}&voice_id=${voiceId}`
      );

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.statusText}`);
      }

      // Lire le stream en tant que ArrayBuffer
      const audioData = await response.arrayBuffer();

      // Convertir PCM int16 en Float32Array pour Web Audio API
      const pcmData = new Int16Array(audioData);
      const float32Data = new Float32Array(pcmData.length);

      for (let i = 0; i < pcmData.length; i++) {
        float32Data[i] = pcmData[i] / 32768.0; // Normaliser de int16 à float32
      }

      // Créer un AudioBuffer
      const audioBuffer = this.audioContext!.createBuffer(
        1, // mono
        float32Data.length,
        48000 // sample rate
      );

      // Copier les données dans le buffer
      audioBuffer.getChannelData(0).set(float32Data);

      // Créer une source et la connecter
      this.currentSource = this.audioContext!.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext!.destination);

      // Marquer comme en lecture
      this.isPlaying = true;

      // Jouer l'audio
      this.currentSource.start();

      // Attendre la fin de la lecture
      return new Promise<void>((resolve) => {
        this.currentSource!.onended = () => {
          this.isPlaying = false;
          this.currentSource = null;
          resolve();
        };
      });

    } catch (error) {
      console.error('Erreur TTS:', error);
      this.isPlaying = false;
      throw error;
    }
  }

  /**
   * Arrête la lecture en cours
   */
  stop() {
    if (this.currentSource && this.isPlaying) {
      try {
        this.currentSource.stop();
      } catch (e) {
        // Ignore les erreurs si déjà arrêté
      }
      this.currentSource = null;
      this.isPlaying = false;
    }
  }

  /**
   * Indique si un audio est en cours de lecture
   */
  getIsPlaying(): boolean {
    return this.isPlaying;
  }
}

// Instance singleton
let ttsServiceInstance: TTSService | null = null;

export function getTTSService(): TTSService {
  if (!ttsServiceInstance) {
    ttsServiceInstance = new TTSService();
  }
  return ttsServiceInstance;
}
