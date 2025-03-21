"""
Tools for the game character agent.
"""
from typing import Optional, Literal

DirectionType = Literal["left", "right", "up", "down"]

def jump(direction: DirectionType = None) -> str:
    """
    Makes the character jump.
    
    Args:
        direction (str, optional): Direction to jump (left, right, up, down)
        
    Returns:
        str: A description of the jump action
    """
    if direction:
        print(f"Jumping {direction}!")
        return f"*(The character jumps {direction}.)*"
    else:
        print("Jumping!")
        return "*(The character jumps.)*"


def talk(message: str) -> str:
    """
    Makes the character say something.
    
    Args:
        message (str): The message to say
        
    Returns:
        str: A description of the talk action with the message
    """
    print(f"Talking: {message}")
    return f"*(The character says: '{message}')*"


def walk(direction: DirectionType) -> str:
    """
    Makes the character walk in a specific direction.
    
    Args:
        direction (str): Direction to walk (left, right, up, down)
        
    Returns:
        str: A description of the walk action
    """
    print(f"Walking {direction}")
    return f"*(The character walks {direction}.)*"


def run(direction: DirectionType) -> str:
    """
    Makes the character run in a specific direction.
    
    Args:
        direction (str): Direction to run (left, right, up, down)
        
    Returns:
        str: A description of the run action
    """
    print(f"Running {direction}")
    return f"*(The character runs {direction}.)*"


def push(direction: DirectionType) -> str:
    """
    Makes the character push in a specific direction.
    
    Args:
        direction (str): Direction to push (left, right, up, down)
        
    Returns:
        str: A description of the push action
    """
    print(f"Pushing {direction}")
    return f"*(The character pushes {direction}.)*"


def pull(direction: DirectionType) -> str:
    """
    Makes the character pull in a specific direction.
    
    Args:
        direction (str): Direction to pull (left, right, up, down)
        
    Returns:
        str: A description of the pull action
    """
    print(f"Pulling {direction}")
    return f"*(The character pulls {direction}.)*" 