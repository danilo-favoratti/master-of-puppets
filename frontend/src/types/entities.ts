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

// Union type for all entities
export type GameEntity = PotEntity | CampFireEntity | PigEntity | ChestEntity | TentEntity | BedrollEntity | CampfireSpitEntity | CampfirePotEntity;

// Array type for all entities
export type GameEntities = GameEntity[]; 