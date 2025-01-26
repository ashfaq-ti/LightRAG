# import asyncio
# import websockets
# import sys

# async def listen_to_websocket():
#     uri = "ws://localhost:8020/ws"  # Replace with your actual WebSocket server URL

#     async with websockets.connect(uri) as websocket:
#         # Send a prompt to the WebSocket server
#         prompt = "is hctra call center open on thursday?"
#         await websocket.send(prompt)

#         print("Prompt sent to the server. Waiting for response...\n")

#         paragraph = ""  # Initialize an empty string to store the response

#         try:
#             while True:
#                 # Receive streaming chunks
#                 chunk = await websocket.recv()
#                 paragraph += chunk  # Append the chunk to the paragraph
                
#                 # Clear the current line and print the updated paragraph
#                 sys.stdout.write("\r" + paragraph)
#                 sys.stdout.flush()
#         except websockets.exceptions.ConnectionClosed:
#             print("\nConnection closed by the server.")

# # Run the client
# if __name__ == "__main__":
#     asyncio.run(listen_to_websocket())

# import asyncio
# import websockets

# async def listen_to_websocket():
#     uri = "ws://localhost:8020/ws"  # Replace with your actual WebSocket server URL

#     async with websockets.connect(uri) as websocket:
#         # Send a prompt to the WebSocket server
#         prompt = "What is the capital of France?"
#         await websocket.send(prompt)

#         print("Prompt sent to the server. Waiting for response...\n")

#         paragraph = ""  # Initialize an empty string to store the response

#         try:
#             while True:
#                 # Receive streaming chunks
#                 chunk = await websocket.recv()
#                 paragraph += chunk  # Append the chunk to the paragraph

#                 # Clear the previous print and reprint the updated paragraph
#                 print("\033[F\033[K", end="")  # Move cursor up one line and clear it
#                 print(paragraph)
#         except websockets.exceptions.ConnectionClosed:
#             print("\nConnection closed by the server.")

# # Run the client
# if __name__ == "__main__":
#     asyncio.run(listen_to_websocket())

import asyncio
import websockets

async def listen_to_websocket():
    uri = "ws://localhost:8020/ws"  # Replace with your actual WebSocket server URL

    async with websockets.connect(uri) as websocket:
        # Send a prompt to the WebSocket server
        prompt = "What are python keywords? Provide references And page numbers to the sources as well."
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
