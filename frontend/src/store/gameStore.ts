import {create} from 'zustand';
import {CharacterAnimationType} from "../types/animations";
import {GameData} from '../types/game';

export enum GameState {
  MENU,
  PLAYING,
  GAME_OVER
}

// Define interfaces for the board data
interface Position {
  x: number;
  y: number;
}

interface Square {
  position: Position;
  contains_entity: boolean;
}

const DEFAULT_GAME_DATA:GameData = {
  map: {
    size: 20,
    border_size: 1,
    grid: Array(400).fill(null).map((_, index) => ({
      x: index % 5,
      y: Math.floor(index / 5)
    }))
  },
  entities: []
}

interface Entity {
  id: string;
  type: string;
  name: string;
  position: Position | null;
  strength: number;
  inventory: string[];
  can_perform: string[];
  description: string;
  // Add other entity properties as needed
}

interface Board {
  width: number;
  height: number;
  squares: Square[];
}

interface GameStore {
  score: number;
  health: number;
  gameState: GameState;
  highScore: number;
  currentAnimation: CharacterAnimationType;
  isManualAnimation: boolean;
  // Add board and entities
  board: Board;
  entities: Entity[];
  // Existing functions
  incrementScore: () => void;
  decrementHealth: () => void;
  startGame: () => void;
  setGameOver: () => void;
  resetGame: () => void;
  setAnimation: (animation: CharacterAnimationType) => void;
  setManualAnimation: (isManual: boolean) => void;
  
  // New functions for board management
  updateBoard: (board: Board) => void;
  updateSquare: (x: number, y: number, containsEntity: boolean) => void;
  updateEntities: (entities: Entity[]) => void;
  moveEntity: (entityId: string, newPosition: Position) => void;
  
  // New properties
  position: [number, number, number];
  setPosition: (position: [number, number, number]) => void;
  gameData: GameData;
  setGameData: (gameData: GameData) => void;
}

const INITIAL_HEALTH = 3;

// Default board configuration
const DEFAULT_BOARD: Board = {
  width: 20,
  height: 20,
  squares: Array(400).fill(null).map((_, index) => ({
    position: { 
      x: index % 5, 
      y: Math.floor(index / 5) 
    },
    contains_entity: false
  }))

};

export const useGameStore = create<GameStore>((set, get) => ({
  score: 0,
  health: INITIAL_HEALTH,
  gameState: GameState.MENU,
  highScore: 0,
  currentAnimation: CharacterAnimationType.IDLE_DOWN,
  isManualAnimation: false,
  // Initialize board and entities
  board: DEFAULT_BOARD,
  entities: [],
  gameData: DEFAULT_GAME_DATA,
  // Existing methods
  incrementScore: () => set(state => ({ score: state.score + 1 })),
  
  decrementHealth: () => set(state => ({ health: state.health - 1 })),
  
  startGame: () => set({
    score: 0,
    health: INITIAL_HEALTH,
    gameState: GameState.PLAYING
  }),
  
  setGameOver: () => {
    const { score, highScore } = get();
    const newHighScore = score > highScore ? score : highScore;
    
    set({
      gameState: GameState.GAME_OVER,
      highScore: newHighScore
    });
  },
  
  resetGame: () => set({
    score: 0,
    health: INITIAL_HEALTH,
    gameState: GameState.MENU
  }),

  setAnimation: (animation: CharacterAnimationType) => set({
    currentAnimation: animation,
    isManualAnimation: true
  }),

  setManualAnimation: (isManual: boolean) => set({
    isManualAnimation: isManual
  }),

  // New methods for board management
  updateBoard: (board: Board) => set({ board }),
  
  updateSquare: (x: number, y: number, containsEntity: boolean) => set(state => {
    const newSquares = [...state.board.squares];
    const index = y * state.board.width + x;
    if (index >= 0 && index < newSquares.length) {
      newSquares[index] = { 
        ...newSquares[index], 
        contains_entity: containsEntity 
      };
    }
    return { board: { ...state.board, squares: newSquares } };
  }),
  
  updateEntities: (entities: Entity[]) => set({ entities }),
  
  moveEntity: (entityId: string, newPosition: Position) => set(state => {
    const newEntities = state.entities.map(entity => 
      entity.id === entityId 
        ? { ...entity, position: newPosition }
        : entity
    );
    
    return { entities: newEntities };
  }),

  setGameData: (gameData: GameData) => set({ gameData }),
  
  // New properties
  position: [10, 10, 0],
  setPosition: (position: [number, number, number]) => set({ position })
})); 