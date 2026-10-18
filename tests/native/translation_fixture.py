from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time, threading, subprocess, sys
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def reply(self, value, status=200):
  self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
  try:self.wfile.write(json.dumps(value).encode())
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self): self.reply({'data':[{'id':'fixture-local'},{'id':'remote:cloud'}]})
 def do_POST(self):
  value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  model=value.get('model')
  if self.path=='/api/show':return self.reply({'remote_host':'https://example.invalid'} if model=='cloud-alias' else {})
  if model=='redirect':
   self.send_response(302);self.send_header('Location','http://192.0.2.1/should-never-be-requested');self.end_headers();return
  if model=='slow':time.sleep(5)
  self.reply({'choices':[{'finish_reason':'length' if model=='truncated' else 'stop','message':{'content':'Hello'}}]})
server=ThreadingHTTPServer(('127.0.0.1',11434), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
 result = subprocess.run(sys.argv[1:])
finally:
 server.shutdown()
 server.server_close()
sys.exit(result.returncode)
