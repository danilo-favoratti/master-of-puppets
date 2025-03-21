import { create } from 'zustand';
import { AnimationType } from '../components/CharacterSprite';

export enum GameState {
  MENU,
  PLAYING,
  GAME_OVER
}

interface GameStore {
  score: number;
  health: number;
  gameState: GameState;
  highScore: number;
  currentAnimation: AnimationType;
  isManualAnimation: boolean;
  incrementScore: () => void;
  decrementHealth: () => void;
  startGame: () => void;
  setGameOver: () => void;
  resetGame: () => void;
  setAnimation: (animation: AnimationType) => void;
  setManualAnimation: (isManual: boolean) => void;
}

const INITIAL_HEALTH = 3;

export const useGameStore = create<GameStore>((set, get) => ({
  score: 0,
  health: INITIAL_HEALTH,
  gameState: GameState.MENU,
  highScore: 0,
  currentAnimation: AnimationType.IDLE_DOWN,
  isManualAnimation: false,
  
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

  setAnimation: (animation: AnimationType) => set({
    currentAnimation: animation,
    isManualAnimation: true
  }),

  setManualAnimation: (isManual: boolean) => set({
    isManualAnimation: isManual
  })
})); 