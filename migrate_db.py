#!/usr/bin/env python3
"""
Database migration script for Claw4Task.
Adds new columns to existing tasks table without losing data.
"""

import asyncio
import sqlite3
import os

# Get database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "./claw4task.db")


def migrate_database():
    """Add new columns to tasks table."""
    print(f"🔄 Migrating database: {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(tasks)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    print(f"📊 Existing columns: {len(existing_columns)}")
    
    # New columns to add
    new_columns = {
        'deliverables': 'JSON DEFAULT "[]"',
        'examples': 'JSON DEFAULT "[]"',
        'reference_links': 'JSON DEFAULT "[]"',
        'notes_for_ai': 'TEXT',
        'required_capabilities': 'JSON DEFAULT "[]"',
        'estimated_hours': 'FLOAT',
        'complexity_level': 'INTEGER DEFAULT 3',
    }
    
    # Add missing columns
    for column, col_type in new_columns.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} {col_type}")
                print(f"  ✅ Added column: {column}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  Column {column} might already exist: {e}")
        else:
            print(f"  ⏭️  Column {column} already exists")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration completed successfully!")
    print()
    print("📝 Note: Existing tasks will have default values for new fields:")
    print("   - deliverables: []")
    print("   - examples: []")
    print("   - reference_links: []")
    print("   - required_capabilities: []")
    print("   - complexity_level: 3")
    print("   - estimated_hours: NULL")


if __name__ == "__main__":
    migrate_database()
