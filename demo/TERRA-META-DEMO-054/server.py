import json, mimetypes, os, importlib.util, sys, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from jury_adapter_041 import discover
from free_question_guard_084 import assess_request, json_reply # TERRA-FINAL-084-FREE-QUESTION-SERVER
ROOT=Path(__file__).resolve().parent
TRACES=Path.home()/"Documents"/"TerraCouncil-Scientific-Inputs"

LIVE_LOCK = threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_POST(self):
        if urlparse(self.path).path == "/api/release/action":
            import release_101
            return release_101.post(self)
        # TERRA-FINAL-084-FREE-QUESTION-SERVER: controlled question preflight only.
        if urlparse(self.path).path == "/api/question/preview":
            from free_question_guard_084 import assess_request, json_reply
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<1 or length>8192:
                    return json_reply(self,400,{"error":"invalid_request_size"})
                payload=json.loads(self.rfile.read(length))
                return json_reply(self,200,assess_request(payload,TRACES))
            except (ValueError,TypeError,json.JSONDecodeError):
                return json_reply(self,400,{"error":"invalid_question_payload"})
        if urlparse(self.path).path == "/api/question/live":
            # TERRA-FINAL-089-UNIVERSAL-EVIDENCE-PREFLIGHT
            from universal_live_089 import route
            return route(self,TRACES,__file__)
        # TERRA-FINAL-092-LIVE-EXECUTE-ROUTE
        if urlparse(self.path).path == "/api/question/execute":
            from dispatch_092 import route
            if not LIVE_LOCK.acquire(blocking=False):
                from free_question_guard_084 import json_reply
                return json_reply(self,409,{"error":"another_live_session_running"})
            try:return route(self,__file__)
            finally:LIVE_LOCK.release()
        if urlparse(self.path).path != "/api/live":
            self.send_error(404);return
        def reply(code, payload):
            raw=json.dumps(payload,ensure_ascii=False,default=str).encode("utf-8")
            self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        if not os.environ.get("META_API_KEY"):
            return reply(503,{"error":"Live mode is not configured: META_API_KEY absent from server."})
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size<1 or size>4096: return reply(400,{"error":"Invalid request size"})
            data=json.loads(self.rfile.read(size))
            if data!={"pilot":"FLOOD","confirmed":True,"max_calls":4}:
                return reply(400,{"error":"Explicit authorization required. FLOOD pilot only, 4 calls maximum."})
            if not LIVE_LOCK.acquire(blocking=False):return reply(409,{"error":"A live session is already running."})
            try:
                import glob
                repo=Path(__file__).resolve().parents[3]
                pkg=repo/"data"/"science_packages"
                scripts=list(pkg.rglob("terra_science_024.py"))
                packets=sorted(TRACES.glob("SCIENCE-021-FLOOD-*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
                if not scripts or not packets:return reply(503,{"error":"Live scientific engine or FLOOD packet missing. No call attempted."})
                sys.path.insert(0,str(repo/"src"))
                sys.path.insert(0,str(scripts[0].parent))
                import terra_science_024 as sci
                from terra_meta_013c_adaptive_council import run
                from council import meta_call
                packet=json.loads(packets[0].read_text(encoding="utf-8"))
                result=sci.execute(packet,run,live=True,key=os.environ["META_API_KEY"],max_calls=4,original=meta_call)
                from datetime import datetime,timezone
                path=TRACES/("SCIENCE-024-LIVE-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")+".json")
                with path.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2)
                return reply(200,{"trace":result})
            finally:LIVE_LOCK.release()
        except Exception as exc:
            return reply(500,{"error":"Live execution interrupted: "+str(type(exc).__name__)+". Do not retry without reviewing saved logs."})
    def do_GET(self):
        if urlparse(self.path).path.startswith("/api/release/"):
            import release_101
            return release_101.get(self)
        path=urlparse(self.path).path
        if path=="/api/council-session":
            folder=ROOT/"council_sessions"
            available={}
            for lang in ("fr","en"):
                p=folder/f"{lang}_flood_council_manifest.json"
                try:
                    obj=json.loads(p.read_text(encoding="utf-8"))
                    if obj.get("status")=="COMPLETE" and len(obj.get("segments",[]))==5 and all(
                         (folder/r["filename"]).is_file() for r in obj["segments"]):
                        available[lang]={"segments":[{"speaker":r["speaker"],"role":r["role"],
                             "text":r["text"],"url":"/council_sessions/"+r["filename"]} for r in obj["segments"]],
                             "source_trace":obj["trace_filename"],"adaptation":obj["adaptation"]}
                except (OSError,ValueError,KeyError):
                    pass
            raw=json.dumps({"sessions":available},ensure_ascii=False).encode("utf-8")
            self.send_response(200);self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if path=="/api/voices":
            path_manifest=ROOT/"voice_audio"/"manifest.json"
            try: manifest=json.loads(path_manifest.read_text(encoding="utf-8"))
            except (OSError,ValueError): manifest={}
            # Only return records with MP3s physically available.
            manifest={p:[r for r in entries if (ROOT/"voice_audio"/Path(r.get("mp3", "")).name).is_file()]
                      for p,entries in manifest.items() if isinstance(entries,list)}
            raw=json.dumps({"voices":manifest},ensure_ascii=False).encode("utf8")
            self.send_response(200);self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if path=="/api/trace":
            found=discover(TRACES)
            raw=json.dumps({"trace":found.get("FLOOD"),"additional_traces":{k:v for k,v in found.items() if k!="FLOOD"}},ensure_ascii=False).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        return super().do_GET()


