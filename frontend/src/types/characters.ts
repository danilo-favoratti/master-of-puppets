// Import the sprite sheets
import char_demn_v01 from "../assets/spritesheets/characters/char_a_p1_0bas_demn_v01.png";
import char_demn_v02 from "../assets/spritesheets/characters/char_a_p1_0bas_demn_v02.png";
import char_gbln_v01 from "../assets/spritesheets/characters/char_a_p1_0bas_gbln_v01.png";
import char_humn_v00 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v00.png";
import char_humn_v01 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v01.png";
import char_humn_v02 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v02.png";
import char_humn_v03 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v03.png";
import char_humn_v04 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v04.png";
import char_humn_v05 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v05.png";
import char_humn_v06 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v06.png";
import char_humn_v07 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v07.png";
import char_humn_v08 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v08.png";
import char_humn_v09 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v09.png";
import char_humn_v10 from "../assets/spritesheets/characters/char_a_p1_0bas_humn_v10.png";

// Define character types
export enum CharacterType {
  HUMAN = "human",
  GOBLIN = "goblin",
  DEMON = "demon",
}

// Group character sprites by type
export const CHARACTERS = {
  [CharacterType.HUMAN]: [
    char_humn_v00,
    char_humn_v01,
    char_humn_v02,
    char_humn_v03,
    char_humn_v04,
    char_humn_v05,
    char_humn_v06,
    char_humn_v07,
    char_humn_v08,
    char_humn_v09,
    char_humn_v10,
  ],
  [CharacterType.GOBLIN]: [char_gbln_v01],
  [CharacterType.DEMON]: [char_demn_v01, char_demn_v02],
} as const;

// Function to get a random character sprite
export const getRandomCharacter = () => {
  // Get random character type
  const types = Object.values(CharacterType);
  const randomType = types[Math.floor(Math.random() * types.length)];

  // Get random variant from that type
  const variants = CHARACTERS[randomType];
  const randomVariant = variants[Math.floor(Math.random() * variants.length)];

  return {
    type: randomType,
    sprite: randomVariant,
  };
}; 