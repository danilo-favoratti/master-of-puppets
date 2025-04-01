import React, { useState, useEffect } from 'react';

// Define the structure of a tool call
export interface ToolCall {
  id: string;
  name: string;
  params: Record<string, any>;
  timestamp: number;
  result?: string;
}

interface ToolsMenuProps {
  toolCalls: ToolCall[];
}

const ToolsMenu: React.FC<ToolsMenuProps> = ({ toolCalls }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  // Format the timestamp
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };
  
  // Format parameters for display
  const formatParams = (params: Record<string, any>) => {
    // Filter out large objects/arrays
    const formattedParams: Record<string, any> = {};
    
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
          formattedParams[key] = value.length > 5 
            ? `[Array: ${value.length} items]` 
            : value;
        } else {
          const keys = Object.keys(value);
          formattedParams[key] = keys.length > 5 
            ? `{Object: ${keys.length} properties}` 
            : value;
        }
      } else {
        formattedParams[key] = value;
      }
    }
    
    return JSON.stringify(formattedParams, null, 2);
  };
  
  // Toggle the menu open/closed
  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="fixed top-4 right-4 z-50 border-2 border-red-500">
      {/* Tools menu button */}
      <button 
        onClick={toggleMenu}
        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded shadow-lg flex items-center"
      >
        <span className="mr-2">🛠️</span>
        Tools {toolCalls.length > 0 && `(${toolCalls.length})`}
      </button>
      
      {/* Tools panel */}
      {isOpen && (
        <div className="bg-gray-900 text-white shadow-xl rounded p-4 overflow-auto max-h-[80vh] w-96 mt-2">
          <div className="flex justify-between items-center mb-4 pb-2 border-b border-gray-700">
            <h2 className="text-xl font-bold">Tool Calls</h2>
            <button onClick={toggleMenu} className="text-gray-400 hover:text-white text-xl">
              ✕
            </button>
          </div>
          
          {toolCalls.length === 0 ? (
            <p className="text-gray-400 italic">No tools have been called yet</p>
          ) : (
            <div className="space-y-4">
              {toolCalls.map((tool) => (
                <div key={tool.id} className="border border-gray-700 rounded p-3 bg-gray-800">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-bold text-blue-400">{tool.name}</h3>
                    <span className="text-xs text-gray-400">{formatTime(tool.timestamp)}</span>
                  </div>
                  <div className="mb-2">
                    <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-1">Parameters:</h4>
                    <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto whitespace-pre-wrap break-words">
                      {formatParams(tool.params)}
                    </pre>
                  </div>
                  {tool.result && (
                    <div>
                      <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-1">Result:</h4>
                      <p className="text-xs bg-gray-900 p-2 rounded overflow-x-auto break-words">
                        {tool.result.length > 300 ? `${tool.result.substring(0, 300)}...` : tool.result}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolsMenu; 