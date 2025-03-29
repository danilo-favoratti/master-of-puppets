import alea from "alea";
import React, {useMemo} from "react";
import {createNoise2D} from "simplex-noise";
import {Vector3} from "three";
import ForestTile from "./ForestTile";

interface MapDisplayProps {
  mapGridData: number[][];
  width: number;
  height: number;
}

const MapDisplay: React.FC<MapDisplayProps> = ({ mapGridData, width, height }) => {
  const terrainMap = useMemo(() => {
    // Create a seeded random number generator
    const prng = alea("seed"); // You can change 'seed' to any string to get different terrain
    const noise2D = createNoise2D(prng);
    const scale = 0.1;

    const map = Array.from({ length: height }).map((_, y) =>
      Array.from({ length: width }).map((_, x) => {
        if (x >= mapGridData.length || y >= mapGridData[x]?.length) {
            console.error(`MapDisplay: Out of bounds access at x=${x}, y=${y}. Grid dimensions: ${mapGridData.length}x${mapGridData[0]?.length}, Requested dimensions: ${width}x${height}`);
            return { tileX: 0, tileY: 0 }; // Default/error tile
        }

        const noiseValue = noise2D(x * scale, y * scale);

        if (mapGridData[x][y] === 1) {
          const randomGrass = Math.floor(Math.random() * 4);
          if (randomGrass === 0) return { tileX: 1, tileY: 6 };
          if (randomGrass === 1) return { tileX: 1, tileY: 5 };
          if (randomGrass === 2) return { tileX: 2, tileY: 6 };
          if (randomGrass === 3) return { tileX: 2, tileY: 5 };
        } else {
          return { tileX: 1, tileY: 9 }; // soil
        }
      })
    );

    return map;
  }, [mapGridData, width, height]);

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
