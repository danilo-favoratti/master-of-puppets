// Import animation types from CharacterBody
import { CharacterAnimationType } from "./animations";

// Import all face sprites
// Goggles (gogl)
import goglV01 from "/src/assets/spritesheets/3fac/char_a_p1_3fac_gogl_v01.png";
import goglV02 from "/src/assets/spritesheets/3fac/char_a_p1_3fac_gogl_v02.png";
import goglV03 from "/src/assets/spritesheets/3fac/char_a_p1_3fac_gogl_v03.png";
import goglV04 from "/src/assets/spritesheets/3fac/char_a_p1_3fac_gogl_v04.png";
import goglV05 from "/src/assets/spritesheets/3fac/char_a_p1_3fac_gogl_v05.png";

// Define face styles
export enum FaceStyle {
  GOGGLES = "goggles",
  NONE = "none", // Added for possibility of no face accessory
}

// Group face sprites by style
export const FACES = {
  [FaceStyle.GOGGLES]: [goglV01, goglV02, goglV03, goglV04, goglV05],
};

// Function to get a random face or none (with a certain probability)
export const getRandomFace = (chanceOfNoFace: number = 40) => {
  // First, determine if we should have no face accessory (default 40% chance)
  if (Math.random() * 100 < chanceOfNoFace) {
    return {
      style: FaceStyle.NONE,
      sprite: null,
    };
  }

  // Get random style type (excluding NONE)
  const styles = [FaceStyle.GOGGLES];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = FACES[randomStyleType as keyof typeof FACES];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

export interface CharacterFaceProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  faceStyle?: FaceStyle; // Optional specific face style
  zOffset?: number; // Optional Z offset to position the face relative to the character
  chanceOfNoFace?: number; // Percentage chance (0-100) that no face accessory will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
