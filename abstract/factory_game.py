import random
from typing import List, Dict, Any, Tuple, Optional
from colorama import Fore, Back, Style, init
from factory_map import generate_map, MAP_SIZE, BORDER_SIZE, LAND_SYMBOL, WATER_SYMBOL
from factory import create_chest, create_camp, create_land_obstacle, CampfireFactory, BackpackFactory, FirewoodFactory, TentFactory, BedrollFactory, LogStoolFactory, CampfireSpitFactory, CampfirePotFactory, create_pot

# Initialize colorama for Windows
init()

class GameFactory:
    """Factory for generating complete game worlds with maps and objects."""
    
    def __init__(self, map_size: int = MAP_SIZE, border_size: int = BORDER_SIZE):
        """
        Initialize the game factory.
        
        Args:
            map_size: Size of the map (square)
            border_size: Size of the water border
        """
        self.map_size = map_size
        self.border_size = border_size
        self.map_grid = None
        self.objects = {
            "chests": [],
            "camps": [],
            "npcs": [],
            "landmarks": [],
            "obstacles": [],
            "campfires": [],
            "backpacks": [],
            "firewood": [],
            "tents": [],
            "bedrolls": [],
            "log_stools": [],
            "campfire_spits": [],
            "campfire_pots": [],
            "pots": []
        }
        
    def generate_world(self, 
                      chest_count: int = 5, 
                      camp_count: int = 3,
                      npc_count: int = 8,
                      landmark_count: int = 3,
                      obstacle_count: int = 10,
                      campfire_count: int = 4,
                      backpack_count: int = 3,
                      firewood_count: int = 6,
                      tent_count: int = 2,
                      bedroll_count: int = 3,
                      log_stool_count: int = 4,
                      campfire_spit_count: int = 2,
                      campfire_pot_count: int = 2,
                      pot_count: int = 5) -> Dict[str, Any]:
        """
        Generate a complete game world with map and objects.
        
        Args:
            chest_count: Number of chests to place
            camp_count: Number of camps to place
            npc_count: Number of NPCs to place
            landmark_count: Number of landmarks to place
            obstacle_count: Number of land obstacles to place
            campfire_count: Number of campfires to place
            backpack_count: Number of backpacks to place
            firewood_count: Number of firewood to place
            tent_count: Number of tents to place
            bedroll_count: Number of bedrolls to place
            log_stool_count: Number of log stools to place
            campfire_spit_count: Number of campfire spits to place
            campfire_pot_count: Number of campfire pots to place
            pot_count: Number of pots to place
            
        Returns:
            Dict containing the map and placed objects
        """
        # Generate the map
        self.map_grid = generate_map()
        
        # Place objects in order of importance
        self.place_objects("landmarks", landmark_count)
        self.place_objects("obstacles", obstacle_count)
        self.place_objects("camps", camp_count)
        self.place_objects("campfires", campfire_count)
        self.place_objects("tents", tent_count)
        self.place_objects("bedrolls", bedroll_count)
        self.place_objects("log_stools", log_stool_count)
        self.place_objects("campfire_spits", campfire_spit_count)
        self.place_objects("campfire_pots", campfire_pot_count)
        self.place_objects("chests", chest_count)
        self.place_objects("backpacks", backpack_count)
        self.place_objects("firewood", firewood_count)
        self.place_objects("pots", pot_count)
        self.place_objects("npcs", npc_count)
        
        return {
            "map": self.map_grid,
            "objects": self.objects
        }
    
    def create_landmark(self) -> Dict[str, Any]:
        """
        Create a landmark object for the game world.
        
        Returns:
            Dict: A landmark object with attributes
        """
        landmark_types = ["tower", "statue", "ruins", "cave", "shrine", "portal", "monolith"]
        landmark_type = random.choice(landmark_types)
        
        # Randomize if the landmark is special (has unique properties)
        is_special = random.random() < 0.3  # 30% chance of being special
        
        landmark = {
            "type": landmark_type,
            "name": f"{landmark_type.capitalize()}",
            "special": is_special,
            "id": f"landmark_{landmark_type}_{random.randint(1000, 9999)}"
        }
        
        # Add special properties based on type
        if landmark_type == "tower":
            landmark["height"] = random.randint(3, 8)
            landmark["description"] = f"A {landmark['height']}-story high watchtower overlooking the area."
            if is_special:
                landmark["has_treasure"] = True
                landmark["locked"] = random.random() < 0.7  # 70% chance of being locked
                
        elif landmark_type == "statue":
            statue_subjects = ["hero", "king", "queen", "deity", "beast", "ancient_one"]
            landmark["subject"] = random.choice(statue_subjects)
            landmark["description"] = f"A statue of a {landmark['subject'].replace('_', ' ')}."
            if is_special:
                landmark["has_inscription"] = True
                landmark["gives_buff"] = random.random() < 0.5  # 50% chance of giving buff
                
        elif landmark_type == "ruins":
            ruin_types = ["temple", "fortress", "village", "castle", "outpost"]
            landmark["ruin_type"] = random.choice(ruin_types)
            landmark["description"] = f"Ruins of an ancient {landmark['ruin_type']}."
            if is_special:
                landmark["has_hidden_entrance"] = True
                landmark["guarded"] = random.random() < 0.4  # 40% chance of being guarded
                
        elif landmark_type == "cave":
            cave_types = ["small", "large", "deep", "crystal", "dark"]
            landmark["cave_type"] = random.choice(cave_types)
            landmark["description"] = f"A {landmark['cave_type']} cave entrance leading underground."
            if is_special:
                landmark["has_monster"] = random.random() < 0.6  # 60% chance of having monster
                landmark["has_treasure"] = random.random() < 0.7  # 70% chance of having treasure
                
        elif landmark_type == "shrine":
            shrine_types = ["nature", "warrior", "healer", "scholar", "traveler"]
            landmark["shrine_type"] = random.choice(shrine_types)
            landmark["description"] = f"A shrine dedicated to the {landmark['shrine_type']}."
            if is_special:
                landmark["gives_blessing"] = True
                landmark["requires_offering"] = random.random() < 0.5  # 50% chance of requiring offering
                
        elif landmark_type == "portal":
            portal_states = ["active", "dormant", "broken", "unstable"]
            landmark["state"] = random.choice(portal_states)
            landmark["description"] = f"A {landmark['state']} magical portal."
            if is_special:
                landmark["destination"] = "special_location"
                landmark["requires_key"] = random.random() < 0.8  # 80% chance of requiring key
                
        else:  # monolith
            monolith_materials = ["stone", "obsidian", "crystal", "metal", "unknown"]
            landmark["material"] = random.choice(monolith_materials)
            landmark["description"] = f"A towering monolith made of {landmark['material']}."
            if is_special:
                landmark["has_inscriptions"] = True
                landmark["magical"] = random.random() < 0.9  # 90% chance of being magical
                
        return landmark
    
    def create_npc(self) -> Dict[str, Any]:
        """
        Create an NPC for the game world.
        
        Returns:
            Dict: An NPC object with attributes
        """
        npc_types = ["villager", "hero", "merchant", "guard", "wizard", "monk", "thief"]
        npc_type = random.choice(npc_types)
        
        # Basic states
        states = ["idle", "walking", "sleeping", "working", "eating"]
        
        # Type-specific states
        type_states = {
            "villager": ["farming", "chatting", "crafting"],
            "hero": ["training", "resting", "negotiating"],
            "merchant": ["selling", "bargaining", "counting_coins"],
            "guard": ["patrolling", "watching", "fighting"],
            "wizard": ["studying", "brewing", "casting"],
            "monk": ["meditating", "teaching", "healing"],
            "thief": ["sneaking", "hiding", "stealing"]
        }
        
        # Combine basic states with type-specific states
        all_states = states + type_states.get(npc_type, [])
        state = random.choice(all_states)
        
        # Determine if hostile based on type (thieves more likely to be hostile)
        hostile_chance = {
            "thief": 0.7,
            "wizard": 0.3,
            "guard": 0.2,
            "hero": 0.1,
            "monk": 0.05,
            "merchant": 0.05,
            "villager": 0.02
        }
        is_hostile = random.random() < hostile_chance.get(npc_type, 0.1)
        
        # Create the NPC
        npc = {
            "id": f"npc_{npc_type}_{random.randint(1000, 9999)}",
            "type": npc_type,
            "name": f"{npc_type.capitalize()}",  # Could be expanded with name generation
            "level": random.randint(1, 5),
            "state": state,
            "hostile": is_hostile,
            "inventory": []
        }
        
        # Add some random items to inventory
        possible_items = ["potion", "food", "coin", "tool", "weapon", "clothing"]
        inventory_size = random.randint(0, 3)
        
        for _ in range(inventory_size):
            item_type = random.choice(possible_items)
            quantity = random.randint(1, 3)
            npc["inventory"].append({
                "type": item_type,
                "quantity": quantity,
                "id": f"item_{item_type}_{random.randint(1000, 9999)}"
            })
            
        return npc
        
    def place_objects(self, object_type: str, count: int) -> None:
        """
        Place objects randomly on land tiles.
        
        Args:
            object_type: Type of object to place 
            count: Number of objects to place
        """
        # Reset the objects list for this type
        self.objects[object_type] = []
        
        # Find all land tiles
        land_tiles = []
        for y in range(self.map_size):
            for x in range(self.map_size):
                if y < self.border_size or y >= self.map_size - self.border_size or \
                   x < self.border_size or x >= self.map_size - self.border_size:
                    continue
                
                # Check if the tile is land
                if self.map_grid[y][x] == "$$$":
                    # Check if the tile is already occupied by another object
                    occupied = False
                    for obj_type, obj_list in self.objects.items():
                        for obj in obj_list:
                            if obj["position"] == (x, y):
                                occupied = True
                                break
                        if occupied:
                            break
                    
                    if not occupied:
                        land_tiles.append((x, y))
        
        # Shuffle the land tiles
        random.shuffle(land_tiles)
        
        # Place objects on the first 'count' land tiles
        for i in range(min(count, len(land_tiles))):
            x, y = land_tiles[i]
            
            # Create the object
            if object_type == "chests":
                obj = create_chest()
            elif object_type == "camps":
                obj = create_camp()
            elif object_type == "npcs":
                obj = self.create_npc()
            elif object_type == "landmarks":
                obj = self.create_landmark()
            elif object_type == "obstacles":
                obj = create_land_obstacle()
            elif object_type == "campfires":
                obj = CampfireFactory.create_campfire("unlit")
            elif object_type == "backpacks":
                obj = BackpackFactory.create_backpack()
            elif object_type == "firewood":
                obj = FirewoodFactory.create_firewood()
            elif object_type == "tents":
                obj = TentFactory.create_tent()
            elif object_type == "bedrolls":
                obj = BedrollFactory.create_bedroll()
            elif object_type == "log_stools":
                obj = LogStoolFactory.create_stool()
            elif object_type == "campfire_spits":
                obj = CampfireSpitFactory.create_campfire_spit()
            elif object_type == "campfire_pots":
                obj = CampfirePotFactory.create_pot("tripod")
            elif object_type == "pots":
                obj = create_pot()
            else:
                continue
            
            # Add position to the object
            obj["position"] = (x, y)
            
            # Add to the objects list
            self.objects[object_type].append(obj)

    def print_world(self) -> None:
        """
        Print the game world with colored text representation.
        Each tile is represented by 3 characters.
        """
        if not self.map_grid:
            print("No world generated yet. Call generate_world() first.")
            return
        
        # Create a copy of the map grid for display
        display_grid = [row[:] for row in self.map_grid]
        
        # Place objects on the display grid in order of visibility (layering)
        
        # First obstacles and landmarks (lowest layer above terrain)
        for obstacle in self.objects["obstacles"]:
            x, y = obstacle["position"]
            display_grid[y][x] = "OBS"
            
        for landmark in self.objects["landmarks"]:
            x, y = landmark["position"]
            if landmark["type"] == "tower":
                display_grid[y][x] = "TWR"
            elif landmark["type"] == "statue":
                display_grid[y][x] = "STA"
            elif landmark["type"] == "ruins":
                display_grid[y][x] = "RUI"
            elif landmark["type"] == "cave":
                display_grid[y][x] = "CAV"
            elif landmark["type"] == "shrine":
                display_grid[y][x] = "SHR"
            elif landmark["type"] == "portal":
                display_grid[y][x] = "PRT"
            else:  # monolith
                display_grid[y][x] = "MON"
        
        # Add pots to the display grid
        for pot in self.objects["pots"]:
            x, y = pot["position"]
            if pot["size"] == "small":
                display_grid[y][x] = "SPT"
            elif pot["size"] == "medium":
                display_grid[y][x] = "MPT"
            else:  # big
                display_grid[y][x] = "BPT"
        
        # Then camps and camp-related items
        for camp in self.objects["camps"]:
            x, y = camp["position"]
            
            if camp["type"] == "bandit":
                display_grid[y][x] = "BND"
            elif camp["type"] == "traveler":
                display_grid[y][x] = "TRV"
            elif camp["type"] == "merchant":
                display_grid[y][x] = "MRC"
            elif camp["type"] == "military":
                display_grid[y][x] = "MIL"
            else:  # abandoned
                display_grid[y][x] = "ABD"
                
        for campfire in self.objects["campfires"]:
            x, y = campfire["position"]
            display_grid[y][x] = "CFR"
            
        for tent in self.objects["tents"]:
            x, y = tent["position"]
            display_grid[y][x] = "TNT"
            
        for bedroll in self.objects["bedrolls"]:
            x, y = bedroll["position"]
            display_grid[y][x] = "BDR"
            
        for log_stool in self.objects["log_stools"]:
            x, y = log_stool["position"]
            display_grid[y][x] = "LST"
            
        for campfire_spit in self.objects["campfire_spits"]:
            x, y = campfire_spit["position"]
            display_grid[y][x] = "CSP"
            
        for campfire_pot in self.objects["campfire_pots"]:
            x, y = campfire_pot["position"]
            display_grid[y][x] = "CPT"
            
        for firewood in self.objects["firewood"]:
            x, y = firewood["position"]
            display_grid[y][x] = "FWD"
        
        # Then chests and backpacks
        for chest in self.objects["chests"]:
            x, y = chest["position"]
            
            if chest["type"] == "wooden":
                display_grid[y][x] = "CHW"
            elif chest["type"] == "silver":
                display_grid[y][x] = "CHS"
            elif chest["type"] == "golden":
                display_grid[y][x] = "CHG" 
            else:  # magical
                display_grid[y][x] = "CHM"
                
        for backpack in self.objects["backpacks"]:
            x, y = backpack["position"]
            display_grid[y][x] = "BPK"
        
        # Finally NPCs (top layer)
        for npc in self.objects["npcs"]:
            x, y = npc["position"]
            
            if npc["type"] == "villager":
                display_grid[y][x] = "VIL"
            elif npc["type"] == "hero":
                display_grid[y][x] = "HRO"
            elif npc["type"] == "merchant":
                display_grid[y][x] = "MER"
            elif npc["type"] == "guard":
                display_grid[y][x] = "GRD"
            elif npc["type"] == "wizard":
                display_grid[y][x] = "WIZ"
            elif npc["type"] == "monk":
                display_grid[y][x] = "MNK"
            else:  # thief
                display_grid[y][x] = "THF"
        
        # Count land tiles
        land_count = sum(1 for row in self.map_grid for tile in row if tile == "$$$")
        water_count = self.map_size * self.map_size - land_count
        
        # Print world summary
        print("\n== WORLD SUMMARY ==")
        print(f"Size: {self.map_size}x{self.map_size}")
        print(f"Land tiles: {land_count} ({land_count / (self.map_size * self.map_size) * 100:.1f}%)")
        print(f"Water tiles: {water_count} ({water_count / (self.map_size * self.map_size) * 100:.1f}%)")
        print(f"Objects: {sum(len(obj_list) for obj_list in self.objects.values())}")
        
        # Print the legend
        print("\n== WORLD MAP LEGEND ==")
        print(f"{Fore.BLUE}{Back.CYAN}~~~{Style.RESET_ALL} Water")
        print(f"{Fore.GREEN}{Back.BLACK}$$${Style.RESET_ALL} Land")
        print(f"{Fore.YELLOW}{Back.BLACK}CHW{Style.RESET_ALL} Wooden Chest   {Fore.YELLOW}{Back.BLACK}CHS{Style.RESET_ALL} Silver Chest   "
              f"{Fore.YELLOW}{Back.BLACK}CHG{Style.RESET_ALL} Golden Chest   {Fore.YELLOW}{Back.BLACK}CHM{Style.RESET_ALL} Magical Chest")
        print(f"{Fore.YELLOW}{Back.BLACK}BPK{Style.RESET_ALL} Backpack")
        print(f"{Fore.RED}{Back.BLACK}BND{Style.RESET_ALL} Bandit Camp   {Fore.RED}{Back.BLACK}TRV{Style.RESET_ALL} Traveler Camp   "
              f"{Fore.RED}{Back.BLACK}MRC{Style.RESET_ALL} Merchant Camp   {Fore.RED}{Back.BLACK}ABD{Style.RESET_ALL} Abandoned Camp")
        print(f"{Fore.RED}{Back.BLACK}CFR{Style.RESET_ALL} Campfire   {Fore.RED}{Back.BLACK}TNT{Style.RESET_ALL} Tent   "
              f"{Fore.RED}{Back.BLACK}BDR{Style.RESET_ALL} Bedroll   {Fore.RED}{Back.BLACK}LST{Style.RESET_ALL} Log Stool")
        print(f"{Fore.RED}{Back.BLACK}CSP{Style.RESET_ALL} Campfire Spit   {Fore.RED}{Back.BLACK}CPT{Style.RESET_ALL} Campfire Pot   "
              f"{Fore.RED}{Back.BLACK}FWD{Style.RESET_ALL} Firewood")
        print(f"{Fore.MAGENTA}{Back.BLACK}TWR{Style.RESET_ALL} Tower   {Fore.MAGENTA}{Back.BLACK}STA{Style.RESET_ALL} Statue   "
              f"{Fore.MAGENTA}{Back.BLACK}RUI{Style.RESET_ALL} Ruins   {Fore.MAGENTA}{Back.BLACK}CAV{Style.RESET_ALL} Cave")
        print(f"{Fore.MAGENTA}{Back.BLACK}OBS{Style.RESET_ALL} Obstacle")
        print(f"{Fore.GREEN}{Back.BLACK}SPT{Style.RESET_ALL} Small Pot   {Fore.GREEN}{Back.BLACK}MPT{Style.RESET_ALL} Medium Pot   "
              f"{Fore.GREEN}{Back.BLACK}BPT{Style.RESET_ALL} Big Pot")
        print(f"{Fore.CYAN}{Back.BLACK}VIL{Style.RESET_ALL} Villager   {Fore.CYAN}{Back.BLACK}HRO{Style.RESET_ALL} Hero   "
              f"{Fore.CYAN}{Back.BLACK}WIZ{Style.RESET_ALL} Wizard   {Fore.CYAN}{Back.BLACK}MER{Style.RESET_ALL} Merchant")
        print("=====================\n")
        
        # Print the map with colors
        for y in range(self.map_size):
            row = ""
            for x in range(self.map_size):
                tile = display_grid[y][x]
                
                if tile == "~~~":  # Water
                    row += f"{Fore.BLUE}{Back.CYAN}~~~{Style.RESET_ALL}"
                elif tile == "$$$":  # Land
                    row += f"{Fore.GREEN}{Back.BLACK}$$$"
                
                # Chests and backpacks (yellow)
                elif tile in ["CHW", "CHS", "CHG", "CHM", "BPK"]:
                    row += f"{Fore.YELLOW}{Back.BLACK}{tile}"
                
                # Camps and camp items (red)
                elif tile in ["BND", "TRV", "MRC", "ABD", "MIL", "CFR", "TNT", "BDR", "LST", "CSP", "CPT", "FWD"]:
                    row += f"{Fore.RED}{Back.BLACK}{tile}"
                
                # Landmarks and obstacles (magenta)
                elif tile in ["TWR", "STA", "RUI", "CAV", "SHR", "PRT", "MON", "OBS"]:
                    row += f"{Fore.MAGENTA}{Back.BLACK}{tile}"
                
                # Pots (green)
                elif tile in ["SPT", "MPT", "BPT"]:
                    row += f"{Fore.GREEN}{Back.BLACK}{tile}"
                
                # NPCs (cyan)
                elif tile in ["VIL", "HRO", "MER", "GRD", "WIZ", "MNK", "THF"]:
                    row += f"{Fore.CYAN}{Back.BLACK}{tile}"
                
                else:
                    row += f"{Style.RESET_ALL}{tile}"
                
                # Add a space between tiles for better readability
                row += " "
            
            print(row + Style.RESET_ALL)
        
        # Print object details
        print(f"\nGame World Generated:")
        
        # Print chests
        print(f"- {len(self.objects['chests'])} chests")
        for i, chest in enumerate(self.objects['chests']):
            chest_type = chest['type'].capitalize()
            contents = ', '.join([f"{item['quantity']}× {item['name']}" for item in chest['contents'][:2]])
            if len(chest['contents']) > 2:
                contents += f", and {len(chest['contents']) - 2} more items"
            print(f"  {i+1}. {chest_type} chest {Fore.YELLOW}({chest['position'][0]},{chest['position'][1]}){Style.RESET_ALL}: {contents}")
        
        # Print backpacks
        print(f"- {len(self.objects['backpacks'])} backpacks")
        for i, backpack in enumerate(self.objects['backpacks']):
            capacity = backpack.get('capacity', 'Unknown')
            color = backpack.get('color', 'Unknown')
            print(f"  {i+1}. {color} backpack {Fore.YELLOW}({backpack['position'][0]},{backpack['position'][1]}){Style.RESET_ALL}: {capacity} capacity")
        
        # Print camps
        print(f"- {len(self.objects['camps'])} camps")
        for i, camp in enumerate(self.objects['camps']):
            occupants = len(camp['occupants'])
            camp_type = camp['type'].capitalize()
            size = camp['size'].capitalize()
            print(f"  {i+1}. {size} {camp_type} camp {Fore.RED}({camp['position'][0]},{camp['position'][1]}){Style.RESET_ALL}: {occupants} occupants, {len(camp['structures'])} structures")
        
        # Print camp items
        for item_type, color_code in [
            ('campfires', Fore.RED),
            ('tents', Fore.RED),
            ('bedrolls', Fore.RED),
            ('log_stools', Fore.RED),
            ('campfire_spits', Fore.RED),
            ('campfire_pots', Fore.RED),
            ('firewood', Fore.RED)
        ]:
            if len(self.objects[item_type]) > 0:
                item_name = item_type.replace('_', ' ')
                print(f"- {len(self.objects[item_type])} {item_name}")
                for i, item in enumerate(self.objects[item_type]):
                    quality = item.get('quality', 'standard').capitalize()
                    print(f"  {i+1}. {quality} {item_name[:-1]} {color_code}({item['position'][0]},{item['position'][1]}){Style.RESET_ALL}")
        
        # Print pots
        if len(self.objects['pots']) > 0:
            print(f"- {len(self.objects['pots'])} pots")
            for i, pot in enumerate(self.objects['pots']):
                size = pot['size'].capitalize()
                state = pot['state'].capitalize()
                durability = pot.get('durability', 'Unknown')
                max_durability = pot.get('max_durability', 'Unknown')
                durability_info = f"{durability}/{max_durability}" if durability != 'Unknown' else ''
                print(f"  {i+1}. {size} Vase ({state}) {Fore.GREEN}({pot['position'][0]},{pot['position'][1]}){Style.RESET_ALL}: " +
                     f"Capacity: {pot.get('capacity', 'Unknown')}, Durability: {durability_info}")
        
        # Print landmarks and obstacles
        print(f"- {len(self.objects['landmarks'])} landmarks")
        for i, landmark in enumerate(self.objects['landmarks']):
            landmark_type = landmark['type'].capitalize()
            special = " (Special)" if landmark.get('special', False) else ""
            print(f"  {i+1}. {landmark_type}{special} {Fore.MAGENTA}({landmark['position'][0]},{landmark['position'][1]}){Style.RESET_ALL}")
            
        print(f"- {len(self.objects['obstacles'])} obstacles")
        for i, obstacle in enumerate(self.objects['obstacles']):
            obstacle_type = obstacle['type'].capitalize() if 'type' in obstacle else 'Generic'
            print(f"  {i+1}. {obstacle_type} obstacle {Fore.MAGENTA}({obstacle['position'][0]},{obstacle['position'][1]}){Style.RESET_ALL}")
        
        # Print NPCs
        print(f"- {len(self.objects['npcs'])} NPCs")
        for i, npc in enumerate(self.objects['npcs']):
            npc_type = npc['type'].capitalize()
            status = "Hostile" if npc.get('hostile', False) else "Friendly"
            print(f"  {i+1}. Level {npc['level']} {npc_type} {Fore.CYAN}({npc['position'][0]},{npc['position'][1]}){Style.RESET_ALL}: {status}, {npc['state'].capitalize()}")

    def export_world_json(self) -> Dict[str, Any]:
        """
        Export the game world as a JSON-serializable dictionary.
        
        Returns:
            Dict containing all map and object information.
        """
        if not self.map_grid:
            return {"error": "No world generated yet. Call generate_world() first."}
        
        # Count land and water tiles
        land_count = sum(1 for row in self.map_grid for tile in row if tile == LAND_SYMBOL)
        water_count = self.map_size * self.map_size - land_count
        
        # Convert map grid to 0s and 1s (water = 0, land = 1)
        grid = []
        for row in self.map_grid:
            grid_row = []
            for cell in row:
                grid_row.append(1 if cell == "$$$" else 0)
            grid.append(grid_row)
        
        # Create the world data dictionary
        world_data = {
            "map": {
                "size": self.map_size,
                "border_size": self.border_size,
                "grid": grid,
                "statistics": {
                    "land_tiles": land_count,
                    "water_tiles": water_count,
                    "land_percentage": land_count / (self.map_size * self.map_size) * 100
                }
            },
            "objects": self.objects,
            "total_object_count": sum(len(obj_list) for obj_list in self.objects.values())
        }
        
        return world_data

    def export_world_ui_json(self) -> Dict[str, Any]:
        """
        Export the game world in UI-friendly format.
        
        Returns:
            Dict containing map and entities in UI format
        """
        if not self.map_grid:
            return {"error": "No world generated yet. Call generate_world() first."}
            
        # Convert map grid to 0s and 1s (water = 0, land = 1)
        ui_grid = []
        for row in self.map_grid:
            grid_row = []
            for cell in row:
                grid_row.append(1 if cell == "$$$" else 0)
            ui_grid.append(grid_row)
            
        # Convert objects to entities
        entities = []
        
        # Convert NPCs
        for npc in self.objects["npcs"]:
            entities.append({
                "id": npc["id"],
                "type": npc["type"],
                "name": npc["name"],
                "position": {"x": npc["position"][0], "y": npc["position"][1]},
                "state": "idle" + ("Down" if random.random() < 0.5 else "Up"),
                "canMove": True,
                "moveInterval": random.randint(2000, 4000),
                "variant": str(random.randint(1, 3)),
                "isMovable": True,
                "isJumpable": False,
                "isUsableAlone": False,
                "isCollectable": False,
                "isWearable": False,
                "weight": 1,
                "level": npc.get("level", 1),
                "hostile": npc.get("hostile", False),
                "inventory": npc.get("inventory", [])
            })
            
        # Convert campfires
        for i, campfire in enumerate(self.objects["campfires"]):
            entities.append({
                "id": f"campfire-{i+1}",
                "type": "campfire",
                "name": "Camp Fire",
                "position": {"x": campfire["position"][0], "y": campfire["position"][1]},
                "state": campfire["state"],
                "variant": "1",
                "isMovable": False,
                "isJumpable": True,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 5,
                "possibleActions": ["light", "extinguish"],
                "description": campfire.get("description", "A place to cook and keep warm.")
            })
            
        # Convert pots
        for i, pot in enumerate(self.objects["pots"]):
            entities.append({
                "id": f"pot-{i+1}",
                "type": "pot",
                "name": "Pot",
                "position": {"x": pot["position"][0], "y": pot["position"][1]},
                "state": pot.get("state", "idle"),
                "variant": "1",
                "isMovable": pot.get("is_movable", True),
                "isJumpable": pot.get("is_jumpable", False),
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": pot.get("weight", 3),
                "capacity": pot.get("capacity", 5),
                "durability": pot.get("durability", 100),
                "maxDurability": pot.get("max_durability", 100),
                "size": pot.get("size", "medium"),
                "description": pot.get("description", "A container that can hold items.")
            })

        # Convert chests
        for i, chest in enumerate(self.objects["chests"]):
            entities.append({
                "id": chest.get("id", f"chest-{i+1}"),
                "type": "chest",
                "name": f"{chest['type'].capitalize()} Chest",
                "position": {"x": chest["position"][0], "y": chest["position"][1]},
                "state": "closed" if chest.get("locked", False) else "open",
                "variant": chest["type"],
                "isMovable": False,
                "isJumpable": False,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 10,
                "locked": chest.get("locked", False),
                "lockType": chest.get("lock_type", None),
                "contents": chest.get("contents", []),
                "description": chest.get("description", "A container for storing valuable items.")
            })

        # Convert landmarks
        for landmark in self.objects["landmarks"]:
            entities.append({
                "id": landmark["id"],
                "type": landmark["type"],
                "name": landmark["name"],
                "position": {"x": landmark["position"][0], "y": landmark["position"][1]},
                "state": landmark.get("state", "idle"),
                "variant": "1",
                "isMovable": False,
                "isJumpable": False,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 100,
                "special": landmark.get("special", False),
                "description": landmark.get("description", "A notable location."),
                "properties": {k: v for k, v in landmark.items() if k not in ["id", "type", "name", "position", "state", "special", "description"]}
            })

        # Convert camp items (tents, bedrolls, log stools, etc.)
        for item_type in ["tents", "bedrolls", "log_stools", "campfire_spits", "campfire_pots", "firewood"]:
            for i, item in enumerate(self.objects[item_type]):
                base_name = item_type[:-1].replace("_", " ").title()
                entities.append({
                    "id": item.get("id", f"{item_type[:-1]}-{i+1}"),
                    "type": item_type[:-1],
                    "name": f"{item.get('quality', 'Standard')} {base_name}",
                    "position": {"x": item["position"][0], "y": item["position"][1]},
                    "state": item.get("state", "idle"),
                    "variant": "1",
                    "isMovable": item.get("is_movable", True),
                    "isJumpable": item.get("is_jumpable", False),
                    "isUsableAlone": item.get("is_usable_alone", True),
                    "isCollectable": item.get("is_collectable", False),
                    "isWearable": item.get("is_wearable", False),
                    "weight": item.get("weight", 2),
                    "quality": item.get("quality", "standard"),
                    "durability": item.get("durability", 100),
                    "maxDurability": item.get("max_durability", 100),
                    "description": item.get("description", f"A {base_name.lower()} that can be used in camp.")
                })
            
        return {
            "map": {
                "size": self.map_size,
                "border_size": self.border_size,
                "grid": ui_grid
            },
            "entities": entities
        }

