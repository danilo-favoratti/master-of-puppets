import React from "react";
import * as THREE from "three";
import { Position } from "../types/game";

interface EntityProps {
  id: string;
  type: string;
  name: string;
  position: Position;
  imageUrl: string;
  size?: number;
}

export const Entity: React.FC<EntityProps> = ({
  id,
  type,
  name,
  position,
  imageUrl,
}) => {
  const texture = new THREE.TextureLoader().load(imageUrl);
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;

  const [x, y, z] = [position.x, 0, position.y];

  return (
    <mesh position={[x, y, 0.05]} name={name}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        map={texture}
        transparent={true}
        side={THREE.DoubleSide}
      />
    </mesh>
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
