import { useState, useEffect } from 'react';

interface KeyState {
  ArrowUp: boolean;
  ArrowDown: boolean;
  ArrowLeft: boolean;
  ArrowRight: boolean;
  Shift: boolean;
  z: boolean;
  x: boolean;
  ' ': boolean;
}

export const useKeyboardControls = () => {
  const [keys, setKeys] = useState<KeyState>({
    ArrowUp: false,
    ArrowDown: false,
    ArrowLeft: false,
    ArrowRight: false,
    Shift: false,
    z: false,
    x: false,
    ' ': false
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (keys.hasOwnProperty(e.key)) {
        setKeys(prevKeys => ({
          ...prevKeys,
          [e.key]: true
        }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (keys.hasOwnProperty(e.key)) {
        setKeys(prevKeys => ({
          ...prevKeys,
          [e.key]: false
        }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [keys]);

  return keys;
}; 