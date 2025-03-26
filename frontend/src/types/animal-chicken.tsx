// Import animation types from CharacterBody
import { CharacterAnimationType } from "./animations";

// Import all face sprites
// Goggles (gogl)
import V01 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAA_v00.png";
import V02 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAA_v01.png";
import V03 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAA_v02.png";
import V04 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAB_v00.png";
import V05 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAB_v01.png";
import V06 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_AAB_v02.png";
import V07 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_ABA_v00.png";
import V08 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_ABA_v01.png";
import V09 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_ABB_v00.png";
import V10 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAA_v00.png";
import V11 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAA_v01.png";
import V12 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAA_v02.png";
import V13 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAA_v03.png";
import V14 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAB_v00.png";
import V15 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAB_v01.png";
import V16 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAB_v02.png";
import V17 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAB_v03.png";
import V18 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BAB_v04.png";
import V19 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBA_v00.png";
import V20 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBB_v00.png";
import V21 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBB_v01.png";
import V22 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBB_v02.png";
import V23 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBB_v03.png";
import V24 from "/src/assets/spritesheets/animals/chicken/livestock_chicken_BBB_v04.png";

// Define face styles
export enum AnimalChickenType {
  NONE = "none",
}

// Group face sprites by style
export const ANIMALS_CHICKEN = {
  [AnimalChickenType.NONE]: [
    V01,
    V02,
    V03,
    V04,
    V05,
    V06,
    V07,
    V08,
    V09,
    V10,
    V11,
    V12,
    V13,
    V14,
    V15,
    V16,
    V17,
    V18,
    V19,
    V20,
    V21,
    V22,
    V23,
    V24,
  ],
};

export interface AnimalChickenConfType {
  type: AnimalChickenType;
  sprite: string;
  spritesheetSize: { columns: number; rows: number };
}

// Function to get a random face or none (with a certain probability)
export const getRandomChicken = (): AnimalChickenConfType => {
  // Get random style type (excluding NONE)
  const styles = [AnimalChickenType.NONE];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants =
    ANIMALS_CHICKEN[randomStyleType as keyof typeof ANIMALS_CHICKEN];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    type: randomStyleType,
    sprite: randomVariant,
    spritesheetSize: { columns: 8, rows: 8 },
  };
};

export interface CharacterAnimalProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  faceStyle?: AnimalChickenType; // Optional specific face style
  zOffset?: number; // Optional Z offset to position the face relative to the character
  chanceOfNoAnimal?: number; // Percentage chance (0-100) that no face accessory will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
