import numpy as np
from typing import Literal, List, Tuple
import math

# Map configuration
MAP_SIZE = 60
BORDER_SIZE = 15
WATER_LEVEL = 0.5  # Values below this are water, above are land
WATER_SYMBOL = "~~~"
LAND_SYMBOL = "$$$"

def generate_perlin_noise(width: int, height: int, scale: float = 10.0, octaves: int = 6, 
                          persistence: float = 0.5, lacunarity: float = 2.0) -> np.ndarray:
    """
    Generate a 2D Perlin noise map.
    
    Args:
        width: Width of the map
        height: Height of the map
        scale: Scale of the noise (higher = more zoomed out)
        octaves: Number of layers of noise
        persistence: How much each octave contributes
        lacunarity: How much detail is added per octave
        
    Returns:
        2D numpy array of noise values between 0 and 1
    """
    # Initialize empty noise array
    noise_map = np.zeros((height, width))
    
    # Use numpy's random function as a simple noise source
    # In a real implementation, you'd use a proper Perlin noise library
    random_grid = np.random.rand(height, width)
    
    # Simple approximation of noise for demonstration
    # For each coordinate, calculate a weighted sum of surrounding random values
    for y in range(height):
        for x in range(width):
            # Get normalized coordinates
            nx = x / width
            ny = y / height
            
            # Use a weighted average of surrounding points as "noise"
            # This is a very simplified version of noise and not true Perlin noise
            frequency = 1
            amplitude = 1
            noise_value = 0
            
            # Sample points at different frequencies and amplitudes
            for i in range(octaves):
                # Sample index calculation
                sample_x = int((nx * frequency * scale) % width)
                sample_y = int((ny * frequency * scale) % height)
                
                # Get noise value
                noise_value += random_grid[sample_y, sample_x] * amplitude
                
                # Update frequency and amplitude for next octave
                amplitude *= persistence
                frequency *= lacunarity
            
            noise_map[y, x] = noise_value
    
    # Normalize the noise values to [0, 1]
    min_val = np.min(noise_map)
    max_val = np.max(noise_map)
    noise_map = (noise_map - min_val) / (max_val - min_val)
    
    return noise_map

def create_distance_map(width: int, height: int, method: Literal["square_bump", "euclidean"] = "square_bump") -> np.ndarray:
    """
    Create a distance map where the center is 0 and the edges are 1.
    
    Args:
        width: Width of the map
        height: Height of the map
        method: Distance function to use ("square_bump" or "euclidean")
        
    Returns:
        2D numpy array of distance values between 0 and 1
    """
    distance_map = np.zeros((height, width))
    
    for y in range(height):
        for x in range(width):
            # Normalize coordinates to range from -1 to 1
            nx = 2 * x / width - 1
            ny = 2 * y / height - 1
            
            if method == "square_bump":
                # Square bump distance: d = 1 - (1-nx²) * (1-ny²)
                distance_map[y, x] = 1 - (1 - nx**2) * (1 - ny**2)
            else:
                # Euclidean² distance: d = min(1, (nx² + ny²) / sqrt(2))
                distance_map[y, x] = min(1, (nx**2 + ny**2) / math.sqrt(2))
    
    return distance_map

def generate_island_map(size: int = MAP_SIZE, border_size: int = BORDER_SIZE) -> List[List[str]]:
    """
    Generate a map with islands surrounded by water.
    
    Args:
        size: Size of the map (square)
        border_size: Size of the water border
        
    Returns:
        2D list of strings representing the map
    """
    # Generate base noise
    inner_size = size - 2 * border_size
    noise = generate_perlin_noise(inner_size, inner_size)
    
    # Create distance map
    distance = create_distance_map(inner_size, inner_size, "square_bump")
    
    # Apply shaping function (linear interpolation)
    mix = 0.65  # Control how much of the distance affects the final value
    shaped_elevation = np.zeros_like(noise)
    for y in range(inner_size):
        for x in range(inner_size):
            d = distance[y, x]
            e = noise[y, x]
            # Linear interpolation: e = lerp(e, 1-d, mix)
            shaped_elevation[y, x] = e * (1 - mix) + (1 - d) * mix
    
    # Create the final map with water border
    map_grid = []
    for y in range(size):
        row = []
        for x in range(size):
            # If in the border area, it's water
            if (y < border_size or y >= size - border_size or 
                x < border_size or x >= size - border_size):
                row.append(WATER_SYMBOL)
            else:
                # Otherwise, use the shaped elevation
                inner_x = x - border_size
                inner_y = y - border_size
                if shaped_elevation[inner_y, inner_x] >= WATER_LEVEL:
                    row.append(LAND_SYMBOL)
                else:
                    row.append(WATER_SYMBOL)
        map_grid.append(row)
    
    return map_grid

def print_map(map_grid: List[List[str]]) -> None:
    """
    Print the map to the console.
    
    Args:
        map_grid: 2D list of strings representing the map
    """
    for row in map_grid:
        print(" ".join(row))

def generate_map() -> List[List[str]]:
    """
    Generate and return a map with islands surrounded by water.
    
    Returns:
        2D list of strings representing the map
    """
    return generate_island_map()

if __name__ == "__main__":
    # Generate and print a map
    map_grid = generate_map()
    print_map(map_grid) 