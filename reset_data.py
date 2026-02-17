import sys
import os

# Ajout du chemin backend pour les imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from services.cleanup_utils import reset_all_data

if __name__ == "__main__":
    print("🧹 Resetting all data...")
    results = reset_all_data()
    for file, status in results.items():
        print(f" - {file}: {status}")
    print("✅ Done.")
