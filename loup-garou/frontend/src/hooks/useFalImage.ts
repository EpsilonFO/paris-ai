import { useState, useEffect } from 'react';
import { fal } from "@fal-ai/client";

// Configuration sécurisée
try {
  fal.config({
    credentials: import.meta.env.VITE_FAL_KEY || '',
  });
} catch {
  console.warn("Fal AI config failed - image generation disabled");
}

export function useFalImage(playerPersonality: string, isHuman: boolean) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isHuman || !playerPersonality) return;

    const generate = async () => {
      if (imageUrl) return;

      setLoading(true);
      try {
        const result: any = await fal.subscribe("fal-ai/flux-pro", {
          input: {
            prompt: `Dark fantasy portrait, oil painting style, mysterious atmosphere, character design. Description: ${playerPersonality}. Detailed face, cinematic lighting, 8k resolution.`,
            image_size: "square_hd",
            num_inference_steps: 25,
            enable_safety_checker: true
          },
          logs: true,
        });

        if (result.data?.images?.[0]?.url) {
          setImageUrl(result.data.images[0].url);
        } else if (result.images?.[0]?.url) {
          setImageUrl(result.images[0].url);
        }
      } catch (error) {
        console.error("Erreur Fal:", error);
      } finally {
        setLoading(false);
      }
    };

    generate();
  }, [playerPersonality, isHuman, imageUrl]);

  return { imageUrl, loading };
}
