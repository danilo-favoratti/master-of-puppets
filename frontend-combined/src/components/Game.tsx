import { useThree, useFrame } from "@react-three/fiber";
import { useEffect, useState, useRef } from "react";
import { useGameStore } from "../store/gameStore";
import CharacterHair from "./CharacterHair";
import CharacterOutfit from "./CharacterOutfit";
import CharacterSprite, { AnimationType } from "./CharacterSprite";

interface GameProps {
  executeCommand: (commandName: string, result: string, params: any) => void;
  registerCommandHandler: (
    handler: (cmd: string, result: string, params: any) => void
  ) => void;
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

  // Speed constants
  const walkSpeed = 0.05; // unused now
  const runSpeed = 0.1;   // unused now

  // Movement interpolation ref
  const movementRef = useRef<null | { start: [number, number, number], end: [number, number, number], duration: number, elapsedTime: number }>(null);
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

  const animateMovement = (delta: number, duration: number, direction: string) => {
    const currentPos = position;
    let dx = 0, dy = 0, dz = 0;
    if (direction === "up") dy = delta;
    else if (direction === "down") dy = -delta;
    else if (direction === "left") dx = -delta;
    else if (direction === "right") dx = delta;
    const target: [number, number, number] = [currentPos[0] + dx, currentPos[1] + dy, currentPos[2] + dz];
    movementRef.current = { start: currentPos, end: target, duration: duration, elapsedTime: 0 };
  };

  // Smoothly update position based on movementRef using useFrame
  useFrame((_, delta) => {
    if (movementRef.current) {
      movementRef.current.elapsedTime += delta;
      let t = movementRef.current.elapsedTime / movementRef.current.duration;
      if (t > 1) t = 1;
      setPosition([
        lerp(movementRef.current.start[0], movementRef.current.end[0], t),
        lerp(movementRef.current.start[1], movementRef.current.end[1], t),
        lerp(movementRef.current.start[2], movementRef.current.end[2], t)
      ]);
      if (t === 1) {
        movementRef.current = null;
      }
    }
  });

  // Execute animation commands received from websocket
  useEffect(() => {
    // Define a mapping of commands to animation functions
    const commandMap: Record<string, (params: any) => void> = {
      jump: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        const originalPos = position;
        switch (direction) {
          case "up":
            animation = AnimationType.JUMP_UP;
            animateMovement(0.2, 0.5, "up");
            break;
          case "left":
            animation = AnimationType.JUMP_LEFT;
            animateMovement(0.2, 0.5, "left");
            break;
          case "right":
            animation = AnimationType.JUMP_RIGHT;
            animateMovement(0.2, 0.5, "right");
            break;
          default:
            animation = AnimationType.JUMP_DOWN;
            animateMovement(0.2, 0.5, "down");
        }
        setAnimation(animation);
        setIsJumping(true);
        // After first phase (0.5 sec), animate back to original position
        setTimeout(() => {
          movementRef.current = { start: position, end: originalPos, duration: 0.5, elapsedTime: 0 };
          setIsJumping(false);
        }, 500);
      },

      walk: (params) => {
        const direction = params?.direction || "down";
        let animation: AnimationType;
        const moveDistance = 1.0; // Distance to move
        switch (direction) {
          case "up":
            animation = AnimationType.WALK_UP;
            animateMovement(1.0, 1.0, "up");
            break;
          case "left":
            animation = AnimationType.WALK_LEFT;
            animateMovement(1.0, 1.0, "left");
            break;
          case "right":
            animation = AnimationType.WALK_RIGHT;
            animateMovement(1.0, 1.0, "right");
            break;
          default:
            animation = AnimationType.WALK_DOWN;
            animateMovement(1.0, 1.0, "down");
        }
        setAnimation(animation);
        // After walking duration, revert to idle animation
        setTimeout(() => {
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
        const moveDistance = 2.0; // Distance to move when running
        switch (direction) {
          case "up":
            animation = AnimationType.RUN_UP;
            animateMovement(2.0, 0.6, "up");
            break;
          case "left":
            animation = AnimationType.RUN_LEFT;
            animateMovement(2.0, 0.6, "left");
            break;
          case "right":
            animation = AnimationType.RUN_RIGHT;
            animateMovement(2.0, 0.6, "right");
            break;
          default:
            animation = AnimationType.RUN_DOWN;
            animateMovement(2.0, 0.6, "down");
        }
        setAnimation(animation);
        // After running, revert to idle
        setTimeout(() => {
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
      
      // Other commands (push, pull) remain unchanged
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
        setTimeout(() => {
          setIsPushing(false);
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
        setTimeout(() => {
          setIsPulling(false);
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
    
    const handleCommand = (command: string, result: string, params: any) => {
      if (commandMap[command]) {
        commandMap[command](params);
      } else {
        console.warn("Unknown command received:", command);
      }
    };
    
    registerCommandHandler(handleCommand);
    
    return () => {
      // Cleanup
    };
  }, [executeCommand, setAnimation, registerCommandHandler, position]);

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
        onAnimationComplete={() => {}}
      />
      <CharacterOutfit position={position} animation={currentAnimation} />
      <CharacterHair
        position={position}
        scale={[1, 1, 1]}
        rows={8}
        cols={8}
        animation={currentAnimation}
      />
    </>
  );
};

export default Game;
