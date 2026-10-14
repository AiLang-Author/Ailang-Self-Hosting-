#!/usr/bin/env python3
"""Build /tmp/split.db with interior table + DESC feed-index pages."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

PATH = "/tmp/split.db"
SCHEMA = """
CREATE TABLE users (
  id          INTEGER PRIMARY KEY,
  username    TEXT NOT NULL UNIQUE,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE posts (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  body        TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 500),
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE likes (
  user_id     INTEGER NOT NULL REFERENCES users(id),
  post_id     INTEGER NOT NULL REFERENCES posts(id),
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (user_id, post_id)
);
CREATE INDEX posts_created_at_id_idx ON posts (created_at DESC, id DESC);
CREATE INDEX posts_user_id_idx       ON posts (user_id);
CREATE INDEX likes_post_id_idx       ON likes (post_id);
"""


def main():
    for extra in (PATH, PATH + "-wal", PATH + "-shm"):
        if os.path.exists(extra):
            os.remove(extra)
    con = sqlite3.connect(PATH)
    con.executescript("PRAGMA journal_mode=DELETE;")
    con.executescript(SCHEMA)
    con.execute("PRAGMA foreign_keys=OFF")
    for i in range(1, 21):
        con.execute(
            "INSERT INTO users(id, username, created_at) VALUES (?,?,?)",
            (i, "user_%d" % i, "2025-01-01T00:00:00.000Z"),
        )
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(1, 299):
        ts = (base + timedelta(milliseconds=i)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        uid = ((i - 1) % 20) + 1
        con.execute(
            "INSERT INTO posts(id, user_id, body, created_at) VALUES (?,?,?,?)",
            (i, uid, "body_%d" % i, ts),
        )
    ts_top = "2026-12-31T23:59:59.999Z"
    con.execute(
        "INSERT INTO posts(id, user_id, body, created_at) VALUES (?,?,?,?)",
        (299, 1, "body_299", ts_top),
    )
    con.execute(
        "INSERT INTO posts(id, user_id, body, created_at) VALUES (?,?,?,?)",
        (300, 2, "body_300", ts_top),
    )
    for uid in range(1, 21):
        for pid in range(2, 301):
            con.execute(
                "INSERT OR IGNORE INTO likes(user_id, post_id, created_at) VALUES (?,?,?)",
                (uid, pid, "2026-06-01T00:00:00.000Z"),
            )
    con.commit()
    feed = con.execute(
        "SELECT id FROM posts ORDER BY created_at DESC, id DESC LIMIT 20"
    ).fetchall()
    print("feed", [r[0] for r in feed])
    print(
        "likes 300",
        con.execute("SELECT count(*) FROM likes WHERE post_id=300").fetchone()[0],
        "likes 1",
        con.execute("SELECT count(*) FROM likes WHERE post_id=1").fetchone()[0],
        "likes 250",
        con.execute("SELECT count(*) FROM likes WHERE post_id=250").fetchone()[0],
        "nlikes",
        con.execute("SELECT count(*) FROM likes").fetchone()[0],
    )
    print("catalog", con.execute("SELECT type,name,rootpage FROM sqlite_master").fetchall())
    con.close()
    print("wrote", PATH, "size", os.path.getsize(PATH))


if __name__ == "__main__":
    main()
