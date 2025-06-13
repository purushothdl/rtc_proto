import socket

try:
    ip = socket.gethostbyname('db.esqzolxsjmtmslieecok.supabase.co')
    print(f"Resolved IP: {ip}")
except Exception as e:
    print(f"Error: {e}")