def create_game(map_size: int = MAP_SIZE, 
                border_size: int = BORDER_SIZE,
                chest_count: int = 5,
                camp_count: int = 3,
                obstacle_count: int = 10,
                campfire_count: int = 4,
                backpack_count: int = 3,
                firewood_count: int = 6,
                tent_count: int = 2,
                bedroll_count: int = 3,
                log_stool_count: int = 4,
                campfire_spit_count: int = 2,
                campfire_pot_count: int = 2,
                pot_count: int = 5) -> Dict[str, Any]:
    """
    Create a complete game world.
    
    Args:
        map_size: Size of the map (square)
        border_size: Size of the water border
        chest_count: Number of chests to place
        camp_count: Number of camps to place
        obstacle_count: Number of land obstacles to place
        campfire_count: Number of campfires to place
        backpack_count: Number of backpacks to place
        firewood_count: Number of firewood to place
        tent_count: Number of tents to place
        bedroll_count: Number of bedrolls to place
        log_stool_count: Number of log stools to place
        campfire_spit_count: Number of campfire spits to place
        campfire_pot_count: Number of campfire pots to place
        pot_count: Number of pots to place
        
    Returns:
        Dict containing the map and placed objects
    """
    factory = GameFactory(map_size, border_size)
    world = factory.generate_world(
        chest_count=chest_count, 
        camp_count=camp_count,
        obstacle_count=obstacle_count,
        campfire_count=campfire_count,
        backpack_count=backpack_count,
        firewood_count=firewood_count,
        tent_count=tent_count,
        bedroll_count=bedroll_count,
        log_stool_count=log_stool_count,
        campfire_spit_count=campfire_spit_count,
        campfire_pot_count=campfire_pot_count,
        pot_count=pot_count
    )
    return world

