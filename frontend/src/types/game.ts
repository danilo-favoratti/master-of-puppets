import {GameEntity} from "./entities";

// Use type alias for array format
export type Position = [number, number] | [number, number, number]; // Allow optional z

export interface Square {
  position: Position;
  contains_entity: boolean;
}

export interface Entity {
  id: string;
  type: string;
  name: string;
  position: Position | null;
  strength: number;
  inventory: string[];
  can_perform: string[];
  description: string;
}

export interface Board {
  width: number;
  height: number;
  squares: Square[];
}

export type GameObjectType = 'pig' | 'campfire' | 'tree' | 'rock' | 'chest' | 'npc';

export type GameObjectState = 'unlit' | 'burning' | 'dying' | 'extinguished' | 'idle' | 'walking' | 'running';

export interface GameObject {
  id: string;
  type: GameObjectType;
  variant: string;
  position: Position;
  state: GameObjectState;
  entity: Entity;
  onClick?: (event: React.MouseEvent) => void;
  onStateChange?: (newState: GameObjectState) => void;
}

export interface GameObjectConfig {
  id: string;
  type: GameObjectType;
  name: string;
  imageUrl: string;
  spritesheetSize: {
    columns: number;
    rows: number;
  };
  animationConfig: Record<GameObjectState, {
    frame?: { x: number; y: number };
    frames?: Array<{ x: number; y: number }>;
    frameDuration: number;
  }>;
  defaultState: GameObjectState;
  size?: number;
}

export interface GameData {
  map: {
    width: number;
    height: number;
    grid: number[][];
  };
  entities: GameEntity[];
} 