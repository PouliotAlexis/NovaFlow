"""
NovaFlow - RAG Cog (Commandes slash pour l'assistant IA)

Expose les commandes /ask et /cours qui utilisent le moteur RAG
(ChromaDB + LLM) pour répondre aux questions de cours.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from app.services.ai_engine import chat
from app.services.context_builder import ContextBuilder
from app.services.rag_engine.ingest import query_rag


# ── Constantes Discord ─────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 2000


def _split_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Découpe un message long en blocs ≤ limit caractères."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break

        # Chercher le dernier saut de ligne avant la limite
        split_pos = text.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = limit  # Couper au milieu si pas de saut de ligne

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")

    return chunks


class RagCog(commands.Cog):
    """Commandes slash liées au moteur RAG et à l'assistant IA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /ask ─────────────────────────────────────────────────────
    @app_commands.command(
        name="ask",
        description="Pose une question à NovaFlow (avec contexte de tes documents)"
    )
    @app_commands.describe(
        question="Ta question",
        cours="ID du cours pour filtrer le contexte (optionnel)"
    )
    async def ask_command(
        self,
        interaction: discord.Interaction,
        question: str,
        cours: Optional[str] = None,
    ):
        # Defer car la réponse peut prendre du temps (RAG + LLM)
        await interaction.response.defer(thinking=True)

        try:
            # Construction du contexte via les services existants
            if cours:
                context = ContextBuilder.build_course_context(
                    course_id=cours,
                    user_query=question
                )
            else:
                context = ContextBuilder.build_global_context(
                    user_query=question,
                    include_rag=True
                )

            # Appel au LLM
            response_text = await chat(
                prompt=question,
                context=context,
            )

            # Construire l'embed de réponse
            embed = discord.Embed(
                title="💡 Réponse de NovaFlow",
                color=discord.Color.from_rgb(99, 102, 241),  # Indigo
            )

            # Découper la réponse si elle est trop longue
            response_chunks = _split_message(response_text, 4000)  # Limite embed description
            embed.description = response_chunks[0]

            if cours:
                embed.set_footer(text=f"📚 Contexte : Cours {cours}")
            else:
                embed.set_footer(text="🌐 Contexte : Global")

            await interaction.followup.send(embed=embed)

            # Envoyer les blocs supplémentaires en messages séparés
            for chunk in response_chunks[1:]:
                extra_embed = discord.Embed(
                    description=chunk,
                    color=discord.Color.from_rgb(99, 102, 241),
                )
                await interaction.followup.send(embed=extra_embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Erreur",
                description=f"Impossible de répondre : ```{str(e)[:500]}```",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=error_embed)

    # ── /search ──────────────────────────────────────────────────
    @app_commands.command(
        name="search",
        description="Recherche dans tes documents indexés (RAG seulement, sans LLM)"
    )
    @app_commands.describe(
        query="Ce que tu cherches",
        cours="ID du cours (optionnel)",
        resultats="Nombre de résultats (défaut: 3)"
    )
    async def search_command(
        self,
        interaction: discord.Interaction,
        query: str,
        cours: Optional[str] = None,
        resultats: Optional[int] = 3,
    ):
        await interaction.response.defer(thinking=True)

        try:
            context = query_rag(
                query=query,
                n_results=min(resultats or 3, 10),
                course_id=cours,
            )

            if not context or context.strip() == "":
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="🔍 Aucun résultat",
                        description="Aucun document pertinent trouvé pour cette recherche.",
                        color=discord.Color.orange(),
                    )
                )
                return

            embed = discord.Embed(
                title=f"🔍 Résultats pour « {query[:80]} »",
                description=context[:4000],
                color=discord.Color.from_rgb(16, 185, 129),  # Emerald
            )
            if cours:
                embed.set_footer(text=f"📚 Filtré par cours {cours}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Erreur de recherche",
                    description=str(e)[:500],
                    color=discord.Color.red(),
                )
            )


async def setup(bot: commands.Bot):
    """Point d'entrée pour charger le cog."""
    await bot.add_cog(RagCog(bot))
