// Define animation types
export enum AnimationType {
  IDLE_DOWN = "idleDown",
  IDLE_UP = "idleUp",
  IDLE_LEFT = "idleLeft",
  IDLE_RIGHT = "idleRight",
  WALK_DOWN = "walkDown",
  WALK_UP = "walkUp",
  WALK_LEFT = "walkLeft",
  WALK_RIGHT = "walkRight",
  RUN_DOWN = "runDown",
  RUN_UP = "runUp",
  RUN_LEFT = "runLeft",
  RUN_RIGHT = "runRight",
  PUSH_DOWN = "pushDown",
  PUSH_UP = "pushUp",
  PUSH_LEFT = "pushLeft",
  PUSH_RIGHT = "pushRight",
  PULL_DOWN = "pullDown",
  PULL_UP = "pullUp",
  PULL_LEFT = "pullLeft",
  PULL_RIGHT = "pullRight",
  JUMP_DOWN = "jumpDown",
  JUMP_UP = "jumpUp",
  JUMP_LEFT = "jumpLeft",
  JUMP_RIGHT = "jumpRight",
  // Other animations can be added as needed (fishing, farming, etc.)
}

// Animation configuration interface
export interface AnimationConfig {
  frames: number[];
  frameTiming: number[];
  loop?: boolean;
}

// Animation frame definitions
// Each row in the sprite sheet has 8 columns (frames)
// Based on the documentation, rows 0-3 are for directional animations (down, up, left, right)
export const ANIMATIONS: Record<AnimationType, AnimationConfig> = {
  // Idle animations (first frame of each row)
  [AnimationType.IDLE_DOWN]: {
    frames: [0],
    frameTiming: [300],
  },
  [AnimationType.IDLE_UP]: {
    frames: [8],
    frameTiming: [300],
  },
  [AnimationType.IDLE_LEFT]: {
    frames: [24],
    frameTiming: [300],
  },
  [AnimationType.IDLE_RIGHT]: {
    frames: [16],
    frameTiming: [300],
  },

  // Walk animations (frames 0-5 on rows 0-3)
  [AnimationType.WALK_DOWN]: {
    frames: [32, 33, 34, 35, 36, 37],
    frameTiming: [135, 135, 135, 135, 135, 135],
  },
  [AnimationType.WALK_UP]: {
    frames: [40, 41, 42, 43, 44, 45],
    frameTiming: [135, 135, 135, 135, 135, 135],
  },
  [AnimationType.WALK_LEFT]: {
    frames: [56, 57, 58, 59, 60, 61],
    frameTiming: [135, 135, 135, 135, 135, 135],
  },
  [AnimationType.WALK_RIGHT]: {
    frames: [48, 49, 50, 51, 52, 53],
    frameTiming: [135, 135, 135, 135, 135, 135],
  },

  // Run animations (per docs: frames 1,2,7,4,5,8 in sequence)
  [AnimationType.RUN_DOWN]: {
    frames: [64, 65, 70, 67, 68, 71],
    frameTiming: [80, 55, 125, 80, 55, 125],
  },
  [AnimationType.RUN_UP]: {
    frames: [72, 73, 78, 75, 76, 79],
    frameTiming: [80, 55, 125, 80, 55, 125],
  },
  [AnimationType.RUN_LEFT]: {
    frames: [88, 89, 94, 91, 92, 95],
    frameTiming: [80, 55, 125, 80, 55, 125],
  },
  [AnimationType.RUN_RIGHT]: {
    frames: [80, 81, 86, 83, 84, 87],
    frameTiming: [80, 55, 125, 80, 55, 125],
  },

  // Push animations (2-frame loop - columns 1,2 on rows 0-3)
  [AnimationType.PUSH_DOWN]: {
    frames: [1, 2],
    frameTiming: [300, 300],
  },
  [AnimationType.PUSH_UP]: {
    frames: [9, 10],
    frameTiming: [300, 300],
  },
  [AnimationType.PUSH_LEFT]: {
    frames: [25, 26],
    frameTiming: [300, 300],
  },
  [AnimationType.PUSH_RIGHT]: {
    frames: [17, 18],
    frameTiming: [300, 300],
  },

  // Pull animations (2-frame loop - columns 3,4 on rows 0-3)
  [AnimationType.PULL_DOWN]: {
    frames: [3, 4],
    frameTiming: [400, 400],
  },
  [AnimationType.PULL_UP]: {
    frames: [11, 12],
    frameTiming: [400, 400],
  },
  [AnimationType.PULL_LEFT]: {
    frames: [27, 28],
    frameTiming: [400, 400],
  },
  [AnimationType.PULL_RIGHT]: {
    frames: [19, 20],
    frameTiming: [400, 400],
  },

  // Jump animations (4-frame sequence - last 3 columns on rows 0-3, with the first frame repeated at the end)
  [AnimationType.JUMP_DOWN]: {
    frames: [5, 6, 7, 5],
    frameTiming: [300, 150, 100, 300],
    loop: false,
  },
  [AnimationType.JUMP_UP]: {
    frames: [13, 14, 15, 13],
    frameTiming: [300, 150, 100, 300],
    loop: false,
  },
  [AnimationType.JUMP_LEFT]: {
    frames: [29, 30, 31, 29],
    frameTiming: [300, 150, 100, 300],
    loop: false,
  },
  [AnimationType.JUMP_RIGHT]: {
    frames: [21, 22, 23, 21],
    frameTiming: [300, 150, 100, 300],
    loop: false,
  },
}; 