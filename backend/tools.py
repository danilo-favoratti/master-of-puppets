"""
Tools for the game character agent.
"""
from typing import Optional


def jump() -> str:
    """
    Makes the character jump.
    
    Returns:
        str: A description of the jump action
    """
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