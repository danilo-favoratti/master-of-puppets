// HomeScreen.tsx

import React from "react";

interface HomeScreenProps {
  themeIsSelected: boolean;
  isConnected: boolean;
  themeSelect: (theme: string) => void;
  socketMessage: string | null;
}

const HomeScreen = ({
  themeIsSelected,
  isConnected,
  themeSelect,
  socketMessage,
}: HomeScreenProps) => {
  const connectionBgColor = () => {
    if (isConnected) {
      return "green";
    } else if (socketMessage) {
      return "red";
    } else {
      return "#005ea3";
    }
  };
  return (
    <div className="flex flex-col h-screen">
      <div className="home-screen">
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            height: "100vh",
            width: "100vw",
          }}
        >
          <div style={{ flex: 1, position: "relative" }}>
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                zIndex: 20,
              }}
            >
              <div>
                <div className="home-logo"></div>
                <div
                  style={{
                    textAlign: "center",
                    margin: "10px 0 20px 0",
                    color: "#fff",
                    backgroundColor: connectionBgColor(),
                    fontSize: "16px",
                    padding: "5px 10px",
                    borderRadius: "5px",
                  }}
                >
                  {isConnected
                    ? "✓ Connected to server"
                    : "⚠ Connecting to server..."}

                  {socketMessage && (
                    <div style={{ color: "#fff", fontSize: "12px" }}>
                      {socketMessage}
                    </div>
                  )}
                </div>
                <div className="">
                  <h3 style={{ color: "#514b3f", textAlign: "center" }}>
                    Select a Game Theme
                  </h3>
                </div>
              </div>

              <button
                className="button-pixel"
                onClick={() => themeSelect("Abandoned_Prisioner")}
                style={{
                  opacity: isConnected ? 1 : 0.6,
                }}
                disabled={!isConnected}
              >
                Abandoned Prisioner
              </button>
              <button
                className="button-pixel"
                onClick={() => themeSelect("Crash_in_the_Sea")}
                style={{
                  opacity: isConnected ? 1 : 0.6,
                }}
                disabled={!isConnected}
              >
                Crash in the Sea
              </button>
              <button
                className="button-pixel"
                onClick={() => themeSelect("Lost_Memory")}
                style={{
                  opacity: isConnected ? 1 : 0.6,
                }}
                disabled={!isConnected}
              >
                Lost Memory
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomeScreen;
