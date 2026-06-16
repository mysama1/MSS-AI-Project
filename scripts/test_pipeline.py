import urllib.request,json,http.client
r=urllib.request.urlopen("http://localhost:5100/health")
d=json.loads(r.read())
print("Agent:",d["alive"])

conn=http.client.HTTPConnection("127.0.0.1",5100,timeout=60)
body=json.dumps({"steps":[{"prompt":"Say hello in 5 words","label":"greet"},{"prompt":"Translate to Chinese","label":"tl"}]})
conn.request("POST","/pipeline",body,{"Content-Type":"application/json"})
r=conn.getresponse()
d=json.loads(r.read())
print("Pipeline:",d["total_steps"],"steps",d["total_elapsed_ms"],"ms")
for s in d["pipeline"]:
    out=s["output"][:80] if s["output"] else "[empty]"
    print("  Step",s["step"],s["label"],":",out,"d=",s["delta"],"tax=",s["heat_tax"])
print("Final d=",d["final_delta"],"bridge=",d["bridge"])
