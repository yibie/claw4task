#!/usr/bin/env python3
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else './claw4task.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print('=== Task Status Breakdown ===')
c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

print()
print('=== Pending Review Tasks (Need Publisher Action) ===')
c.execute("""SELECT id, title, assignee_id, reward FROM tasks 
             WHERE status = 'pending_review' ORDER BY updated_at DESC""")
rows = c.fetchall()
if rows:
    for row in rows[:5]:
        print(f"  {row[0][:10]}... | {row[1][:25]} | Worker: {row[2][:8] if row[2] else 'N/A'}... | {row[3]} coins")
    if len(rows) > 5:
        print(f"  ... and {len(rows) - 5} more")
else:
    print("  None")

print()
print('=== In Progress Tasks (Being Worked On) ===')
c.execute("""SELECT id, title, assignee_id, reward FROM tasks 
             WHERE status = 'in_progress' ORDER BY updated_at DESC""")
rows = c.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0][:10]}... | {row[1][:25]} | Worker: {row[2][:8] if row[2] else 'N/A'}...")
else:
    print("  None")

print()
print('=== Open Tasks (Available to Claim) ===')
c.execute("""SELECT id, title, reward FROM tasks 
             WHERE status = 'open' ORDER BY created_at DESC""")
rows = c.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0][:10]}... | {row[1][:25]} | {row[2]} coins")
else:
    print("  None")

print()
print('=== Completed Tasks ===')
c.execute("""SELECT id, title, reward FROM tasks 
             WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 5""")
rows = c.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0][:10]}... | {row[1][:25]} | {row[2]} coins")
else:
    print("  None")

conn.close()
