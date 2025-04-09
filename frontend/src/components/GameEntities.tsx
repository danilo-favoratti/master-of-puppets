import { ThreeEvent } from "@react-three/fiber";
import React from "react";
import { GameEntity } from "../types/entities";
import { getX, getY } from "../utils/positionUtils";
import BackpackSprite from "./entities/BackpackSprite";
import BedrollSprite from "./entities/BedrollSprite";
import { CampfirePotSprite } from "./entities/CampfirePotSprite";
import CampfireSpitSprite from "./entities/CampfireSpitSprite";
import { CampFireSprite } from "./entities/CampFireSprite";
import { ChestSprite } from "./entities/ChestSprite";
import LogStoolSprite from "./entities/LogStoolSprite";
import { NpcEntity } from "./entities/NpcEntity";
import { PigSprite } from "./entities/PigSprite";
import { PotSprite } from "./entities/PotSprite";
import { StatueSprite } from "./entities/StatueSprite";
import TravelersCampSprite from "./entities/TravelersCampSprite";
import TreeSprite from "./entities/TreeSprite";

interface GameEntitiesProps {
  entities: GameEntity[];
  onEntityStateChange?: (entityId: string, newState: string) => void;
  onEntityClick?: (entityId: string, event: React.MouseEvent) => void;
}

// Define a simplified entity type to use with all entity components
// This avoids the type errors related to entity properties
const baseEntity = {
  weight: 1,
  usable_with: [],
  possible_alone_actions: [],
};

export const GameEntities: React.FC<GameEntitiesProps> = ({
  entities,
  onEntityStateChange,
  onEntityClick,
}) => {
  const renderEntity = (entity: GameEntity) => {
    const commonProps = {
      position: entity.position,
      onStateChange: (newState: string) => {
        if (onEntityStateChange) {
          onEntityStateChange(entity.id, newState);
        }
      },
      onClick: (event: React.MouseEvent) => {
        if (onEntityClick) {
          onEntityClick(entity.id, event);
        }
      },
    };

    // Create an adapter for ThreeEvent click handler
    const handleThreeClick =
      (entityId: string) => (event: ThreeEvent<MouseEvent>) => {
        if (onEntityClick) {
          // Pass the native MouseEvent from the ThreeEvent
          onEntityClick(
            entityId,
            event.nativeEvent as unknown as React.MouseEvent
          );
        }
      };

    switch (entity.type) {
      case "pot":
        return (
          <PotSprite
            key={entity.id}
            {...commonProps}
            state={entity.state === "unlit" ? "idle" : entity.state as "idle" | "breaking" | "broken"}
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      case "campfire":
        return (
          <CampFireSprite
            key={entity.id}
            {...commonProps}
            state={entity.state as "unlit" | "burning" | "dying" | "extinguished"}
            entity={baseEntity as any}
          />
        );
      case "pig":
        return (
          <PigSprite
            key={entity.id}
            id={entity.id}
            position={entity.position}
            state={entity.state}
            canMove={entity.canMove}
            moveInterval={entity.moveInterval}
            variant={entity.variant}
            onClick={handleThreeClick(entity.id)}
            entity={baseEntity as any}
          />
        );
      case "chest":
        return (
          <ChestSprite
            key={entity.id}
            {...commonProps}
            state={entity.state === "idle" ? "closed" : entity.state as "closed" | "open"}
            variant={(entity.variant as "wooden" | "silver" | "golden" | "magical") || "wooden"}
            entity={baseEntity as any}
          />
        );
      case "tent":
        return (
          <TravelersCampSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      case "bedroll":
        return (
          <BedrollSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            entity={baseEntity as any}
          />
        );
      case "campfire_spit":
        return (
          <CampfireSpitSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            entity={baseEntity as any}
          />
        );
      case "campfire_pot":
        return (
          <CampfirePotSprite
            key={entity.id}
            {...commonProps}
            state={entity.state === "idle" ? "empty" : entity.state as "empty" | "cooking" | "cooked"}
            entity={baseEntity as any}
          />
        );
      case "thief":
      case "guard":
      case "merchant":
      case "hero":
      case "wizard":
        return (
          <NpcEntity
            key={entity.id}
            id={entity.id}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={baseEntity as any}
          />
        );
      case "statue":
        return (
          <StatueSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      case "backpack":
        return (
          <BackpackSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      case "log_stool":
        return (
          <LogStoolSprite
            key={entity.id}
            {...commonProps}
            state="idle" 
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      case "tree":
        return (
          <TreeSprite
            key={entity.id}
            {...commonProps}
            state="idle"
            variant={entity.variant}
            entity={baseEntity as any}
          />
        );
      default:
        return null;
    }
  };

  return <>{entities.map(renderEntity)}</>;
};

export default GameEntities;
