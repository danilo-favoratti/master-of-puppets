import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import "./App.css";
import Game from "./components/Game";
import GameUI from "./components/GameUI";

function App() {
  return (
    <div className="game-container">
      <Canvas
        camera={{ position: [0, 0, 10], fov: 50 }}
        style={{ width: "100vw", height: "100vh" }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <OrbitControls enableRotate={false} enableZoom={false} />
          <Game />
        </Suspense>
      </Canvas>

      <GameUI />
    </div>
  );
}

export default App;
