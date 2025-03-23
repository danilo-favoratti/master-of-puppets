# Game Model Architecture

A structured Python model for a 2D grid-based game with objects, containers, and characters that can interact with the environment.

## Core Components

### 1. Entity System
- **Entity**: Base class for anything that can exist on the board (position, ID, name, description)
- **GameObject**: Objects that can be placed on the board with properties like:
  - Movable (can be pushed/pulled)
  - Jumpable (can be jumped over)
  - Usable (can be used with other objects)
- **Container**: Special type of GameObject that can hold other objects
- **Person**: Character that can perform actions like:
  - Walking/running
  - Jumping
  - Pushing/pulling objects
  - Getting/putting items from/into containers
  - Using objects together
  - Looking around
  - Communication

### 2. Board System
- 2D grid with configurable width and height
- Manages entity positions
- Handles movement validation
- Provides methods for querying entities by position or properties

### 3. Game Manager
- Coordinates game flow and state
- Manages turns and actions
- Provides a high-level API for game interactions
- Maintains game log and messages

## Data Flow

1. Game creates and manages a Board
2. Board tracks Entity positions
3. Person interacts with GameObjects through actions
4. Actions return success/failure with messages
5. Game logs messages and updates state

## Usage Example

```python
from model import Game, Position

# Create a game with a 10x10 board
game = Game(width=10, height=10)

# Create player at position (0,0)
player = game.create_player("Adventurer", position=(0, 0))

# Create some objects
key = game.create_object(
    obj_type="item", 
    name="Key", 
    position=(1, 1),
    is_movable=True
)

# Perform actions
result = game.perform_action("walk", position=(1, 0))
print(result["message"])  # "Adventurer walked to (1, 0)"

# Look around
result = game.perform_action("look")
print(result["message"])  # Lists visible objects
```

## Design Principles

1. **Clear Separation of Concerns**:
   - Board manages the physical space
   - Entities represent things in the game
   - Game coordinates high-level flows

2. **Structured Data and Result Patterns**:
   - Actions return dictionary results with success/failure status
   - Consistent message format for user feedback
   - Typed properties and parameters

3. **Extensibility**:
   - Base classes designed for extension
   - Property system allows for flexible object types
   - Action system can be easily expanded 