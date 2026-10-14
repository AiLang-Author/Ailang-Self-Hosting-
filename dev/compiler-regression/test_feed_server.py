#!/usr/bin/env python3
"""HTTP fence for Applications/Feed/feed_server.ailang on 127.0.0.1:18767."""
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
PORT = 18767
BASE = "http://%s:%s" % (HOST, PORT)
SECRET = "twelve-dollar-challenge"
TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJnb2xkZW5fZW1iZXJfMSIsImlhdCI6MTcwMDAwMDAwMCwiZXhwIjoyMDAwMDAwMDAwfQ."
    "eY9aaLG5NFg6gwKM9JNh4sBrJp5rmWUFTt3npF892hU"
)
BADSUB = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJhYmMiLCJ1c2VybmFtZSI6ImdvbGRlbl9lbWJlcl8xIiwiaWF0IjoxNzAwMDAwMDAwLCJleHAiOjIwMDAwMDAwMDB9."
    "XXud6TOQSvmyu3NIPOjV3lgwM9JZ-KFjLGlY9PDdKT0"
)


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sign(payload):
    h = b64url(b'{"alg":"HS256","typ":"JWT"}')
    p = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    s = b64url(hmac.new(SECRET.encode("ascii"), ("%s.%s" % (h, p)).encode("ascii"), hashlib.sha256).digest())
    return "%s.%s.%s" % (h, p, s)


def req(method, path, body=None, token=None, timeout=5, auth=None):
    data = None
    headers = {}
    if body is not None:
        data = body.encode("utf-8")
        headers["Content-Type"] = "application/json"
    if auth is not None:
        headers["Authorization"] = auth
    elif token is not None:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, raw.decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, raw.decode("utf-8"), dict(e.headers)


