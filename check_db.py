import sqlite3
db = sqlite3.connect('db.sqlite3')
tables = [t[0] for t in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("TABLES:", tables)
