import socket

host = "localhost"
port = 5432

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)  # 2-second timeout

try:
    sock.connect((host, port))
    print(f"✅ PostgreSQL is listening on {host}:{port}")
except (socket.timeout, ConnectionRefusedError):
    print(f"❌ PostgreSQL is NOT listening on {host}:{port}")
finally:
    sock.close()
