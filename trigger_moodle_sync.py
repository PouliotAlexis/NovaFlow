import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.services.moodle_extension_service import process_moodle_files

import threading
import time

print("📤 Starting full Google Drive migration for all local Moodle files...")
from services.google_service import upload_file_to_drive
import glob

target_dir = os.path.expanduser("~/Documents/NovaFlow_Courses")
files = glob.glob(os.path.join(target_dir, "**/*.*"), recursive=True)

uploaded_count = 0
for test_file in files:
    if os.path.isdir(test_file):
        continue
    rel_path = os.path.relpath(test_file, target_dir).replace("\\", "/")
    print(f"[{uploaded_count+1}/{len(files)}] Uploading: {rel_path}...")
    upload_file_to_drive(test_file, rel_path)
    uploaded_count += 1

print(f"✅ Migration complete. {uploaded_count} files processed.")
