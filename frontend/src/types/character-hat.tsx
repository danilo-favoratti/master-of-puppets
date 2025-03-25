// Import animation types from CharacterBody
import {CharacterAnimationType} from "../../types/animations";

// Import all hat sprites
// Headband (band)
import bandV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_band_v01.png";
import bandV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_band_v02.png";
import bandV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_band_v03.png";
import bandV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_band_v04.png";
import bandV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_band_v05.png";

// Hood (hddn)
import hddnV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v01.png";
import hddnV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v02.png";
import hddnV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v03.png";
import hddnV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v04.png";
import hddnV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v05.png";
import hddnV06 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v06.png";
import hddnV07 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v07.png";
import hddnV08 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v08.png";
import hddnV09 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v09.png";
import hddnV10 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hddn_v10.png";

// Helmet (hdpl)
import hdplV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v01.png";
import hdplV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v02.png";
import hdplV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v03.png";
import hdplV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v04.png";
import hdplV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v05.png";
import hdplV06 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v06.png";
import hdplV07 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v07.png";
import hdplV08 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v08.png";
import hdplV09 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v09.png";
import hdplV10 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v10.png";

// Pointy hat (pnty)
import pntyV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pnty_v01.png";
import pntyV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pnty_v02.png";
import pntyV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pnty_v03.png";
import pntyV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pnty_v04.png";
import pntyV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pnty_v05.png";

// Round hat (rnht)
import rnhtV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_rnht_v01.png";
import rnhtV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_rnht_v02.png";
import rnhtV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_rnht_v03.png";
import rnhtV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_rnht_v04.png";
import rnhtV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_rnht_v05.png";

// Puff ball hat (pfbn)
import pfbnV01 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v01.png";
import pfbnV02 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v02.png";
import pfbnV03 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v03.png";
import pfbnV04 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v04.png";
import pfbnV05 from "/src/assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v05.png";

// Define hat styles
export enum HatStyle {
  HEADBAND = "headband",
  HOOD = "hood",
  HELMET = "helmet",
  POINTY = "pointy",
  ROUND = "round",
  PUFFBALL = "puffball",
  NONE = "none", // Added for possibility of no hat
}

// Group hat sprites by style
export const HATS = {
  [HatStyle.HEADBAND]: [bandV01, bandV02, bandV03, bandV04, bandV05],
  [HatStyle.HOOD]: [
    hddnV01,
    hddnV02,
    hddnV03,
    hddnV04,
    hddnV05,
    hddnV06,
    hddnV07,
    hddnV08,
    hddnV09,
    hddnV10,
  ],
  [HatStyle.HELMET]: [
    hdplV01,
    hdplV02,
    hdplV03,
    hdplV04,
    hdplV05,
    hdplV06,
    hdplV07,
    hdplV08,
    hdplV09,
    hdplV10,
  ],
  [HatStyle.POINTY]: [pntyV01, pntyV02, pntyV03, pntyV04, pntyV05],
  [HatStyle.ROUND]: [rnhtV01, rnhtV02, rnhtV03, rnhtV04, rnhtV05],
  [HatStyle.PUFFBALL]: [pfbnV01, pfbnV02, pfbnV03, pfbnV04, pfbnV05],
};

// Function to get a random hat or none (with a certain probability)
export const getRandomHat = (chanceOfNoHat: number = 25) => {
  // First, determine if we should have no hat (default 25% chance)
  if (Math.random() * 100 < chanceOfNoHat) {
    return {
      style: HatStyle.NONE,
      sprite: null,
    };
  }

  // Get random style type (excluding NONE)
  const styles = [
    HatStyle.HEADBAND,
    HatStyle.HOOD,
    HatStyle.HELMET,
    HatStyle.POINTY,
    HatStyle.ROUND,
    HatStyle.PUFFBALL,
  ];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = HATS[randomStyleType as keyof typeof HATS];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

export interface CharacterHatProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  hatStyle?: HatStyle; // Optional specific hat style
  zOffset?: number; // Optional Z offset to position the hat relative to the character
  chanceOfNoHat?: number; // Percentage chance (0-100) that no hat will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
