import os
import sqlite3

paths = [
    os.getcwd(),
    os.path.join(os.getcwd(), "beiet_storage"),
    os.path.expanduser("~"),
    "/tmp"
]

for p in paths:
    if not os.path.exists(p):
        print(f"Directory {p} does not exist.")
        continue
    db = os.path.join(p, "test_perm.db")
    try:
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE t (id INT)")
        conn.close()
        print(f"OK: {p}")
        if os.path.exists(db):
            os.remove(db)
    except Exception as e:
        print(f"FAIL: {p} -> {e}")
