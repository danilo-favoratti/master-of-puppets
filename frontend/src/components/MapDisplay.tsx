import alea from "alea";
import React, { useMemo } from "react";
import { createNoise2D } from "simplex-noise";
import { Vector3 } from "three";
import { useGameStore } from "../store/gameStore";
import ForestTile from "./ForestTile";

const MapDisplay: React.FC = () => {
  const { board } = useGameStore();

  const terrainMap = useMemo(() => {
    // Create a seeded random number generator
    const prng = alea("seed"); // You can change 'seed' to any string to get different terrain
    const noise2D = createNoise2D(prng);
    const scale = 0.1;

    const map = Array.from({ length: board.height }).map((_, y) =>
      Array.from({ length: board.width }).map((_, x) => {
        const noiseValue = noise2D(x * scale, y * scale);

        if (noiseValue < -0.4) {
          return { tileX: 2, tileY: 9 }; // water
        } else if (noiseValue < 0.4) {
          return { tileX: 2, tileY: 6 }; // grass
        } else {
          return { tileX: 1, tileY: 1 }; // soil
        }
      })
    );

    return map;
  }, [board.width, board.height]);

  return (
    <group position={new Vector3(0, 0, 0)}>
      {terrainMap.map((row, y) =>
        row.map((tile, x) => (
          <ForestTile
            key={`${x}-${y}`}
            tileX={tile.tileX}
            tileY={tile.tileY}
            size={1}
            gridX={x}
            gridY={y}
          />
        ))
      )}
    </group>
  );
};

export default MapDisplay;
