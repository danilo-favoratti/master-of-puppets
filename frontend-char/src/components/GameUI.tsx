import { useState } from "react";
import { useGameStore } from "../store/gameStore";
import { AnimationType } from "./CharacterSprite";

const GameUI = () => {
  const score = useGameStore((state) => state.score);
  const health = useGameStore((state) => state.health);
  const highScore = useGameStore((state) => state.highScore);
  const startGame = useGameStore((state) => state.startGame);
  const resetGame = useGameStore((state) => state.resetGame);
  const setAnimation = useGameStore((state) => state.setAnimation);
  const currentAnimation = useGameStore((state) => state.currentAnimation);
  const isManualAnimation = useGameStore((state) => state.isManualAnimation);
  const setManualAnimation = useGameStore((state) => state.setManualAnimation);

  const [showAnimations, setShowAnimations] = useState(false);

  // Group animations by category
  const animationGroups = {
    "Idle Animations": [
      AnimationType.IDLE_DOWN,
      AnimationType.IDLE_UP,
      AnimationType.IDLE_LEFT,
      AnimationType.IDLE_RIGHT,
    ],
    "Walk Animations": [
      AnimationType.WALK_DOWN,
      AnimationType.WALK_UP,
      AnimationType.WALK_LEFT,
      AnimationType.WALK_RIGHT,
    ],
    "Run Animations": [
      AnimationType.RUN_DOWN,
      AnimationType.RUN_UP,
      AnimationType.RUN_LEFT,
      AnimationType.RUN_RIGHT,
    ],
    "Push Animations": [
      AnimationType.PUSH_DOWN,
      AnimationType.PUSH_UP,
      AnimationType.PUSH_LEFT,
      AnimationType.PUSH_RIGHT,
    ],
    "Pull Animations": [
      AnimationType.PULL_DOWN,
      AnimationType.PULL_UP,
      AnimationType.PULL_LEFT,
      AnimationType.PULL_RIGHT,
    ],
    "Jump Animations": [
      AnimationType.JUMP_DOWN,
      AnimationType.JUMP_UP,
      AnimationType.JUMP_LEFT,
      AnimationType.JUMP_RIGHT,
    ],
  };

  // Format the animation name for display
  const formatAnimationName = (animation: string) => {
    return animation
      .replace(/_/g, " ")
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const handleAnimationChange = (animation: AnimationType) => {
    setAnimation(animation);
  };

  const toggleManualControl = () => {
    setManualAnimation(!isManualAnimation);
  };

  return (
    <div className="game-ui">
      <div className="game-stats">
        <p>Score: {score}</p>
        <p>Health: {health}</p>
        <p>High Score: {highScore}</p>
        <p>Current Animation: {formatAnimationName(currentAnimation)}</p>
        <p>
          <span
            className={`control-mode ${isManualAnimation ? "manual" : "auto"}`}
          >
            Control Mode: {isManualAnimation ? "Manual" : "Auto"}
          </span>
        </p>
      </div>

      <div className="game-actions">
        <button onClick={() => startGame()}>Start Game</button>
        <button onClick={() => resetGame()}>Reset Game</button>
        <button onClick={() => setShowAnimations(!showAnimations)}>
          {showAnimations ? "Hide Animations" : "Show Animations"}
        </button>
        <button onClick={toggleManualControl}>
          {isManualAnimation ? "Switch to Auto" : "Switch to Manual"}
        </button>
      </div>

      {showAnimations && (
        <div className="animation-controls">
          <h3>Animation Controls</h3>
          <div className="animation-groups">
            {Object.entries(animationGroups).map(([groupName, animations]) => (
              <div key={groupName} className="animation-group">
                <h4>{groupName}</h4>
                <div className="animation-buttons">
                  {animations.map((animation) => (
                    <button
                      key={animation}
                      onClick={() => handleAnimationChange(animation)}
                      className={currentAnimation === animation ? "active" : ""}
                    >
                      {formatAnimationName(animation)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GameUI;
