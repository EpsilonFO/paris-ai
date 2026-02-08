import { useState, useEffect, useMemo } from 'react';
import { fal } from "@fal-ai/client";

fal.config({
  credentials: import.meta.env.VITE_FAL_KEY,
});

// 🎭 LA GARDE-ROBE DU JEU
const ROLE_COSPLAYS: Record<string, string> = {
  "Loup-Garou": "wearing a dark tattered wolf pelt cloak, sharp claws visible, glowing red eyes, threatening aura, beastly appearance",
  "Voyante": "wearing mystical purple robes with golden stars, holding a glowing crystal ball, magical aura, mysterious look",
  "Sorcière": "wearing a dark witch hat and ragged dress, holding a bubbling green potion flask, arcane symbols, magical smoke",
  "Chasseur": "wearing tough leather armor, carrying a musket rifle on the back, hunter gear, rugged look",
  "Villageois": "wearing simple medieval peasant tunic, holding a pitchfork, rural style, humble appearance",
  "default": "wearing simple medieval clothes"
};

// Liste des rôles qui déclenchent une mise à jour d'image pour l'IA
const SPECIAL_ROLES = new Set(["Loup-Garou", "Voyante", "Sorcière", "Chasseur"]);

export function useFalImage(playerPersonality: string, isHuman: boolean, role?: string | null) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Clé unique pour régénérer l'image au bon moment
  const generationKey = useMemo(() => {
    if (isHuman) {
      // Pour l'humain, on régénère si son rôle change (ex: début de partie)
      return `HUMAN-${role || 'base'}`;
    } else {
      // Pour l'IA, on régénère si c'est une révélation spéciale ou au début
      const isSpecialReveal = role && SPECIAL_ROLES.has(role);
      return `AI-${playerPersonality}-${isSpecialReveal ? role : 'base'}`;
    }
  }, [playerPersonality, isHuman, role]);

  useEffect(() => {
    const generate = async () => {
      setLoading(true);
      try {
        let prompt = "";
        
        // --- 1. CAS DU JOUEUR HUMAIN (TOI) ---
        if (isHuman) {
          console.log("🎨 Génération HUMAIN (Focus sur le Rôle uniquement)");
          
          // On prend le rôle actuel, ou Villageois par défaut si pas encore défini
          const currentRole = role || "Villageois";
          const outfit = ROLE_COSPLAYS[currentRole] || ROLE_COSPLAYS["default"];

          // PROMPT SIMPLE : Juste le personnage dans son costume
          // On ignore "playerPersonality" (le texte "sdffsd")
          prompt = `
            Subject: A mysterious medieval character portrait, representing a ${currentRole}.
            Attire: ${outfit}.
            Face: Hidden in shadow or mysterious, heroic pose.
            Style: Medieval fantasy oil painting, rpg character portrait, masterpiece.
            Negative prompt: cartoon, anime, text, watermark, blurry.
          `;
        } 
        
        // --- 2. CAS DES IAs (Les autres) ---
        else {
          // On détermine s'il faut révéler le costume ou garder le villageois
          const isSpecialReveal = role && SPECIAL_ROLES.has(role);
          const targetRole = isSpecialReveal ? role : "Villageois";
          const outfit = ROLE_COSPLAYS[targetRole!] || ROLE_COSPLAYS["default"];

          try {
            // On essaie de lire les métadonnées riches (JSON)
            const data = JSON.parse(playerPersonality);
            
            prompt = `
              Subject: A portrait of a ${data.gender}.
              Physical Appearance: ${data.description}. Face traits: ${data.traits}.
              Attire (Cosplay): ${outfit}.
              Style: Medieval fantasy oil painting, rpg character portrait, highly detailed.
              Negative prompt: cartoon, anime, text, watermark.
            `;
          } catch (e) {
            // Fallback si le JSON est cassé (rare)
            prompt = `
              Subject: Medieval character portrait.
              Description: ${playerPersonality}.
              Attire: ${outfit}.
              Style: Medieval fantasy oil painting.
            `;
          }
        }

        // Appel à l'API Fal
        const result: any = await fal.subscribe("fal-ai/flux/dev", {
          input: {
            prompt: prompt,
            image_size: "square_hd",
            num_inference_steps: 25,
            guidance_scale: 3.5,
            enable_safety_checker: true
          },
          logs: true,
        });

        if (result.data?.images?.[0]?.url) setImageUrl(result.data.images[0].url);
        else if (result.images?.[0]?.url) setImageUrl(result.images[0].url);
        
      } catch (error) {
        console.error("❌ Erreur Fal:", error);
      } finally {
        setLoading(false);
      }
    };

    generate();

  }, [generationKey]); // Se déclenche quand la clé change

  return { imageUrl, loading };
}