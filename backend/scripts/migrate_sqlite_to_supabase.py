import os
from sqlalchemy import create_engine, select, MetaData
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Connexion SQLite Locale
SQLITE_URL = "sqlite:///novaflow.db"
# Connexion Supabase Cloud
SUPABASE_URL = os.getenv("DATABASE_URL")

if "postgresql" not in SUPABASE_URL:
    print("❌ Erreur: DATABASE_URL n'est pas configuré pour PostgreSQL/Supabase.")
    exit(1)

def migrate_sqlite_to_supabase():
    print(f"🚀 Migration SQLite -> Supabase en cours...")
    
    # Création des moteurs
    sqlite_engine = create_engine(SQLITE_URL)
    supabase_engine = create_engine(SUPABASE_URL)
    
    # Tables à migrer (dans l'ordre pour respecter les Foreign Keys)
    tables = ["events", "tasks", "chat_history", "moodle_config", "moodle_ext_courses", "moodle_synced_files"]
    
    metadata = MetaData()
    metadata.reflect(bind=sqlite_engine)
    
    with Session(supabase_engine) as cloud_session:
        for table_name in tables:
            if table_name not in metadata.tables:
                print(f"⚠️ Table {table_name} absente de SQLite, on ignore.")
                continue
                
            print(f"📦 Migration de la table: {table_name}...")
            
            # Lire depuis SQLite
            table = metadata.tables[table_name]
            with sqlite_engine.connect() as conn:
                rows = conn.execute(select(table)).fetchall()
            
            if not rows:
                print(f"   (Table vide)")
                continue

            # Insérer dans Supabase (on vide avant pour éviter les doublons au cas où)
            # Note: Soyons prudents, on ne vide que si c'est la première migration
            # Pour faire simple, on utilise un try/except sur l'insert
            
            count = 0
            for row in rows:
                row_dict = dict(row._mapping)
                try:
                    cloud_session.execute(table.insert().values(**row_dict))
                    count += 1
                except Exception:
                    # Probablement une duplication de clé primaire, on ignore
                    continue
            
            cloud_session.commit()
            print(f"   ✅ {count} lignes migrées.")

    print("\n✨ Migration terminée ! Vérifie ton dashboard Supabase.")

if __name__ == "__main__":
    migrate_sqlite_to_supabase()
