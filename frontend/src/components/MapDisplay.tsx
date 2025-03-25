import alea from "alea";
import React, {useMemo} from "react";
import {createNoise2D} from "simplex-noise";
import {Vector3} from "three";
import {useGameStore} from "../store/gameStore";
import ForestTile from "./ForestTile";

const MapDisplay: React.FC<{ mapGridData: number[][] }> = ({ mapGridData }) => {
  const { board } = useGameStore();

  const terrainMap = useMemo(() => {
    // Create a seeded random number generator
    const prng = alea("seed"); // You can change 'seed' to any string to get different terrain
    const noise2D = createNoise2D(prng);
    const scale = 0.1;

    const map = Array.from({ length: mapGridData.length }).map((_, y) =>
      Array.from({ length: mapGridData.length }).map((_, x) => {
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
