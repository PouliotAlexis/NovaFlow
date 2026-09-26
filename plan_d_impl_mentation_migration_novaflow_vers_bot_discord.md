# Plan d'implémentation : Migration NovaFlow vers Bot Discord

Ce document détaille la démarche pas-à-pas pour transformer le backend FastAPI de **NovaFlow** en un **bot Discord autonome**, tout en réutilisant l'indexation ChromaDB existante et la logique de synchronisation Moodle.

---

## 1. Architecture cible

L'objectif est d'isoler la logique métier des protocoles de communication afin que le bot Discord consomme directement des services Python indépendants.

```text
backend/
├── app/
│   ├── core/
│   │   ├── config.py              # Variables d'environnement & jetons d'accès
│   │   └── database.py            # SQLite pour la persistance locale de l'état
│   ├── data/
│   │   └── chromadb_v2/           # Base vectorielle persistante (inchangée)
│   ├── services/                  # Logique métier pure (découplée de FastAPI et Discord)
│   │   ├── moodle_service.py      # Récupération et parsing des devoirs / cours
│   │   ├── rag_service.py         # Interrogation ChromaDB + LLM
│   │   └── scheduler_service.py   # Algorithme d'optimisation d'horaire et priorités
│   ├── bot/
│   │   ├── client.py              # Configuration du client Discord et intents
│   │   ├── cogs/
│   │   │   ├── schedule_cog.py    # Commandes slash : planning et calendrier
│   │   │   ├── rag_cog.py         # Commandes slash : questions de cours et révisions
│   │   │   └── tasks_cog.py       # Tâches périodiques : sync Moodle & briefings
│   │   └── ui/
│   │       └── views.py           # Composants interactifs (boutons, formulaires)
│   └── main_bot.py                # Point d'entrée pour l'exécution du bot
```

---

## 2. Phase 1 : Initialisation & Configuration de l'environnement

### 2.1 Branche de travail
Créer et basculer sur une branche dédiée à partir de la version locale fonctionnelle :
```bash
git checkout -b feature/discord-bot
```

### 2.2 Dépendances
Ajouter la bibliothèque `discord.py` à l'environnement virtuel :
```bash
pip install discord.py python-dotenv
```

### 2.3 Portail Développeur Discord
1. Créer une application sur le **Discord Developer Portal**.
2. Dans l'onglet **Bot**, activer les intents nécessaires :
   * **Message Content Intent** (si interactions par message texte direct / MP).
3. Générer l'URL d'invitation avec les permissions :
   * `Send Messages`
   * `Use Slash Commands`
   * `Embed Links`
   * `Attach Files`
4. Renseigner les variables dans `backend/.env` :
   ```env
   DISCORD_BOT_TOKEN="votre_token_secret"
   DISCORD_USER_ID="votre_identifiant_discord_numerique"
   ```

---

## 3. Phase 2 : Extraction des Services Métier

Les contrôleurs FastAPI (`backend/app/api/routes/`) doivent être épurés de tout objet `Request`, `Response` ou `HTTPException` pour devenir des modules Python réutilisables.

### 3.1 Service Moodle (`app/services/moodle_service.py`)
* Extraire la logique d'authentification et de requêtes HTTP vers l'API Moodle.
* Définir une fonction pure retournant des structures Python typées :
  ```python
  from typing import List, Dict, Any

  async def fetch_moodle_assignments() -> List[Dict[str, Any]]:
      """
      Retourne la liste des devoirs Moodle :
      [{"id": 1, "title": "Devoir 1", "course": "IFT1015", "due_date": "2026-10-05T23:59:00"}]
      """
      # Implémentation isolée de FastAPI
      pass
  ```

### 3.2 Service RAG & IA (`app/services/rag_service.py`)
* Conserver le pointage sur le dossier existant `backend/app/data/chromadb_v2/`.
* Exposer la fonction d'interrogation documentaire :
  ```python
  async def ask_assistant(query: str, course_filter: str = None) -> str:
      """
      1. Calcule l'embedding de la requête
      2. Effectue la recherche de similarité dans ChromaDB
      3. Construit le prompt avec le contexte récupéré
      4. Appelle le LLM et renvoie la réponse sous forme de texte
      """
      pass
  ```

