import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"OK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


async def run_health_server(port: int):
    def run():
        server = HTTPServer(("0.0.0.0", port), Handler)
        server.serve_forever()

    thread = Thread(target=run, daemon=True)
    thread.start()

    while True:
        await asyncio.sleep(3600)
