// Import all outfit sprites
// Different outfit types
// Alchemist outfit variants
import alchV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v01.png";
import alchV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v02.png";
import alchV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v03.png";
import alchV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v04.png";
import alchV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v05.png";

// Angler outfit variants
import anglV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v01.png";
import anglV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v02.png";
import anglV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v03.png";
import anglV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v04.png";
import anglV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v05.png";

// Blacksmith outfit variants
import bksmV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v01.png";
import bksmV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v02.png";
import bksmV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v03.png";
import bksmV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v04.png";
import bksmV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v05.png";

// Forester outfit variants
import fstrV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v01.png";
import fstrV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v02.png";
import fstrV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v03.png";
import fstrV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v04.png";
import fstrV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v05.png";

// Pathfinder outfit variants
import pfdrV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v01.png";
import pfdrV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v02.png";
import pfdrV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v03.png";
import pfdrV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v04.png";
import pfdrV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v05.png";

// Import animation types from CharacterBody
import {CharacterAnimationType} from "../../types/animations";

// Define outfit types
export enum OutfitStyle {
  ALCHEMIST = "alchemist",
  ANGLER = "angler",
  BLACKSMITH = "blacksmith",
  FORESTER = "forester",
  PATHFINDER = "pathfinder",
}

// Group outfit sprites by style
export const OUTFITS = {
  [OutfitStyle.ALCHEMIST]: [alchV01, alchV02, alchV03, alchV04, alchV05],
  [OutfitStyle.ANGLER]: [anglV01, anglV02, anglV03, anglV04, anglV05],
  [OutfitStyle.BLACKSMITH]: [bksmV01, bksmV02, bksmV03, bksmV04, bksmV05],
  [OutfitStyle.FORESTER]: [fstrV01, fstrV02, fstrV03, fstrV04, fstrV05],
  [OutfitStyle.PATHFINDER]: [pfdrV01, pfdrV02, pfdrV03, pfdrV04, pfdrV05],
};

// Function to get a random outfit
export const getRandomOutfit = () => {
  // Get random style type
  const styles = Object.values(OutfitStyle);
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = OUTFITS[randomStyleType];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

export interface CharacterOutfitProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  outfitStyle?: OutfitStyle; // Optional specific outfit style
  zOffset?: number; // Optional Z offset to position the outfit relative to the character
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
