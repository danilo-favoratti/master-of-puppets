import React, { useMemo } from "react";
import { Vector3 } from "three";
import { Entity, Position } from "../types/game";
import { GameEntity } from "../types/entities";
import ForestTile from "./ForestTile";

interface MapDisplayProps {
  mapGridData: number[][];
  width: number;
  height: number;
  entities: GameEntity[];
}

const MapDisplay: React.FC<MapDisplayProps> = ({
  mapGridData,
  width,
  height,
  entities,
}) => {
  const arraysEqual = (a, b) => {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  };

  const terrainMap = useMemo(() => {
    const map = Array.from({ length: height }).map((_, y) =>
      Array.from({ length: width }).map((_, x) => {
        if (x >= mapGridData.length || y >= mapGridData[x]?.length) {
          console.error(
            `MapDisplay: Out of bounds access at x=${x}, y=${y}. Grid dimensions: ${mapGridData.length}x${mapGridData[0]?.length}, Requested dimensions: ${width}x${height}`
          );
          return { tileX: 0, tileY: 0 }; // Default/error tile
        }

        // const noiseValue = noise2D(x * scale, y * scale);

        // Water
        if (mapGridData[x][y] === 0) {
          // Check surrounding tiles
          const neighbors = [
            { dx: 0, dy: -1 }, // above
            { dx: -1, dy: 0 }, // left
            { dx: 1, dy: 0 }, // right
            { dx: 0, dy: 1 }, // below
          ];

          const neighborValues = neighbors.map(({ dx, dy }) => {
            const nx = x + dx;
            const ny = y + dy;
            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
              return mapGridData[nx][ny];
            }
            return null; // Out of bounds
          });

          if (arraysEqual(neighborValues, [0, 1, 0, 0]))
            return { tileX: 0, tileY: 10, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [1, 0, 0, 0]))
            return { tileX: 1, tileY: 11, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [0, 0, 1, 0]))
            return { tileX: 3, tileY: 10, neighborValues: neighborValues };
          if (arraysEqual(neighborValues, [0, 0, 0, 1]))
            return { tileX: 1, tileY: 8, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [1, 1, 0, 0]))
            return { tileX: 0, tileY: 11, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [1, 1, 0, 1]))
            return { tileX: 0, tileY: 10, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [1, 0, 1, 0]))
            return { tileX: 3, tileY: 11, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [0, 1, 0, 1]))
            return { tileX: 0, tileY: 8, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [0, 0, 1, 1]))
            return { tileX: 3, tileY: 8, neighborValues: neighborValues };

          if (arraysEqual(neighborValues, [1, 0, 1, 1]))
            return { tileX: 3, tileY: 10, neighborValues: neighborValues };

          // Default to water tile if no specific rule matches
          return { tileX: 1, tileY: 9, neighborValues: neighborValues };
        }

        const entity = entities.find(
          (entity) => entity.position?.[0] === x && entity.position?.[1] === y
        );
        const isEmpty = entity === undefined;

        if (isEmpty && Math.random() < 0.05) {
          const randomTileX = Math.floor(Math.random() * 3);
          const randomTileY = Math.floor(Math.random() * 2);
          return { tileX: randomTileX + 8, tileY: randomTileY + 5 };
        }

        const randomGrass = Math.floor(Math.random() * 4);
        if (randomGrass === 0) return { tileX: 1, tileY: 6 };
        if (randomGrass === 1) return { tileX: 1, tileY: 5 };
        if (randomGrass === 2) return { tileX: 2, tileY: 6 };
        if (randomGrass === 3) return { tileX: 2, tileY: 5 };
        return { tileX: 1, tileY: 9 };
      })
    );

    return map;
  }, [mapGridData, width, height]);

  return (
    <group position={new Vector3(0, 0, 0)}>
      {terrainMap.map((row, y) =>
        row.map((tile, x) => {
          return (
            <ForestTile
              key={`${x}-${y}`}
              tileX={tile.tileX}
              tileY={tile.tileY}
              size={1}
              gridX={x}
              gridY={y}
            />
          );
        })
      )}
    </group>
  );
};

export default MapDisplay;
