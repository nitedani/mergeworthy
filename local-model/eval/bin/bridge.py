#!/usr/bin/env python3
"""Byte pipe for the sandbox. outer: unix socket -> 127.0.0.1:PORT (host side). inner: 127.0.0.1:PORT -> unix socket
(inside the network-less sandbox). The model server is the only thing the sandbox can reach."""
import asyncio, sys
mode, sock, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
async def pipe(r, w):
    try:
        while (b := await r.read(65536)): w.write(b); await w.drain()
    except Exception: pass
    finally: w.close()
async def handle(r, w):
    try:
        r2, w2 = await (asyncio.open_connection('127.0.0.1', port) if mode == 'outer' else asyncio.open_unix_connection(sock))
    except Exception: w.close(); return
    await asyncio.gather(pipe(r, w2), pipe(r2, w))
async def main():
    s = await (asyncio.start_unix_server(handle, sock) if mode == 'outer' else asyncio.start_server(handle, '127.0.0.1', port))
    async with s: await s.serve_forever()
asyncio.run(main())
