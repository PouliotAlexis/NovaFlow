import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.database import engine
from sqlalchemy import text

def add_columns():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE moodle_config ADD COLUMN token VARCHAR"))
            print("Added token column")
        except Exception as e:
            print(f"Token column might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE moodle_config ADD COLUMN sesskey VARCHAR"))
            print("Added sesskey column")
        except Exception as e:
            print(f"Sesskey column might already exist: {e}")

if __name__ == "__main__":
    add_columns()
