import React from "react";

interface LightControlsProps {
  intensity?: number;
  distance?: number;
  decay?: number;
  ambientLightIntensity?: number;
  onIntensityChange: (value: number) => void;
  onDistanceChange: (value: number) => void;
  onDecayChange: (value: number) => void;
  onAmbientLightIntensityChange?: (value: number) => void;
}

const LightControls: React.FC<LightControlsProps> = ({
  intensity = 1,
  distance = 5,
  decay = 2,
  ambientLightIntensity = 0,
  onIntensityChange,
  onDistanceChange,
  onDecayChange,
  onAmbientLightIntensityChange,
}) => {
  return (
    <div className="flex flex-col gap-2 p-2 bg-black/70 rounded-lg">
      <div className="text-white text-sm">Controles de Luz</div>

      {onAmbientLightIntensityChange && (
        <div className="flex flex-col gap-1">
          <label className="text-white text-xs">Luz Ambiente</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={ambientLightIntensity}
            onChange={(e) =>
              onAmbientLightIntensityChange(Number(e.target.value))
            }
            className="w-full"
          />
          <span className="text-white text-xs">
            {ambientLightIntensity?.toFixed(2) || "0.00"}
          </span>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label className="text-white text-xs">Intensidade (Lanterna)</label>
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          value={intensity}
          onChange={(e) => onIntensityChange(Number(e.target.value))}
          className="w-full"
        />
        <span className="text-white text-xs">
          {intensity?.toFixed(1) || "1.0"}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-white text-xs">Distância</label>
        <input
          type="range"
          min="1"
          max="10"
          step="0.5"
          value={distance}
          onChange={(e) => onDistanceChange(Number(e.target.value))}
          className="w-full"
        />
        <span className="text-white text-xs">
          {distance?.toFixed(1) || "5.0"}
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-white text-xs">Decaimento</label>
        <input
          type="range"
          min="0"
          max="5"
          step="0.1"
          value={decay}
          onChange={(e) => onDecayChange(Number(e.target.value))}
          className="w-full"
        />
        <span className="text-white text-xs">{decay?.toFixed(1) || "2.0"}</span>
      </div>
    </div>
  );
};

export default LightControls;
