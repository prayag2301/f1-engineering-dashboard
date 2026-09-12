#!/usr/bin/env python3
"""Preview exported files with Pages subpaths and real 404s, without an API/server renderer."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--base-path", default="/f1-engineering-dashboard")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "frontend/out"
    prefix = args.base_path.rstrip("/")

    class Handler(SimpleHTTPRequestHandler):
        extensions_map = SimpleHTTPRequestHandler.extensions_map | {
            ".glb": "model/gltf-binary"
        }

        def log_message(self, format, *values):
            pass  # Browser tests report failed requests without logging every JS chunk.

        def send_head(self):
            route = urlsplit(self.path).path
            if prefix and route != prefix and not route.startswith(prefix + "/"):
                self.send_error(404)
                return None
            return super().send_head()

        def translate_path(self, path):
            return super().translate_path(path[len(prefix) :] if prefix else path)

        def list_directory(self, path):
            self.send_error(404)
            return None

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(root))
    )
    print(f"Static preview: http://127.0.0.1:{args.port}{prefix}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
