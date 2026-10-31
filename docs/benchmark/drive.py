import asyncio, os, subprocess, sys, time, json
import websockets
B = os.path.dirname(os.path.abspath(__file__)); PORT = 9300
TICK = os.sysconf("SC_CLK_TCK")
def rss(pid):
    for l in open(f"/proc/{pid}/status"):
        if l.startswith("VmRSS"): return int(l.split()[1]) / 1024
def thr(pid):
    for l in open(f"/proc/{pid}/status"):
        if l.startswith("Threads"): return int(l.split()[1])
def cpu(pid):
    f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split(); return (int(f[11]) + int(f[12])) / TICK
TARGETS = {
 "Python (asyncio+websockets)": ([sys.executable, f"{B}/py/srv.py", "{p}"], f"{B}/py/srv.py"),
 "Node.js 22 (ws)": (["node", f"{B}/node/srv.js", "{p}"], "node"),
 "Go 1.24 (coder/websocket)": ([f"{B}/go/srv", "{p}"], f"{B}/go/srv"),
 "Rust (axum, 1 Thread)": ([f"{B}/rust/target/release/srv", "{p}"], f"{B}/rust/target/release/srv"),
}
async def run(name, cmd, files):
    global PORT; PORT += 1; port = PORT
    p = subprocess.Popen([c.replace("{p}", str(port)) for c in cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=B)
    for _ in range(100):
        try: r, w = await asyncio.open_connection("127.0.0.1", port); w.close(); break
        except OSError: await asyncio.sleep(0.1)
    await asyncio.sleep(2)
    idle = rss(p.pid)
    got = [0]; socks = []
    async def reader(ws):
        async for _ in ws: got[0] += 1
    tasks = []
    for _ in range(3):
        ws = await websockets.connect(f"ws://127.0.0.1:{port}/ws"); socks.append(ws); tasks.append(asyncio.create_task(reader(ws)))
    await asyncio.sleep(2); c0 = cpu(p.pid); t0 = time.time(); g0 = got[0]
    await asyncio.sleep(20)
    c1 = cpu(p.pid); dt = time.time() - t0
    out = dict(idle=idle, load=rss(p.pid), cpu=(c1 - c0) / dt * 100, threads=thr(p.pid), msgs=(got[0] - g0) / dt, startup=None)
    for t in tasks: t.cancel()
    p.terminate(); p.wait()
    size = os.path.getsize(files) if os.path.exists(files) else 0
    out["size"] = size
    return out
async def main():
    res = {}
    for name, (cmd, files) in TARGETS.items():
        res[name] = await run(name, cmd, files); print(name, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in res[name].items()}, flush=True)
    json.dump(res, open(f"{B}/result.json", "w"))
asyncio.run(main())
