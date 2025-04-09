import { Position } from "../types/game";

/**
 * Position utility functions for working with the Position type
 * Helps handle the conversion between tuple [x, y] and object {x, y} formats
 */

/**
 * Convert a Position tuple to an object with x, y properties
 */
export const positionToXY = (position: Position): { x: number, y: number, z?: number } => {
  return {
    x: position[0],
    y: position[1],
    z: position[2]
  };
};

/**
 * Convert an object with x, y properties to a Position tuple
 */
export const xyToPosition = (xy: { x: number, y: number, z?: number }): Position => {
  return xy.z !== undefined ? [xy.x, xy.y, xy.z] : [xy.x, xy.y];
};

/**
 * Get x coordinate from a Position tuple
 */
export const getX = (position: Position): number => position[0];

/**
 * Get y coordinate from a Position tuple
 */
export const getY = (position: Position): number => position[1];

/**
 * Get z coordinate from a Position tuple (if exists)
 */
export const getZ = (position: Position): number | undefined => position[2];

/**
 * Create a new Position with updated x coordinate
 */
export const setX = (position: Position, x: number): Position => {
  return position.length === 3 ? [x, position[1], position[2]] : [x, position[1]];
};

/**
 * Create a new Position with updated y coordinate
 */
export const setY = (position: Position, y: number): Position => {
  return position.length === 3 ? [position[0], y, position[2]] : [position[0], y];
};

/**
 * Create a new Position with updated z coordinate
 */
export const setZ = (position: Position, z: number): Position => {
  return [position[0], position[1], z];
};

/**
 * Add dx, dy to a Position
 */
export const addToPosition = (position: Position, dx: number, dy: number): Position => {
  return position.length === 3 
    ? [position[0] + dx, position[1] + dy, position[2]] 
    : [position[0] + dx, position[1] + dy];
};

/**
 * Calculate absolute difference between two positions
 */
export const positionDiff = (pos1: Position, pos2: Position): {dx: number, dy: number} => {
  return {
    dx: Math.abs(pos1[0] - pos2[0]),
    dy: Math.abs(pos1[1] - pos2[1])
  };
};

/**
 * Linear interpolation between two numbers
 */
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/**
 * Linear interpolation between two positions
 */
export const lerpPosition = (start: Position, end: Position, t: number): Position => {
  if (start.length === 3 && end.length === 3) {
    return [
      lerp(start[0], end[0], t),
      lerp(start[1], end[1], t),
      lerp(start[2], end[2], t)
    ];
  }
  return [
    lerp(start[0], end[0], t),
    lerp(start[1], end[1], t)
  ];
}; 