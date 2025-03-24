import { GameObjectConfig } from '../types/game';

export const gameObjectConfigs: Record<string, GameObjectConfig> = {
  pig: {
    id: 'pig-1',
    type: 'pig',
    name: 'Pig',
    imageUrl: '/src/assets/spritesheets/animals/livestock_pig_A_v01.png',
    spritesheetSize: { columns: 5, rows: 3 },
    animationConfig: {
      idle: {
        frame: { x: 0, y: 0 },
        frameDuration: 200,
      },
      walking: {
        frames: [
          { x: 1, y: 0 },
          { x: 2, y: 0 },
          { x: 3, y: 0 },
          { x: 4, y: 0 },
        ],
        frameDuration: 200,
      },
      running: {
        frames: [
          { x: 1, y: 1 },
          { x: 2, y: 1 },
          { x: 3, y: 1 },
          { x: 4, y: 1 },
        ],
        frameDuration: 150,
      },
      unlit: { frame: { x: 0, y: 0 }, frameDuration: 200 },
      burning: { frame: { x: 0, y: 0 }, frameDuration: 200 },
      dying: { frame: { x: 0, y: 0 }, frameDuration: 200 },
      extinguished: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    },
    defaultState: 'idle',
    size: 1,
  },
  campfire: {
    id: 'campfire-1',
    type: 'campfire',
    name: 'Camp Fire',
    imageUrl: '/src/assets/travelers_camp.png',
    spritesheetSize: { columns: 5, rows: 3 },
    animationConfig: {
      unlit: {
        frame: { x: 0, y: 0 },
        frameDuration: 200,
      },
      burning: {
        frames: [
          { x: 1, y: 0 },
          { x: 2, y: 0 },
          { x: 3, y: 0 },
          { x: 4, y: 0 },
        ],
        frameDuration: 200,
      },
      dying: {
        frames: [
          { x: 1, y: 1 },
          { x: 2, y: 1 },
          { x: 3, y: 1 },
          { x: 4, y: 1 },
        ],
        frameDuration: 200,
      },
      extinguished: {
        frames: [{ x: 0, y: 1 }],
        frameDuration: 150,
      },
      idle: { frame: { x: 0, y: 0 }, frameDuration: 200 },
      walking: { frame: { x: 0, y: 0 }, frameDuration: 200 },
      running: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    },
    defaultState: 'unlit',
    size: 1,
  },
}; 