if __name__ == "__main__":
    # Create a game factory
    factory = GameFactory()
    
    # Generate a world with all object types
    world = factory.generate_world(
        chest_count=8, 
        camp_count=4, 
        npc_count=10, 
        landmark_count=5,
        obstacle_count=12,
        campfire_count=6,
        backpack_count=5,
        firewood_count=8,
        tent_count=4,
        bedroll_count=5,
        log_stool_count=6,
        campfire_spit_count=3,
        campfire_pot_count=3,
        pot_count=6
    )
    
    # Print the world
    factory.print_world()
    
    # Print and save JSON representations
    import json
    from datetime import datetime
    
    # Generate timestamp and filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_filename = f"{timestamp}-map.json"
    ui_filename = f"{timestamp}-ui.json"
    
    # Save original map JSON
    world_json = factory.export_world_json()
    print("\nJSON representation of the world:")
    print(json.dumps(world_json, indent=2))
    
    with open(map_filename, 'w') as f:
        json.dump(world_json, f, indent=2)
    print(f"\nMap saved to: {map_filename}")
    
    # Save UI JSON
    ui_json = factory.export_world_ui_json()
    print("\nUI JSON representation of the world:")
    print(json.dumps(ui_json, indent=2))
    
    with open(ui_filename, 'w') as f:
        json.dump(ui_json, f, indent=2)
    print(f"UI map saved to: {ui_filename}") 