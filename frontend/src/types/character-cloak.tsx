// Import animation types from CharacterBody
import {CharacterAnimationType} from "./animations";

// Import all cloak sprites
// Long cloaks (lnpl)
import lnplV01 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v01.png";
import lnplV02 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v02.png";
import lnplV03 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v03.png";
import lnplV04 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v04.png";
import lnplV05 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v05.png";
import lnplV06 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v06.png";
import lnplV07 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v07.png";
import lnplV08 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v08.png";
import lnplV09 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v09.png";
import lnplV10 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v10.png";

// Medium cloaks (mnpl)
import mnplV01 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v01.png";
import mnplV02 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v02.png";
import mnplV03 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v03.png";
import mnplV04 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v04.png";
import mnplV05 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v05.png";
import mnplV06 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v06.png";
import mnplV07 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v07.png";
import mnplV08 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v08.png";
import mnplV09 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v09.png";
import mnplV10 from "/src/assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v10.png";

// Define cloak styles
export enum CloakStyle {
  LONG = "long",
  MEDIUM = "medium",
  NONE = "none", // Added for possibility of no cloak
}

// Group cloak sprites by style
export const CLOAKS = {
  [CloakStyle.LONG]: [
    lnplV01,
    lnplV02,
    lnplV03,
    lnplV04,
    lnplV05,
    lnplV06,
    lnplV07,
    lnplV08,
    lnplV09,
    lnplV10,
  ],
  [CloakStyle.MEDIUM]: [
    mnplV01,
    mnplV02,
    mnplV03,
    mnplV04,
    mnplV05,
    mnplV06,
    mnplV07,
    mnplV08,
    mnplV09,
    mnplV10,
  ],
};

// Function to get a random cloak or none (with a certain probability)
export const getRandomCloak = (chanceOfNoCloak: number = 30) => {
  // First, determine if we should have no cloak (default 30% chance)
  if (Math.random() * 100 < chanceOfNoCloak) {
    return {
      style: CloakStyle.NONE,
      sprite: null,
    };
  }

  // Get random style type (excluding NONE)
  const styles = [CloakStyle.LONG, CloakStyle.MEDIUM];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = CLOAKS[randomStyleType as keyof typeof CLOAKS];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

export interface CharacterCloakProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  cloakStyle?: CloakStyle; // Optional specific cloak style
  zOffset?: number; // Optional Z offset to position the cloak relative to the character
  chanceOfNoCloak?: number; // Percentage chance (0-100) that no cloak will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
