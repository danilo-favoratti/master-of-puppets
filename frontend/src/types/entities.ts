import { Position } from "./game";

// Base interface for all entities
export interface BaseEntity {
  id: string;
  type: string;
  name: string;
  position: Position;
  state?: string;
  variant?: string;
}

// Pot entity interface
export interface PotEntity extends BaseEntity {
  type: "pot";
  state: "unlit" | "breaking" | "broken" | "broke";
}

// Campfire entity interface
export interface CampFireEntity extends BaseEntity {
  type: "campfire";
  state: "unlit" | "burning" | "dying" | "extinguished";
}

// Pig entity interface
export interface PigEntity extends BaseEntity {
  type: "pig";
  state: "idleUp" | "idleDown" | "idleLeft" | "idleRight" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
  canMove?: boolean;
  moveInterval?: number;
}

// Chest entity interface
export interface ChestEntity extends BaseEntity {
  type: "chest";
  state: "idle" | "breaking" | "broken";
}

// Tent entity interface
export interface TentEntity extends BaseEntity {
  type: "tent";
  state: "idle";
}

// Bedroll entity interface
export interface BedrollEntity extends BaseEntity {
  type: "bedroll";
  state: "idle";
}

// Campfire spit entity interface
export interface CampfireSpitEntity extends BaseEntity {
  type: "campfire_spit";
  state: "idle";
}

// Campfire pot entity interface
export interface CampfirePotEntity extends BaseEntity {
  type: "campfire_pot";
  state: "empty" | "cooking" | "idle";
}

// Thief entity interface
export interface ThiefEntity extends BaseEntity {
  type: "thief";
  state: "idle" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
}

// Guard entity interface
export interface GuardEntity extends BaseEntity {
  type: "guard";
  state: "idle" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
}

// Merchant entity interface
export interface MerchantEntity extends BaseEntity {
  type: "merchant";
  state: "idle" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
}

// Hero entity interface
export interface HeroEntity extends BaseEntity {
  type: "hero";
  state: "idle" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
}

// Wizard entity interface
export interface WizardEntity extends BaseEntity {
  type: "wizard";
  state: "idle" | "walkLeft" | "walkRight" | "walkUp" | "walkDown";
}

// Statue entity interface
export interface StatueEntity extends BaseEntity {
  type: "statue";
  state: "idle";
}

// Union type for all entities
export type GameEntity = PotEntity | CampFireEntity | PigEntity | ChestEntity | TentEntity | BedrollEntity | CampfireSpitEntity | CampfirePotEntity | ThiefEntity | GuardEntity | MerchantEntity | HeroEntity | WizardEntity | StatueEntity;

// Array type for all entities
export type GameEntities = GameEntity[]; 