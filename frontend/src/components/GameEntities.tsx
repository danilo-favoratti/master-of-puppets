import {ThreeEvent} from "@react-three/fiber";
import React from "react";
import {GameEntity} from "../types/entities";
import BedrollSprite from "./entities/BedrollSprite";
import {CampfirePotSprite} from "./entities/CampfirePotSprite";
import CampfireSpitSprite from "./entities/CampfireSpitSprite";
import {CampFireSprite} from "./entities/CampFireSprite";
import {ChestSprite} from "./entities/ChestSprite";
import {NpcEntity} from "./entities/NpcEntity";
import {PigSprite} from "./entities/PigSprite";
import {PotSprite} from "./entities/PotSprite";
import {StatueSprite} from "./entities/StatueSprite";
import TravelersCampSprite from "./entities/TravelersCampSprite";

interface GameEntitiesProps {
  entities: GameEntity[];
  onEntityStateChange?: (entityId: string, newState: string) => void;
  onEntityClick?: (entityId: string, event: React.MouseEvent) => void;
}

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
            state={entity.state}
            variant={entity.variant}
            entity={{
              is_movable: true,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "campfire":
        return (
          <CampFireSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "pig":
        return (
          <PigSprite
            key={entity.id}
            position={entity.position}
            state={entity.state}
            canMove={entity.canMove}
            moveInterval={entity.moveInterval}
            onStateChange={(newState) => {
              if (onEntityStateChange) {
                onEntityStateChange(entity.id, newState);
              }
            }}
            onClick={handleThreeClick(entity.id)}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "chest":
        return (
          <ChestSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            variant={entity.variant}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "tent":
        return (
          <TravelersCampSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            variant={entity.variant}
            entity={{
              is_movable: true,
              is_jumpable: false,
              is_usable_alone: true,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "bedroll":
        return (
          <BedrollSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            entity={{
              is_movable: true,
              is_jumpable: false,
              is_usable_alone: true,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "campfire_spit":
        return (
          <CampfireSpitSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            entity={{
              is_movable: true,
              is_jumpable: false,
              is_usable_alone: true,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "campfire_pot":
        return (
          <CampfirePotSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            entity={{
              is_movable: true,
              is_jumpable: false,
              is_usable_alone: true,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "thief":
        return (
          <NpcEntity
            key={entity.id}
            {...commonProps}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "guard":
        return (
          <NpcEntity
            key={entity.id}
            {...commonProps}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "merchant":
        return (
          <NpcEntity
            key={entity.id}
            {...commonProps}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "hero":
        return (
          <NpcEntity
            key={entity.id}
            {...commonProps}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "wizard":
        return (
          <NpcEntity
            key={entity.id}
            {...commonProps}
            name={entity.name}
            type={entity.type}
            position={entity.position}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );
      case "statue":
        return (
          <StatueSprite
            key={entity.id}
            {...commonProps}
            state={entity.state}
            variant={entity.variant}
            entity={{
              is_movable: false,
              is_jumpable: false,
              is_usable_alone: false,
              is_collectable: false,
              is_wearable: false,
              weight: 1,
              usable_with: [],
              possible_alone_actions: [],
            }}
          />
        );

      default:
        return null;
    }
  };

  return <>{entities.map(renderEntity)}</>;
};

export default GameEntities;
