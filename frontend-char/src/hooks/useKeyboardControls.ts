import { useEffect, useState } from 'react';

export interface KeyMap {
  ArrowUp: boolean;
  ArrowDown: boolean;
  ArrowLeft: boolean;
  ArrowRight: boolean;
  ' ': boolean; // Espaço
  Shift: boolean; // For running
  z: boolean; // For pushing
  x: boolean; // For pulling
}

export const useKeyboardControls = () => {
  const [keys, setKeys] = useState<KeyMap>({
    ArrowUp: false,
    ArrowDown: false,
    ArrowLeft: false,
    ArrowRight: false,
    ' ': false,
    Shift: false,
    z: false,
    x: false
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key in keys) {
        e.preventDefault();
        setKeys(state => ({
          ...state,
          [e.key]: true,
        }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key in keys) {
        e.preventDefault();
        setKeys(state => ({
          ...state,
          [e.key]: false,
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