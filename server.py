"""
AutoJobs Local Backend Server & 1-Click Action API.
Serves the Copilot Dashboard and handles 1-Click Email Dispatching via Gmail SMTP.
"""

import json
import logging
import mimetypes
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import config
import outbound_engine
import referral_engine
import ats_optimizer
import candidate_profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
PORT = 8000


class AutoJobsRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging
        logging.info(f"{self.command} {self.path}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API Routes
        if path == "/api/tracker":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = outbound_engine.load_tracker()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # Serve Dashboard Root redirect
        if path in ["", "/"]:
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return

        # Serve Static Files
        if path.startswith("/dashboard"):
            rel_path = path[len("/dashboard"):].lstrip("/")
            if not rel_path or rel_path == "":
                rel_path = "index.html"
            
            file_path = DASHBOARD_DIR / rel_path
            if file_path.exists() and file_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(file_path))
                self.send_response(200)
                self.send_header("Content-Type", mime_type or "text/plain")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # 404 Fallback
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON Body
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        # 1-Click Email Dispatch Route
        if path == "/api/send-pitch":
            to_email = payload.get("to_email", "").strip()
            subject = payload.get("subject", "").strip()
            body = payload.get("body", "").strip()
            company = payload.get("company", "Company")
            role = payload.get("role", "Product Manager")

            if not to_email or not subject or not body:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Missing to_email, subject, or body"}).encode("utf-8"))
                return

            # Dispatch via Outbound Engine
            success = outbound_engine.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                is_digest=False,
                attach_resume=True
            )

            # Update Tracker Ledger
            if success:
                tracker = outbound_engine.load_tracker()
                today_str = outbound_engine.datetime.now(outbound_engine.timezone.utc).strftime("%Y-%m-%d")
                updated = False
                for item in tracker:
                    if item.get("company", "").lower() == company.lower():
                        item["status"] = "OUTREACH_SENT"
                        item["contact_email"] = to_email
                        item["last_action_date"] = today_str
                        item["date_applied"] = today_str
                        if "history" not in item:
                            item["history"] = []
                        item["history"].append({
                            "date": today_str,
                            "action": f"1-Click pitch sent to {to_email} with attached resume PDF."
                        })
                        updated = True
                        break
                if updated:
                    outbound_engine.save_tracker(tracker)

            self.send_response(200 if success else 500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            resp_data = {
                "status": "success" if success else "error",
                "message": f"Pitch and resume PDF successfully dispatched to {to_email}!" if success else f"Failed to transmit email to {to_email}. Please check SMTP configuration."
            }
            self.wfile.write(json.dumps(resp_data).encode("utf-8"))
            return

        # 404 Fallback
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, AutoJobsRequestHandler)
    logging.info(f"⚡ AutoJobs Copilot Server running at http://localhost:{PORT}/dashboard/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()


if __name__ == "__main__":
    run_server()
