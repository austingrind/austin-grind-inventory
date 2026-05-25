"""
Austin Grind Bakery — Local Email Helper
Runs on http://localhost:9999  and sends order emails via Outlook COM automation.
Start once per session: double-click "Start Email Helper.bat"
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, sys

try:
    import win32com.client
except ImportError:
    print("ERROR: pywin32 not installed.  Run:  pip install pywin32")
    input("Press Enter to exit...")
    sys.exit(1)

PORT = 9999

class Handler(BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data   = json.loads(self.rfile.read(length))

            outlook = win32com.client.Dispatch("Outlook.Application")
            mail    = outlook.CreateItem(0)   # 0 = olMailItem
            mail.To      = data["to"]
            mail.CC      = data.get("cc", "")
            mail.Subject = data["subject"]
            mail.HTMLBody= data["html"]
            mail.Send()

            self._respond(200, {"status": "sent"})
            print(f"Sent: {data['subject']}")

        except Exception as e:
            self._respond(500, {"error": str(e)})
            print(f"Error: {e}")

    def _respond(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", len(payload))
        self._cors()
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass   # suppress default access log

if __name__ == "__main__":
    print(f"Austin Grind Email Helper running on port {PORT} — keep this window open.")
    print("Close this window to stop.\n")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
