"""
OpenAI Agent setup for the game character.
"""
import os
from typing import Dict, Any, List

from openai import OpenAI
from tools import jump, talk, walk, run, push, pull


def setup_agent(api_key: str):
    """
    Set up the OpenAI agent with the character's personality and tools.
    
    Args:
        api_key (str): OpenAI API key
        
    Returns:
        OpenAI Assistant instance
    """
    # Create OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Define the character's personality in the system prompt
    system_prompt = """
    You are a funny, ironic, non-binary videogame character with a witty personality. 
    Your responses should be concise, entertaining, and reflect your unique personality.
    When users give you commands or ask questions, you can respond in two ways:
    1. With a simple text response when having a conversation
    2. By using one of your available tools/actions when asked to perform specific tasks
    
    You can perform various movement actions in different directions (left, right, up, down).
    For example, if someone asks you to "jump up" or "walk to the left", use the appropriate
    directional action.
    
    Keep your responses brief and entertaining!
    """
    
    # Create a new assistant with the tools
    assistant = client.beta.assistants.create(
        name="Game Character",
        instructions=system_prompt,
        tools=[
            {"type": "function", "function": {"name": "jump", "description": "Makes the character jump", 
                                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                           "required": []}}},
            {"type": "function", "function": {"name": "talk", "description": "Makes the character say something", 
                                             "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, 
                                                           "required": ["message"]}}},
            {"type": "function", "function": {"name": "walk", "description": "Makes the character walk in a specific direction", 
                                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                           "required": ["direction"]}}},
            {"type": "function", "function": {"name": "run", "description": "Makes the character run in a specific direction", 
                                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                           "required": ["direction"]}}},
            {"type": "function", "function": {"name": "push", "description": "Makes the character push in a specific direction", 
                                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                           "required": ["direction"]}}},
            {"type": "function", "function": {"name": "pull", "description": "Makes the character pull in a specific direction", 
                                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                           "required": ["direction"]}}}
        ],
        model="gpt-4o"
    )
    
    return {"client": client, "assistant": assistant}


def process_user_input(agent_data: Dict, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process user input through the agent, invoking tools if needed.
    
    Args:
        agent_data (Dict): The configured agent data (client and assistant)
        user_input (str): User message to process
        conversation_history (List[Dict[str, Any]], optional): Previous conversation history
        
    Returns:
        Dict[str, Any]: Response containing text and/or command information
    """
    client = agent_data["client"]
    assistant = agent_data["assistant"]
    
    if conversation_history is None:
        conversation_history = []
    
    # Create a new thread if we don't have one yet
    if "thread_id" not in agent_data:
        thread = client.beta.threads.create()
        agent_data["thread_id"] = thread.id
    
    # Add the user message to the thread
    client.beta.threads.messages.create(
        thread_id=agent_data["thread_id"],
        role="user",
        content=user_input
    )
    
    # Run the assistant on the thread
    run = client.beta.threads.runs.create(
        thread_id=agent_data["thread_id"],
        assistant_id=assistant.id
    )
    
    # Wait for the run to complete
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=agent_data["thread_id"],
            run_id=run.id
        )
        if run.status in ["queued", "in_progress"]:
            import time
            time.sleep(0.5)
    
    # Handle tool calls if any
    if run.status == "requires_action":
        tool_outputs = []
        
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments
            import json
            args = json.loads(arguments)
            
            # Execute the appropriate tool
            if function_name == "jump":
                direction = args.get("direction")
                result = jump(direction)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "jump",
                    "result": result,
                    "params": {"direction": direction}
                }
                
            elif function_name == "talk":
                message = args.get("message", "")
                result = talk(message)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "talk",
                    "result": result
                }
                
            elif function_name == "walk":
                direction = args.get("direction")
                result = walk(direction)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "walk",
                    "result": result,
                    "params": {"direction": direction}
                }
                
            elif function_name == "run":
                direction = args.get("direction")
                result = run(direction)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "run",
                    "result": result,
                    "params": {"direction": direction}
                }
                
            elif function_name == "push":
                direction = args.get("direction")
                result = push(direction)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "push",
                    "result": result,
                    "params": {"direction": direction}
                }
                
            elif function_name == "pull":
                direction = args.get("direction")
                result = pull(direction)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
                
                # Prepare response for the client
                response = {
                    "type": "command",
                    "name": "pull",
                    "result": result,
                    "params": {"direction": direction}
                }
        
        # Submit the tool outputs back to the assistant
        if tool_outputs:
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=agent_data["thread_id"],
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            
            # Wait for processing to complete
            while run.status in ["queued", "in_progress"]:
                run = client.beta.threads.runs.retrieve(
                    thread_id=agent_data["thread_id"],
                    run_id=run.id
                )
                if run.status in ["queued", "in_progress"]:
                    import time
                    time.sleep(0.5)
        
        return response, conversation_history
    
    # Get the assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=agent_data["thread_id"]
    )
    
    # Get the most recent assistant message
    assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
    if assistant_messages:
        latest_message = assistant_messages[0].content[0].text.value
        response = {
            "type": "text",
            "content": latest_message
        }
    else:
        response = {
            "type": "text",
            "content": "I'm not sure what to say. Can you try again?"
        }
    
    # Update conversation history (simplified for this implementation)
    # In a real implementation, you might want to keep track of the actual 
    # conversation in a more structured way
    
    return response, conversation_history 