import React from "react";
import * as THREE from "three";
import {Position} from "../types/game";
import { getX, getY, getZ } from "../utils/positionUtils";

interface EntityProps {
  id: string;
  type: string;
  name: string;
  position: Position;
  imageUrl: string;
  size?: number;
  isSpritesheet?: boolean;
  spritePosition?: { x: number; y: number };
  spriteSize?: { width: number; height: number };
  spritesheetSize?: { columns: number; rows: number };
}

export const Entity: React.FC<EntityProps> = ({
  name,
  position,
  imageUrl,
  isSpritesheet = false,
  spritePosition = { x: 0, y: 0 },
  spritesheetSize = { columns: 1, rows: 1 },
}) => {
  const texture = new THREE.TextureLoader().load(imageUrl);
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;

  if (isSpritesheet) {
    const { columns, rows } = spritesheetSize;
    const { x, y } = spritePosition;

    // Configure texture to show only the specific sprite
    texture.repeat.set(1 / columns, 1 / rows);
    texture.offset.set(x / columns, 1 - (y + 1) / rows);
    return (
      <mesh position={[getX(position), 0, getY(position)]} name={name}>
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial
          map={texture}
          transparent={true}
          side={THREE.DoubleSide}
        />
      </mesh>
    );
  }

  return (
    <mesh position={[getX(position), getY(position), 0.05]} name={name}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        map={texture}
        transparent={true}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

// Example usage with spritesheet
export const SpritesheetEntity: React.FC<{
  position: Position;
  spritePosition: { x: number; y: number };
}> = ({ position, spritePosition }) => {
  return (
    <Entity
      id="sprite-1"
      type="character"
      name="Spritesheet Character"
      position={position}
      imageUrl="/src/assets/character_spritesheet.png"
      isSpritesheet={true}
      spritePosition={spritePosition}
      spritesheetSize={{ columns: 4, rows: 4 }} // Example spritesheet configuration
    />
  );
};

// Specific component for the travelers camp tent
export const TravelersCampTent: React.FC<{ position: Position }> = ({
  position,
}) => {
  return (
    <Entity
      id="tent-1"
      type="structure"
      name="Travelers Camp Tent"
      position={position}
      imageUrl="/src/assets/travelers_camp_tent.png"
      size={2}
    />
  );
};

export default Entity;
