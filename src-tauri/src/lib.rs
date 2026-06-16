use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};

static BACKEND_CHILD: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

fn get_backend_child() -> &'static Mutex<Option<Child>> {
  BACKEND_CHILD.get_or_init(|| Mutex::new(None))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let app = tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Démarrage automatique du backend FastAPI en mode Debug
      #[cfg(debug_assertions)]
      {
        println!("[Tauri] Démarrage du backend FastAPI en arrière-plan...");
        
        let python_path = "../backend/venv/Scripts/python.exe";
        let mut cmd = if std::path::Path::new(python_path).exists() {
          Command::new(python_path)
        } else {
          Command::new("python")
        };

        cmd.args(&["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]);
        cmd.current_dir("../backend");

        // Masquer la fenêtre de console sous Windows (Désactivé pour Playwright)
        #[cfg(target_os = "windows")]
        {
          // use std::os::windows::process::CommandExt;
          // cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        match cmd.spawn() {
          Ok(child) => {
            println!("[Tauri] Backend FastAPI démarré avec succès (PID={})", child.id());
            *get_backend_child().lock().unwrap() = Some(child);
          }
          Err(e) => {
            eprintln!("[Tauri] Erreur de démarrage du backend FastAPI : {}", e);
          }
        }
      }

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application");

  app.run(|_app_handle, event| {
    if let tauri::RunEvent::Exit = event {
      let mut lock = get_backend_child().lock().unwrap();
      if let Some(mut child) = lock.take() {
        println!("[Tauri] Arrêt du backend FastAPI...");
        let _ = child.kill();
      }
    }
  });
}
