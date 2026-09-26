"""
NovaFlow - Composants interactifs Discord (Boutons, Formulaires, Sélecteurs)

Vues réutilisables pour les interactions sans texte.
"""

import discord
from app.services.task_manager import TaskManager


class DailyCheckinView(discord.ui.View):
    """Vue du check-in quotidien du soir avec boutons de feedback."""

    def __init__(self):
        super().__init__(timeout=None)  # Pas d'expiration

    @discord.ui.button(
        label="Objectifs atteints",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="checkin_success",
    )
    async def on_success(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ Excellent travail !",
            description="Ta session a été enregistrée. Continue comme ça ! 💪",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label="Partiellement fait",
        style=discord.ButtonStyle.primary,
        emoji="🔄",
        custom_id="checkin_partial",
    )
    async def on_partial(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔄 C'est noté !",
            description="Pas de pression. Les créneaux non terminés seront reportés demain.",
            color=discord.Color.from_rgb(59, 130, 246),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label="Session reportée",
        style=discord.ButtonStyle.secondary,
        emoji="⏳",
        custom_id="checkin_reschedule",
    )
    async def on_reschedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⏳ Compris",
            description="Les créneaux de demain seront ajustés en conséquence.",
            color=discord.Color.greyple(),
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ConfirmDeleteView(discord.ui.View):
    """Vue de confirmation pour la suppression d'une tâche."""

    def __init__(self, task_id: str, task_title: str):
        super().__init__(timeout=60)  # 60 secondes avant expiration
        self.task_id = task_id
        self.task_title = task_title

    @discord.ui.button(
        label="Confirmer la suppression",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
    )
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        tm = TaskManager.instance()
        success = tm.delete_task(self.task_id)

        if success:
            embed = discord.Embed(
                title="🗑️ Tâche supprimée",
                description=f"**{self.task_title}** a été supprimée.",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="La tâche n'existe plus.",
                color=discord.Color.red(),
            )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label="Annuler",
        style=discord.ButtonStyle.secondary,
        emoji="↩️",
    )
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="↩️ Annulé",
            description="La suppression a été annulée.",
            color=discord.Color.greyple(),
        )
        await interaction.response.edit_message(embed=embed, view=None)


class TaskPrioritySelect(discord.ui.View):
    """Sélecteur de priorité pour une tâche."""

    def __init__(self, task_id: str):
        super().__init__(timeout=60)
        self.task_id = task_id

    @discord.ui.select(
        placeholder="Choisir la priorité...",
        options=[
            discord.SelectOption(label="Haute", value="high", emoji="🔴"),
            discord.SelectOption(label="Moyenne", value="medium", emoji="🟡"),
            discord.SelectOption(label="Basse", value="low", emoji="🟢"),
        ],
    )
    async def priority_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        tm = TaskManager.instance()
        priority = select.values[0]
        result = tm.update_task(self.task_id, {"priority": priority})

        emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
        label = {"high": "Haute", "medium": "Moyenne", "low": "Basse"}.get(priority, priority)

        if result:
            embed = discord.Embed(
                title=f"{emoji} Priorité mise à jour",
                description=f"**{result['title']}** → Priorité **{label}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Tâche introuvable.",
                color=discord.Color.red(),
            )
        await interaction.response.edit_message(embed=embed, view=None)
