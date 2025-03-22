"""
Debug script to check TensorFlow installation and compatibility.
"""
import sys
print(f"Python version: {sys.version}")

try:
    import tensorflow as tf
    print(f"TensorFlow version: {tf.__version__}")
    
    # Check if contrib is available
    try:
        import tensorflow.contrib
        print("tensorflow.contrib is available")
    except ImportError as e:
        print(f"tensorflow.contrib not available: {e}")
    
    # Check specific modules
    try:
        import tensorflow.contrib.distributions
        print("tensorflow.contrib.distributions is available")
    except ImportError as e:
        print(f"tensorflow.contrib.distributions not available: {e}")
    
except ImportError as e:
    print(f"Failed to import TensorFlow: {e}")

try:
    from agents import Agent, function_tool
    print("Successfully imported agents.Agent and function_tool")
except ImportError as e:
    print(f"Failed to import from agents: {e}") 