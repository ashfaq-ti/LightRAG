import asyncio
import websockets

async def listen_to_websocket():
    uri = "ws://localhost:8020/ws"  # Replace with your actual WebSocket server URL

    async with websockets.connect(uri) as websocket:
        # Send a prompt to the WebSocket server
        prompt = f"what is an EX tag, how does it function? also give the call center timings , also Provide top level reference document names and relevant page numbers that are related to the user's question. DO NOT MENTION ABOUT ENTITIES OR RELATIONSHIPS OR DATA TABLES"
        await websocket.send(prompt)

        print("Prompt sent to the server. Waiting for response...\n")
        try:
            while True:
                # Receive streaming chunks
                chunk = await websocket.recv()
                # Clear the current line and print the updated paragraph
                print(f"{chunk}", end="", flush=True)
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed by the server.")

# Run the client
if __name__ == "__main__":
    asyncio.run(listen_to_websocket())
