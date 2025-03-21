import { useFrame } from "@react-three/fiber";
import { useEffect, useState } from "react";
import { useKeyboardControls } from "../hooks/useKeyboardControls";
import { useGameStore } from "../store/gameStore";
import CharacterSprite, { AnimationType } from "./CharacterSprite";

const Game = () => {
  const keys = useKeyboardControls();
  const [position, setPosition] = useState<[number, number, number]>([0, 0, 0]);
  const currentAnimation = useGameStore((state) => state.currentAnimation);
  const setAnimation = useGameStore((state) => state.setAnimation);
  const isManualAnimation = useGameStore((state) => state.isManualAnimation);
  const setManualAnimation = useGameStore((state) => state.setManualAnimation);
  const [isPushing, setIsPushing] = useState(false);
  const [isPulling, setIsPulling] = useState(false);
  const [isJumping, setIsJumping] = useState(false);

  // Speed of character movement
  const walkSpeed = 0.05;
  const runSpeed = 0.1;

  // Reset manual animation control when any movement key is pressed
  useEffect(() => {
    const anyMovementKeyPressed =
      keys.ArrowUp ||
      keys.ArrowDown ||
      keys.ArrowLeft ||
      keys.ArrowRight ||
      keys.Shift ||
      keys.z ||
      keys.x ||
      keys[" "];

    if (anyMovementKeyPressed && isManualAnimation) {
      setManualAnimation(false);
    }
  }, [keys, isManualAnimation, setManualAnimation]);

  // Debug current animation state
  useEffect(() => {
    console.log(`Current animation state: ${currentAnimation}`);
    console.log(
      `Movement keys: Up=${keys.ArrowUp}, Down=${keys.ArrowDown}, Left=${keys.ArrowLeft}, Right=${keys.ArrowRight}`
    );
    console.log(
      `Action keys: Shift=${keys.Shift}, Z=${keys.z}, X=${keys.x}, Space=${keys[" "]}`
    );
  }, [currentAnimation, keys]);

  useFrame(() => {
    // Handle character movement based on keyboard input
    let newX = position[0];
    let newY = position[1];
    let newAnimation = currentAnimation;
    let isMoving = false;

    // Skip animation updates if manual control is enabled
    if (!isManualAnimation) {
      // Check if shift key is pressed to run
      const isRunPressed = keys.Shift;
      const currentSpeed = isRunPressed ? runSpeed : walkSpeed;

      // Handle jump with spacebar
      if (keys[" "] && !isJumping) {
        setIsJumping(true);
        console.log("Jump triggered");
      }

      // Handle Z key for pushing
      if (keys.z && !isPushing) {
        setIsPushing(true);
        console.log("Push triggered");
        // Reset after some time to demo the animation
        setTimeout(() => {
          setIsPushing(false);
          console.log("Push completed");
        }, 2000);
      }

      // Handle X key for pulling
      if (keys.x && !isPulling) {
        setIsPulling(true);
        console.log("Pull triggered");
        // Reset after some time to demo the animation
        setTimeout(() => {
          setIsPulling(false);
          console.log("Pull completed");
        }, 2000);
      }

      // Set animation based on movement and state
      if (isJumping) {
        // Jump animation based on last direction
        if (
          currentAnimation === AnimationType.IDLE_DOWN ||
          currentAnimation === AnimationType.WALK_DOWN ||
          currentAnimation === AnimationType.RUN_DOWN
        ) {
          newAnimation = AnimationType.JUMP_DOWN;
        } else if (
          currentAnimation === AnimationType.IDLE_UP ||
          currentAnimation === AnimationType.WALK_UP ||
          currentAnimation === AnimationType.RUN_UP
        ) {
          newAnimation = AnimationType.JUMP_UP;
        } else if (
          currentAnimation === AnimationType.IDLE_LEFT ||
          currentAnimation === AnimationType.WALK_LEFT ||
          currentAnimation === AnimationType.RUN_LEFT
        ) {
          newAnimation = AnimationType.JUMP_LEFT;
        } else if (
          currentAnimation === AnimationType.IDLE_RIGHT ||
          currentAnimation === AnimationType.WALK_RIGHT ||
          currentAnimation === AnimationType.RUN_RIGHT
        ) {
          newAnimation = AnimationType.JUMP_RIGHT;
        }
      } else if (isPushing) {
        // Push animation based on last direction
        if (
          currentAnimation === AnimationType.IDLE_DOWN ||
          currentAnimation === AnimationType.WALK_DOWN ||
          currentAnimation === AnimationType.RUN_DOWN
        ) {
          newAnimation = AnimationType.PUSH_DOWN;
        } else if (
          currentAnimation === AnimationType.IDLE_UP ||
          currentAnimation === AnimationType.WALK_UP ||
          currentAnimation === AnimationType.RUN_UP
        ) {
          newAnimation = AnimationType.PUSH_UP;
        } else if (
          currentAnimation === AnimationType.IDLE_LEFT ||
          currentAnimation === AnimationType.WALK_LEFT ||
          currentAnimation === AnimationType.RUN_LEFT
        ) {
          newAnimation = AnimationType.PUSH_LEFT;
        } else if (
          currentAnimation === AnimationType.IDLE_RIGHT ||
          currentAnimation === AnimationType.WALK_RIGHT ||
          currentAnimation === AnimationType.RUN_RIGHT
        ) {
          newAnimation = AnimationType.PUSH_RIGHT;
        }
      } else if (isPulling) {
        // Pull animation based on last direction
        if (
          currentAnimation === AnimationType.IDLE_DOWN ||
          currentAnimation === AnimationType.WALK_DOWN ||
          currentAnimation === AnimationType.RUN_DOWN
        ) {
          newAnimation = AnimationType.PULL_DOWN;
        } else if (
          currentAnimation === AnimationType.IDLE_UP ||
          currentAnimation === AnimationType.WALK_UP ||
          currentAnimation === AnimationType.RUN_UP
        ) {
          newAnimation = AnimationType.PULL_UP;
        } else if (
          currentAnimation === AnimationType.IDLE_LEFT ||
          currentAnimation === AnimationType.WALK_LEFT ||
          currentAnimation === AnimationType.RUN_LEFT
        ) {
          newAnimation = AnimationType.PULL_LEFT;
        } else if (
          currentAnimation === AnimationType.IDLE_RIGHT ||
          currentAnimation === AnimationType.WALK_RIGHT ||
          currentAnimation === AnimationType.RUN_RIGHT
        ) {
          newAnimation = AnimationType.PULL_RIGHT;
        }
      } else {
        // Normal movement
        if (keys.ArrowUp) {
          newY += currentSpeed;
          newAnimation = isRunPressed
            ? AnimationType.RUN_UP
            : AnimationType.WALK_UP;
          isMoving = true;
        }
        if (keys.ArrowDown) {
          newY -= currentSpeed;
          newAnimation = isRunPressed
            ? AnimationType.RUN_DOWN
            : AnimationType.WALK_DOWN;
          isMoving = true;
        }
        if (keys.ArrowLeft) {
          newX -= currentSpeed;
          newAnimation = isRunPressed
            ? AnimationType.RUN_LEFT
            : AnimationType.WALK_LEFT;
          isMoving = true;
        }
        if (keys.ArrowRight) {
          newX += currentSpeed;
          newAnimation = isRunPressed
            ? AnimationType.RUN_RIGHT
            : AnimationType.WALK_RIGHT;
          isMoving = true;
        }

        // Set to idle if not moving
        if (!isMoving) {
          // Convert from walk/run to idle based on last direction
          if (
            currentAnimation === AnimationType.WALK_DOWN ||
            currentAnimation === AnimationType.RUN_DOWN
          ) {
            newAnimation = AnimationType.IDLE_DOWN;
          } else if (
            currentAnimation === AnimationType.WALK_UP ||
            currentAnimation === AnimationType.RUN_UP
          ) {
            newAnimation = AnimationType.IDLE_UP;
          } else if (
            currentAnimation === AnimationType.WALK_LEFT ||
            currentAnimation === AnimationType.RUN_LEFT
          ) {
            newAnimation = AnimationType.IDLE_LEFT;
          } else if (
            currentAnimation === AnimationType.WALK_RIGHT ||
            currentAnimation === AnimationType.RUN_RIGHT
          ) {
            newAnimation = AnimationType.IDLE_RIGHT;
          }
        }
      }

      if (newAnimation !== currentAnimation) {
        setAnimation(newAnimation);
        // Don't set manual flag here as we're in auto mode
      }
    }

    // Always update the position regardless of animation control
    setPosition([newX, newY, 0]);
  });

  return (
    <>
      <CharacterSprite
        position={position}
        scale={[1, 1, 1]}
        rows={8}
        cols={8}
        animation={currentAnimation}
        onAnimationComplete={(animation) => {
          console.log(`Animation ${animation} completed`);

          // Quando uma animação de pulo terminar, voltar para o estado idle na mesma direção
          if (animation === AnimationType.JUMP_DOWN) {
            setIsJumping(false);
            setAnimation(AnimationType.IDLE_DOWN);
          } else if (animation === AnimationType.JUMP_UP) {
            setIsJumping(false);
            setAnimation(AnimationType.IDLE_UP);
          } else if (animation === AnimationType.JUMP_LEFT) {
            setIsJumping(false);
            setAnimation(AnimationType.IDLE_LEFT);
          } else if (animation === AnimationType.JUMP_RIGHT) {
            setIsJumping(false);
            setAnimation(AnimationType.IDLE_RIGHT);
          }
        }}
      />
    </>
  );
};

export default Game;
