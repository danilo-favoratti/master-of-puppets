// Import animation types from CharacterBody
import {CharacterAnimationType} from "./animations";
// Import all hair sprites
// Main hairstyle variants
import bob2 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v00.png";
import flat from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v00.png";
import fro1 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v00.png";
import pon1 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v00.png";
import spk2 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v00.png";

// Color variants for each style (we'll pick one randomly)
// Flat style color variants
import flatV01 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v01.png";
import flatV02 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v02.png";
import flatV03 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v03.png";
import flatV04 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v04.png";
import flatV05 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v05.png";
import flatV06 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v06.png";
import flatV07 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v07.png";
import flatV08 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v08.png";
import flatV09 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v09.png";
import flatV10 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v10.png";
import flatV11 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v11.png";
import flatV12 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v12.png";
import flatV13 from "/src/assets/spritesheets/4har/char_a_p1_4har_flat_v13.png";

// Bob style color variants
import bobV01 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v01.png";
import bobV02 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v02.png";
import bobV03 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v03.png";
import bobV04 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v04.png";
import bobV05 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v05.png";
import bobV06 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v06.png";
import bobV07 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v07.png";
import bobV08 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v08.png";
import bobV09 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v09.png";
import bobV10 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v10.png";
import bobV11 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v11.png";
import bobV12 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v12.png";
import bobV13 from "/src/assets/spritesheets/4har/char_a_p1_4har_bob2_v13.png";

// Fro style color variants
import froV01 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v01.png";
import froV02 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v02.png";
import froV03 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v03.png";
import froV04 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v04.png";
import froV05 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v05.png";
import froV06 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v06.png";
import froV07 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v07.png";
import froV08 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v08.png";
import froV09 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v09.png";
import froV10 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v10.png";
import froV11 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v11.png";
import froV12 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v12.png";
import froV13 from "/src/assets/spritesheets/4har/char_a_p1_4har_fro1_v13.png";

// Ponytail style color variants
import ponV01 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v01.png";
import ponV02 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v02.png";
import ponV03 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v03.png";
import ponV04 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v04.png";
import ponV05 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v05.png";
import ponV06 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v06.png";
import ponV07 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v07.png";
import ponV08 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v08.png";
import ponV09 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v09.png";
import ponV10 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v10.png";
import ponV11a from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v11a.png";
import ponV11b from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v11b.png";
import ponV12 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v12.png";
import ponV13 from "/src/assets/spritesheets/4har/char_a_p1_4har_pon1_v13.png";

// Spiky style color variants
import spkV01 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v01.png";
import spkV02 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v02.png";
import spkV03 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v03.png";
import spkV04 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v04.png";
import spkV05 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v05.png";
import spkV06 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v06.png";
import spkV07 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v07.png";
import spkV08 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v08.png";
import spkV09 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v09.png";
import spkV10 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v10.png";
import spkV11 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v11.png";
import spkV12 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v12.png";
import spkV13 from "/src/assets/spritesheets/4har/char_a_p1_4har_spk2_v13.png";

// Define hairstyle types
export enum HairStyle {
  FLAT = "flat",
  BOB = "bob",
  FRO = "fro",
  PONYTAIL = "ponytail",
  SPIKY = "spiky",
}

// Group hair sprites by style
export const HAIRSTYLES = {
  [HairStyle.FLAT]: [
    flat,
    flatV01,
    flatV02,
    flatV03,
    flatV04,
    flatV05,
    flatV06,
    flatV07,
    flatV08,
    flatV09,
    flatV10,
    flatV11,
    flatV12,
    flatV13,
  ],
  [HairStyle.BOB]: [
    bob2,
    bobV01,
    bobV02,
    bobV03,
    bobV04,
    bobV05,
    bobV06,
    bobV07,
    bobV08,
    bobV09,
    bobV10,
    bobV11,
    bobV12,
    bobV13,
  ],
  [HairStyle.FRO]: [
    fro1,
    froV01,
    froV02,
    froV03,
    froV04,
    froV05,
    froV06,
    froV07,
    froV08,
    froV09,
    froV10,
    froV11,
    froV12,
    froV13,
  ],
  [HairStyle.PONYTAIL]: [
    pon1,
    ponV01,
    ponV02,
    ponV03,
    ponV04,
    ponV05,
    ponV06,
    ponV07,
    ponV08,
    ponV09,
    ponV10,
    ponV11a,
    ponV11b,
    ponV12,
    ponV13,
  ],
  [HairStyle.SPIKY]: [
    spk2,
    spkV01,
    spkV02,
    spkV03,
    spkV04,
    spkV05,
    spkV06,
    spkV07,
    spkV08,
    spkV09,
    spkV10,
    spkV11,
    spkV12,
    spkV13,
  ],
};

// Function to get a random hairstyle
export const getRandomHairstyle = () => {
  // Get random style type
  const styles = Object.values(HairStyle);
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = HAIRSTYLES[randomStyleType];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

export interface CharacterHairProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  hairStyle?: HairStyle; // Optional specific hairstyle
  zOffset?: number; // Optional Z offset to position the hair slightly in front of the character
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