def main():
    bad = 0
    st, body, _ = req("GET", "/health")
    if st != 200:
        print("FAIL health status", st, body)
        bad += 1
    else:
        h = json.loads(body)
        if h.get("status") != "ok" or h.get("db") != "ok" or "uptime_s" not in h:
            print("FAIL health body", body)
            bad += 1
        keys = list(json.loads(body).keys()) if False else None
        if body.find('"status":"ok"') < 0 or body.find('"db":"ok"') < 0:
            print("FAIL health key order", body)
            bad += 1

    st, body, _ = req("GET", "/nope")
    if st != 404 or body != '{"error":"not found"}':
        print("FAIL 404", st, body)
        bad += 1

    for bad_id in ("abc", "0", "-1", "1.5"):
        st, body, _ = req("GET", "/posts/" + bad_id)
        if st != 400 or body != '{"error":"invalid post id"}':
            print("FAIL invalid id", bad_id, st, body)
            bad += 1

    st, body, _ = req("GET", "/posts/9999")
    if st != 404 or body != '{"error":"post not found"}':
        print("FAIL missing post", st, body)
        bad += 1

    st, body, _ = req("GET", "/posts/300")
    if st != 200:
        print("FAIL get 300", st, body)
        bad += 1
    else:
        p = json.loads(body)["post"]
        if p["id"] != 300 or p["body"] != "body_300" or p["author"] != "user_2" or p["like_count"] != 20:
            print("FAIL get 300 fields", p)
            bad += 1
        if not body.startswith('{"post":{"id":300,'):
            print("FAIL get 300 key order", body)
            bad += 1

    st, body, _ = req("GET", "/feed")
    if st != 200:
        print("FAIL feed", st, body)
        bad += 1
    else:
        posts = json.loads(body)["posts"]
        ids = [p["id"] for p in posts]
        if ids != list(range(300, 280, -1)):
            print("FAIL feed ids", ids)
            bad += 1
        if not body.startswith('{"posts":[{"id":300,'):
            print("FAIL feed key order", body[:80])
            bad += 1

    st, body, _ = req("POST", "/posts", body='{"body":"hello api"}')
    if st != 401 or body != '{"error":"missing bearer token"}':
        print("FAIL post no auth", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts", body='{"body":"x"}', auth="Basic abc")
    if st != 401 or body != '{"error":"missing bearer token"}':
        print("FAIL basic auth", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts", body='{"body":"x"}', token="abc")
    if st != 401 or body != '{"error":"invalid or expired token"}':
        print("FAIL garbage token", st, body)
        bad += 1

    now = int(time.time())
    expired = sign({"sub": "1", "username": "golden_ember_1", "iat": now - 7200, "exp": now - 3600})
    st, body, _ = req("POST", "/posts", body='{"body":"x"}', token=expired)
    if st != 401 or body != '{"error":"invalid or expired token"}':
        print("FAIL expired", st, body)
        bad += 1

    none = b64url(b'{"alg":"none","typ":"JWT"}') + "." + TOKEN.split(".")[1] + "."
    st, body, _ = req("POST", "/posts", body='{"body":"x"}', token=none)
    if st != 401 or body != '{"error":"invalid or expired token"}':
        print("FAIL alg none", st, body)
        bad += 1

    no_name = sign({"sub": "1", "iat": now, "exp": now + 3600})
    st, body, _ = req("POST", "/posts", body='{"body":"x"}', token=no_name)
    if st != 401 or body != '{"error":"invalid token payload"}':
        print("FAIL no username", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts/abc/like")
    if st != 401 or body != '{"error":"missing bearer token"}':
        print("FAIL like no auth", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts/abc/like", token=TOKEN)
    if st != 400 or body != '{"error":"invalid post id"}':
        print("FAIL like bad id after auth", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts", body='{"body":"hello api"}', token=BADSUB)
    if st != 401 or body != '{"error":"invalid token payload"}':
        print("FAIL bad sub", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts", body="not-json", token=TOKEN)
    if st != 400 or body != '{"error":"malformed JSON body"}':
        print("FAIL malformed", st, body)
        bad += 1

    st, body, _ = req("POST", "/posts", body="{bad json", token=TOKEN)
    if st != 400 or body != '{"error":"malformed JSON body"}':
        print("FAIL malformed brace", st, body)
        bad += 1

    for label, payload in (
        ("empty", '{"body":""}'),
        ("whitespace", '{"body":"   "}'),
        ("numeric", '{"body":123}'),
        ("missing", "{}"),
    ):
        st, body, _ = req("POST", "/posts", body=payload, token=TOKEN)
        if st != 400 or body != '{"error":"body is required"}':
            print("FAIL", label, "body", st, body)
            bad += 1

    st, body, _ = req("POST", "/posts", body='{"body":"%s"}' % ("a" * 501), token=TOKEN)
    if st != 400 or body != '{"error":"body must be at most 500 characters"}':
        print("FAIL 501 body", st, body)
        bad += 1

    st, body, hdrs = req("POST", "/posts", body='{"body":"hello api"}', token=TOKEN)
    ctype = ""
    for k, v in hdrs.items():
        if k.lower() == "content-type":
            ctype = v
    if not ctype.lower().startswith("application/json"):
        print("FAIL create content-type", ctype)
        bad += 1
    if st != 201:
        print("FAIL create", st, body)
        bad += 1
    else:
        p = json.loads(body)["post"]
        if p["id"] != 301 or p["body"] != "hello api" or p["author"] != "golden_ember_1" or p["like_count"] != 0:
            print("FAIL create fields", p)
            bad += 1
        if len(p["created_at"]) != 24 or not p["created_at"].endswith("Z"):
            print("FAIL created_at", p["created_at"])
            bad += 1

    st, body, _ = req("GET", "/posts/301")
    if st != 200:
        print("FAIL get 301", st, body)
        bad += 1
    else:
        p = json.loads(body)["post"]
        if p["id"] != 301 or p["body"] != "hello api" or p["author"] != "user_1":
            print("FAIL get 301 fields", p)
            bad += 1

    special = '{"body":"  test: <b>&amp;</b> \\"quoted\\" / café ✓  "}'
    st, body, _ = req("POST", "/posts", body=special, token=TOKEN)
    if st != 201:
        print("FAIL special create", st, body)
        bad += 1
    else:
        got = json.loads(body)["post"]["body"]
        if got != 'test: <b>&amp;</b> "quoted" / café ✓':
            print("FAIL special body", got)
            bad += 1

    st, body, _ = req("POST", "/posts/9999/like", token=TOKEN)
    if st != 404 or body != '{"error":"post not found"}':
        print("FAIL like missing", st, body)
        bad += 1

    st, body, _ = req("GET", "/feed")
    if st != 200:
        print("FAIL feed after create", st, body)
        bad += 1
    else:
        posts = json.loads(body)["posts"]
        ids = [p["id"] for p in posts]
        if 301 not in ids:
            print("FAIL feed missing 301", ids)
            bad += 1
        if ids[:2] != [300, 299]:
            print("FAIL feed still topped by 300/299", ids[:5])
            bad += 1
        for fp in posts:
            st2, b2, _ = req("GET", "/posts/%s" % fp["id"])
            if st2 != 200:
                print("FAIL feed getpost", fp["id"], st2, b2)
                bad += 1
                break
            gp = json.loads(b2)["post"]
            if gp["id"] != fp["id"] or gp["body"] != fp["body"] or gp["created_at"] != fp["created_at"] or gp["author"] != fp["author"]:
                print("FAIL feed vs getpost", fp, gp)
                bad += 1
                break

    st, body, _ = req("GET", "/feed")
    if st != 200:
        print("FAIL feed second", st, body)
        bad += 1
    else:
        posts = json.loads(body)["posts"]
        hit = [p for p in posts if p["id"] == 301]
        if not hit or hit[0]["body"] != "hello api":
            print("FAIL feed second 301", hit)
            bad += 1

    st, body, _ = req("POST", "/posts/301/like", token=TOKEN)
    if st != 201:
        print("FAIL like first", st, body)
        bad += 1
    else:
        j = json.loads(body)
        if j != {"liked": True, "already_liked": False, "post_id": 301}:
            print("FAIL like first body", body)
            bad += 1

    st, body, _ = req("POST", "/posts/301/like", token=TOKEN)
    if st != 200:
        print("FAIL like again", st, body)
        bad += 1
    else:
        j = json.loads(body)
        if j.get("already_liked") is not True:
            print("FAIL like again body", body)
            bad += 1

    st, body, _ = req("GET", "/posts/301")
    p = json.loads(body)["post"]
    if p.get("like_count") != 1:
        print("FAIL like_count after", p)
        bad += 1

    if bad == 0:
        print("PASS")
    return bad


if __name__ == "__main__":
    sys.exit(main())
