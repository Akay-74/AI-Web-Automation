import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/ws/tasks/0c7f4c42-d886-4b8b-b626-174917f1b3c6"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.recv()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
