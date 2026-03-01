import sys
import os
sys.path.append('c:/Users/alexi/GIT/NovaFlow/backend')
from services.google_service import upload_files_batch_to_drive

with open('test_sync.txt', 'w', encoding='utf-8') as f:
    f.write('hello world')

print("Lancement test batch...")
try:
    upload_files_batch_to_drive([('test_sync.txt', 'Test_Folder/test_sync.txt')])
    print("Fini avec succes.")
except Exception as e:
    print(f"Exception: {e}")
