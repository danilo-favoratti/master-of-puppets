# Add a router to direct messages to the appropriate agent
from agents import Runner

from old.agent_copywriter import CopywriterAgent
from agent_puppet_master import GameState, create_puppet_master
from game_object import Container
from simple_cli_game import GameBoard


class GameSession:
    def __init__(self):
        self.copywriter_agent = CopywriterAgent()
        self.path_researcher = None  # Initialize when needed
        self.puppet_master = None  # Initialize when needed
        self.game_state = None  # Will be populated after map creation
        self.current_agent = "copywriter"  # Start with copywriter

    async def process_message(self, message_data):
        """Route messages to the appropriate agent based on game state"""

        if "theme:" in message_data.get("content", "").lower():
            # Theme selection always goes to copywriter
            response, _ = await self.copywriter_agent.process_user_input(message_data["content"])

            # If map was created, initialize game state
            if response.get("type") == "map_created" and self.copywriter_agent.game_context.environment:
                # Initialize game state with map data
                self.game_state = GameState()
                self.game_state.game_board = self._create_game_board_from_map(
                    self.copywriter_agent.game_context.environment["map_data"]
                )

                # Initialize other agents that need the game state
                self.puppet_master = create_puppet_master("Game Character")

                # Switch to storyteller mode
                self.current_agent = "storyteller"

            return response

        # Handle audio messages (binary data)
        if isinstance(message_data, bytes):
            # Process audio through appropriate agent
            if self.current_agent == "storyteller" and hasattr(self.puppet_master, "process_audio"):
                return await self.puppet_master.process_audio(message_data)
            else:
                return await self.copywriter_agent.process_audio(message_data)

        # For established game, route based on message content
        if self.current_agent == "copywriter":
            return await self.copywriter_agent.process_user_input(message_data["content"])
        elif self.current_agent == "storyteller":
            # In a real implementation, this would be handled by a Storyteller agent
            # For now we'll just use the puppet master
            return await self._process_storyteller_message(message_data["content"])

    async def _process_storyteller_message(self, message):
        """Process messages in storyteller mode"""
        # This would integrate with an actual Storyteller agent
        # For now, it will just pass commands to the puppet master

        # Simple command parsing logic
        if any(cmd in message.lower() for cmd in ["move", "walk", "go"]):
            # Extract direction
            directions = ["up", "down", "left", "right"]
            direction = next((d for d in directions if d in message.lower()), "down")

            # Use puppet master to execute movement
            result = await Runner.run(
                starting_agent=self.puppet_master,
                input=f"move {direction}",
                context=self.game_state
            )
            return {"type": "command", "name": "move", "result": result.final_output,
                    "params": {"direction": direction}}

        # Default response if no command is detected
        return {"type": "text", "content": "I'm your guide in this world. What would you like to do?"}

    def _create_game_board_from_map(self, map_data):
        """Convert map data to game board format"""
        # Implementation would depend on your specific data structures
        # This is a simplified placeholder
        game_board = GameBoard()

        # Process entities from map_data
        if "entities" in map_data:
            for entity_data in map_data["entities"]:
                entity = self._create_entity_from_data(entity_data)
                if entity:
                    game_board.add_entity(entity)

        return game_board

    def _create_entity_from_data(self, entity_data):
        """Create game entity from data"""
        # Implementation would depend on your entity structure
        # This is a simplified placeholder
        if "type" not in entity_data:
            return None

        if entity_data["type"] == "chest":
            return Container(
                id=entity_data.get("id", f"chest_{uuid.uuid4()}"),
                name=entity_data.get("name", "Chest"),
                description=entity_data.get("description", "A wooden chest"),
                is_open=False
            )
        # Other entity types...

        return None
