from __future__ import annotations

import argparse
import http.client
import http.server
import ssl
from typing import Final

HOP_BY_HOP: Final = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream_host: str
    upstream_port: int

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP and key.lower() != "host"
        }
        headers["Host"] = f"{self.upstream_host}:{self.upstream_port}"
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-For"] = self.client_address[0]
        conn = http.client.HTTPConnection(self.upstream_host, self.upstream_port, timeout=5)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Strict-Transport-Security", "max-age=31536000")
            self.end_headers()
            self.wfile.write(data)
        finally:
            conn.close()

    do_GET = _proxy
    do_POST = _proxy
    do_PATCH = _proxy

    def log_message(self, format: str, *args: object) -> None:
        print(f"TLS_PROXY {self.address_string()} {format % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--upstream-host", required=True)
    parser.add_argument("--upstream-port", type=int, default=9530)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    ProxyHandler.upstream_host = args.upstream_host
    ProxyHandler.upstream_port = args.upstream_port
    server = http.server.ThreadingHTTPServer((args.listen, args.port), ProxyHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
