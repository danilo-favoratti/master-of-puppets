export interface Position {
  x: number;
  y: number;
}

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