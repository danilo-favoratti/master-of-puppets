import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useState } from "react";
import { useGameStore } from "../store/gameStore";
import CharacterSprite, { AnimationType } from "./CharacterSprite";

interface GameProps {
  executeCommand: (commandName: string, result: string, params: any) => void;
  registerCommandHandler: (handler: (cmd: string, result: string, params: any) => void) => void;
}

const Game = ({ executeCommand, registerCommandHandler }: GameProps) => {
  const { camera } = useThree();
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

  // Execute animation commands received from websocket
  useEffect(() => {
    // Define a mapping of commands to animation functions
    const commandMap: Record<string, (params: any) => void> = {
      jump: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        
        switch (direction) {
          case "up":
            animation = AnimationType.JUMP_UP;
            // Move character up slightly when jumping
            setPosition(([x, y, z]) => [x, y + 0.2, z]);
            setTimeout(() => setPosition(([x, y, z]) => [x, y - 0.2, z]), 500);
            break;
          case "left":
            animation = AnimationType.JUMP_LEFT;
            // Move character left slightly when jumping
            setPosition(([x, y, z]) => [x - 0.2, y, z]);
            setTimeout(() => setPosition(([x, y, z]) => [x + 0.2, y, z]), 500);
            break;
          case "right":
            animation = AnimationType.JUMP_RIGHT;
            // Move character right slightly when jumping
            setPosition(([x, y, z]) => [x + 0.2, y, z]);
            setTimeout(() => setPosition(([x, y, z]) => [x - 0.2, y, z]), 500);
            break;
          default:
            animation = AnimationType.JUMP_DOWN;
            // Move character down slightly when jumping
            setPosition(([x, y, z]) => [x, y - 0.2, z]);
            setTimeout(() => setPosition(([x, y, z]) => [x, y + 0.2, z]), 500);
        }
        
        setAnimation(animation);
        setIsJumping(true);
        
        // Reset after animation completes (roughly 1 second)
        setTimeout(() => {
          setIsJumping(false);
        }, 1000);
      },
      
      walk: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        const moveDistance = 1.0; // Distance to move
        
        switch (direction) {
          case "up":
            animation = AnimationType.WALK_UP;
            // Move character up
            setPosition(([x, y, z]) => [x, y + moveDistance, z]);
            break;
          case "left":
            animation = AnimationType.WALK_LEFT;
            // Move character left
            setPosition(([x, y, z]) => [x - moveDistance, y, z]);
            break;
          case "right":
            animation = AnimationType.WALK_RIGHT;
            // Move character right
            setPosition(([x, y, z]) => [x + moveDistance, y, z]);
            break;
          default:
            animation = AnimationType.WALK_DOWN;
            // Move character down
            setPosition(([x, y, z]) => [x, y - moveDistance, z]);
        }
        
        setAnimation(animation);
        
        // Reset after walking (roughly 1 second)
        setTimeout(() => {
          // Set to idle in the same direction
          if (animation === AnimationType.WALK_UP) {
            setAnimation(AnimationType.IDLE_UP);
          } else if (animation === AnimationType.WALK_LEFT) {
            setAnimation(AnimationType.IDLE_LEFT);
          } else if (animation === AnimationType.WALK_RIGHT) {
            setAnimation(AnimationType.IDLE_RIGHT);
          } else {
            setAnimation(AnimationType.IDLE_DOWN);
          }
        }, 1000);
      },
      
      run: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        const moveDistance = 2.0; // Distance to move (faster than walking)
        
        switch (direction) {
          case "up":
            animation = AnimationType.RUN_UP;
            // Move character up fast
            setPosition(([x, y, z]) => [x, y + moveDistance, z]);
            break;
          case "left":
            animation = AnimationType.RUN_LEFT;
            // Move character left fast
            setPosition(([x, y, z]) => [x - moveDistance, y, z]);
            break;
          case "right":
            animation = AnimationType.RUN_RIGHT;
            // Move character right fast
            setPosition(([x, y, z]) => [x + moveDistance, y, z]);
            break;
          default:
            animation = AnimationType.RUN_DOWN;
            // Move character down fast
            setPosition(([x, y, z]) => [x, y - moveDistance, z]);
        }
        
        setAnimation(animation);
        
        // Reset after running (roughly 0.6 seconds)
        setTimeout(() => {
          // Set to idle in the same direction
          if (animation === AnimationType.RUN_UP) {
            setAnimation(AnimationType.IDLE_UP);
          } else if (animation === AnimationType.RUN_LEFT) {
            setAnimation(AnimationType.IDLE_LEFT);
          } else if (animation === AnimationType.RUN_RIGHT) {
            setAnimation(AnimationType.IDLE_RIGHT);
          } else {
            setAnimation(AnimationType.IDLE_DOWN);
          }
        }, 600);
      },
      
      push: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        
        switch (direction) {
          case "up":
            animation = AnimationType.PUSH_UP;
            break;
          case "left":
            animation = AnimationType.PUSH_LEFT;
            break;
          case "right":
            animation = AnimationType.PUSH_RIGHT;
            break;
          default:
            animation = AnimationType.PUSH_DOWN;
        }
        
        setAnimation(animation);
        setIsPushing(true);
        
        // Reset after animation (roughly 0.8 seconds)
        setTimeout(() => {
          setIsPushing(false);
          // Set to idle in the same direction
          if (animation === AnimationType.PUSH_UP) {
            setAnimation(AnimationType.IDLE_UP);
          } else if (animation === AnimationType.PUSH_LEFT) {
            setAnimation(AnimationType.IDLE_LEFT);
          } else if (animation === AnimationType.PUSH_RIGHT) {
            setAnimation(AnimationType.IDLE_RIGHT);
          } else {
            setAnimation(AnimationType.IDLE_DOWN);
          }
        }, 800);
      },
      
      pull: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        
        switch (direction) {
          case "up":
            animation = AnimationType.PULL_UP;
            break;
          case "left":
            animation = AnimationType.PULL_LEFT;
            break;
          case "right":
            animation = AnimationType.PULL_RIGHT;
            break;
          default:
            animation = AnimationType.PULL_DOWN;
        }
        
        setAnimation(animation);
        setIsPulling(true);
        
        // Reset after animation (roughly 0.8 seconds)
        setTimeout(() => {
          setIsPulling(false);
          // Set to idle in the same direction
          if (animation === AnimationType.PULL_UP) {
            setAnimation(AnimationType.IDLE_UP);
          } else if (animation === AnimationType.PULL_LEFT) {
            setAnimation(AnimationType.IDLE_LEFT);
          } else if (animation === AnimationType.PULL_RIGHT) {
            setAnimation(AnimationType.IDLE_RIGHT);
          } else {
            setAnimation(AnimationType.IDLE_DOWN);
          }
        }, 800);
      },
    };
    
    // Create command handler
    const handleCommand = (command: string, result: string, params: any) => {
      if (commandMap[command]) {
        commandMap[command](params);
      } else {
        console.warn("Unknown command received:", command);
      }
    };
    
    // Register our command handler with the parent App component
    registerCommandHandler(handleCommand);
    
    return () => {
      // Cleanup
    };
  }, [executeCommand, setAnimation, registerCommandHandler]);

  // Handle animation completion
  const handleAnimationComplete = (animation: AnimationType) => {
    // Animation completed handler
  };

  // Make camera follow the character
  useEffect(() => {
    camera.position.x = position[0];
    camera.position.y = position[1];
  }, [camera, position]);

  return (
    <>
      <CharacterSprite
        position={position}
        scale={[1, 1, 1]}
        rows={8}
        cols={8}
        animation={currentAnimation}
        onAnimationComplete={handleAnimationComplete}
      />
    </>
  );
};

export default Game; 