# TERRA_NATIVE_107_ACTIVE: additive language-specific routes
import native_107 as _terra_native107
_native107_post = Handler.do_POST
_native107_get = Handler.do_GET
def _native107_post_route(self):
    if urlparse(self.path).path == '/api/release107/action':return _terra_native107.post(self)
    return _native107_post(self)
def _native107_get_route(self):
    if urlparse(self.path).path.startswith('/api/release107/'):return _terra_native107.get(self)
    return _native107_get(self)
Handler.do_POST = _native107_post_route
Handler.do_GET = _native107_get_route


# TERRA_RELEASE_112_ACTIVE - trace-bound PDF/MP3 orchestration
import deliverables_112 as _terra112
_terra112_old_post=Handler.do_POST
_terra112_old_get=Handler.do_GET
def _terra112_post(self):
    if urlparse(self.path).path == '/api/release112/action':return _terra112.handle_post(self)
    return _terra112_old_post(self)
def _terra112_get(self):
    if urlparse(self.path).path.startswith('/api/release112/'):return _terra112.handle_get(self)
    return _terra112_old_get(self)
Handler.do_POST=_terra112_post
Handler.do_GET=_terra112_get


# TERRA_RELEASE_113_ACTIVE - automatic structural checks; no fake human approvals
import auto_113 as _terra113
_terra113_previous_post=Handler.do_POST
_terra113_previous_get=Handler.do_GET
def _terra113_post(self):
    if urlparse(self.path).path == '/api/release113/generate':return _terra113.handle_post(self)
    return _terra113_previous_post(self)
def _terra113_get(self):
    if urlparse(self.path).path.startswith(('/api/release113/status','/api/release113/audio/')):return _terra113.handle_get(self)
    return _terra113_previous_get(self)
Handler.do_POST=_terra113_post
Handler.do_GET=_terra113_get


# TERRA_RELEASE_115_JURY_DEMO - GET only, three isolated prerecorded pilots
import pilot_115 as _terra115
_terra115_previous_get=Handler.do_GET
def _terra115_get(self):
    if urlparse(self.path).path.startswith('/api/release115/'):
        return _terra115.handle_get(self)
    return _terra115_previous_get(self)
Handler.do_GET=_terra115_get

if __name__=="__main__":
    port=int(os.environ.get("TERRA_UX_PORT","8773"))
    print("TerraCouncil DEMO-041 : http://127.0.0.1:%s/"%port,flush=True)
    print("Trace locale :",TRACES,flush=True)
    ThreadingHTTPServer(("127.0.0.1",port),Handler).serve_forever()
