import asyncio, sys, json
import websockets
clients=set()
async def handler(ws):
    clients.add(ws)
    try:
        async for _ in ws: pass
    finally: clients.discard(ws)
async def main(port):
    msg=json.dumps({"type":"chat","name":"Mira","text":"x"*250})
    async with websockets.serve(handler,"127.0.0.1",port,ping_interval=None):
        while True:
            await asyncio.sleep(0.2)
            websockets.broadcast(clients,msg)
asyncio.run(main(int(sys.argv[1])))
