"""
Tools for the game character to use.
"""

def jump(direction: str = None) -> str:
    """Makes the character jump."""
    if direction:
        return f"Jumped {direction}"
    return "Jumped"

def walk(direction: str) -> str:
    """Makes the character walk in a specific direction."""
    return f"Walked {direction}"

def run(direction: str) -> str:
    """Makes the character run in a specific direction."""
    return f"Ran {direction}"

def push(direction: str) -> str:
    """Makes the character push in a specific direction."""
    return f"Pushed {direction}"

def pull(direction: str) -> str:
    """Makes the character pull in a specific direction."""
    return f"Pulled {direction}" 