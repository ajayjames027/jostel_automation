from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class MockMoodleAPI(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # Always allow CORS for our dashboard demo
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        wsfunction = params.get('wsfunction', [''])[0]
        token = params.get('wstoken', [''])[0]
        
        # Check token authentication
        if token != 'demo-token':
            self.wfile.write(json.dumps({"exception":"moodle_exception","message":"Invalid token. Access denied."}).encode())
            return
            
        # Mocking the Quiz List Endpoint
        if wsfunction == 'mod_quiz_get_quizzes_by_courses':
            response = {
                "quizzes": [
                    {"id": 1, "name": "Midterm Examination - Python Data Science"},
                    {"id": 2, "name": "Final Mock Exam - Research Writing"},
                    {"id": 3, "name": "Weekly Quiz 1 - Economics"}
                ]
            }
            self.wfile.write(json.dumps(response).encode())
            
        # Mocking the Grade Fetching (Attempts) Endpoint
        elif wsfunction == 'mod_quiz_get_attempts':
            quiz_id = params.get('quizid', ['0'])[0]
            
            # Generate different fake grades depending on which quiz they clicked
            if quiz_id == '1':
                attempts = [
                    {"userid": 1051, "state": "finished", "sumgrades": "95.00"},
                    {"userid": 1052, "state": "finished", "sumgrades": "78.50"},
                    {"userid": 1053, "state": "finished", "sumgrades": "88.00"},
                    {"userid": 1054, "state": "inprogress", "sumgrades": None}, 
                    {"userid": 1055, "state": "finished", "sumgrades": "100.00"}
                ]
            else:
                attempts = [
                    {"userid": 2041, "state": "finished", "sumgrades": "80.00"},
                    {"userid": 2042, "state": "finished", "sumgrades": "65.50"},
                    {"userid": 2043, "state": "finished", "sumgrades": "92.00"}
                ]
            
            self.wfile.write(json.dumps({"attempts": attempts}).encode())
        else:
            self.wfile.write(json.dumps({"exception":"moodle_exception","message":"API Function not mocked."}).encode())

if __name__ == '__main__':
    print("\n==============================================")
    print("MOCK MOODLE API DEMO SERVER is booting up...")
    print("==============================================")
    print("Leave this script running in the background.")
    print("Go to your live GitHub dashboard and type:")
    print("Token: demo-token")
    print("Base URL: http://localhost:8080")
    print("==============================================\n")
    server = HTTPServer(('localhost', 8080), MockMoodleAPI)
    server.serve_forever()