### 3.3 Service de Planification (`app/services/scheduler_service.py`)
* Implémenter l'algorithme d'arbitrage de charge de travail :
  $$\text{Priorité} = \frac{\text{Coefficient de l'évaluation} \times \text{Indice de difficulté}}{\text{Jours restants} + 1}$$
* Générer les créneaux recommandés pour les sessions d'étude en fonction de la liste des devoirs non terminés.

---

## 4. Phase 3 : Implémentation du Bot Discord

### 4.1 Point d'entrée (`app/main_bot.py`)
```python
import asyncio
import discord
from discord.ext import commands
from app.core.config import settings

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot connecté : {bot.user} (ID: {bot.user.id})")

async def main():
    async with bot:
        await bot.load_extension("app.bot.cogs.schedule_cog")
        await bot.load_extension("app.bot.cogs.rag_cog")
        await bot.load_extension("app.bot.cogs.tasks_cog")
        await bot.start(settings.DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2 Module RAG (`app/bot/cogs/rag_cog.py`)
* **Gestion du délai de réponse :** Discord impose un délai de 3 secondes avant expiration de la requête. Utiliser `await interaction.response.defer()` pendant que ChromaDB et le LLM travaillent, puis retourner le résultat avec `await interaction.followup.send(...)`.
* **Limite de taille :** Découper les réponses dépassant 2 000 caractères en blocs consécutifs.

### 4.3 Module Calendrier (`app/bot/cogs/schedule_cog.py`)
* Commande `/devoirs` : Renvoie un Embed Discord récapitulant les échéances classées par ordre d'urgence.
* Commande `/planifier` : Présente les blocs d'étude suggérés pour les 48 prochaines heures.

---

## 5. Phase 4 : Tâches d'arrière-plan proactives (`tasks_cog.py`)

Ce module exploite `discord.ext.tasks` pour déclencher des actions automatiques sans requête utilisateur préalable.

```python
import datetime
from discord.ext import tasks, commands
from app.core.config import settings
from app.services.moodle_service import fetch_moodle_assignments
from app.services.scheduler_service import generate_daily_schedule
from app.bot.ui.views import DailyCheckinView

class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moodle_sync.start()
        self.scheduled_briefings.start()

    def cog_unload(self):
        self.moodle_sync.cancel()
        self.scheduled_briefings.cancel()

    @tasks.loop(hours=3)
    async def moodle_sync(self):
        """Vérifie les mises à jour Moodle toutes les 3 heures."""
        updates = await fetch_moodle_assignments()
        if updates:
            user = await self.bot.fetch_user(settings.DISCORD_USER_ID)
            await user.send(f"📚 **Nouvel élément Moodle détecté :** {updates[0]['title']}")

    @tasks.loop(minutes=1)
    async def scheduled_briefings(self):
        """Déclenche les notifications horaires clés."""
        current_time = datetime.datetime.now().strftime("%H:%M")
        
        # Briefing du matin (07:30)
        if current_time == "07:30":
            user = await self.bot.fetch_user(settings.DISCORD_USER_ID)
            embed = await generate_daily_schedule()
            await user.send(embed=embed)

        # Check-in du soir (21:30)
        elif current_time == "21:30":
            user = await self.bot.fetch_user(settings.DISCORD_USER_ID)
            view = DailyCheckinView()
            await user.send("Bilan du soir : As-tu pu finaliser tes objectifs d'étude ?", view=view)
```

---

## 6. Phase 5 : Composants interactifs (`app/bot/ui/views.py`)

Les vues Discord permettent d'interagir sans taper de texte (boutons et sélecteurs).

```python
import discord

class DailyCheckinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Objectifs atteints", style=discord.ButtonStyle.success, emoji="✅")
    async def on_success(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Excellent travail ! Session enregistrée.", view=None)

    @discord.ui.button(label="Session reportée", style=discord.ButtonStyle.secondary, emoji="⏳")
    async def on_reschedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="C'est noté. Les créneaux de demain seront ajustés.", view=None)
```

---

## 7. Phase 6 : Protocole de Validation & Recette

| Étape | Vérification | Résultat attendu |
| :--- | :--- | :--- |
| **1. Services purs** | Exécution de `rag_service.py` via un script de test local | Rendu du LLM basé sur le dossier `chromadb_v2` sans dépendance HTTP |
| **2. Connexion** | Exécution de `python app/main_bot.py` | Statut « En ligne » sur Discord et synchronisation des commandes slash (`tree.sync`) |
| **3. Commande `/ask`** | Envoi d'une question sur un cours indexé | Réception de l'Embed ou texte avec indicateur de chargement (`defer`) |
| **4. Check-in interactif**| Clic sur les boutons de la vue `DailyCheckinView` | Mise à jour immédiate du message et enregistrement dans la base locale |
| **5. Boucle périodique** | Déclenchement forcé de la tâche `moodle_sync` | Notification push reçue sur le client Discord (mobile/PC) |