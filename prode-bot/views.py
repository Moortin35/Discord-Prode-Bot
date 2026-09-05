import discord


class Paginador(discord.ui.View):
    """Botones ◀ ▶ para recorrer una lista de embeds ya armados.

    Numera las páginas en el footer y deshabilita los botones en los extremos.
    Discord corta los embeds en 6000 caracteres, así que los listados largos
    (el fixture completo, las predicciones de todo el torneo) tienen que
    repartirse en varias páginas en vez de mandarse en un solo mensaje.
    """

    def __init__(self, embeds, pie=None, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.indice = 0

        for i, embed in enumerate(embeds, start=1):
            texto = f"Página {i} de {len(embeds)}"
            if pie:
                texto += f" · {pie}"
            embed.set_footer(text=texto)

        self._actualizar_botones()

    def embed_actual(self):
        return self.embeds[self.indice]

    def _actualizar_botones(self):
        self.anterior.disabled = self.indice == 0
        self.siguiente.disabled = self.indice >= len(self.embeds) - 1

    async def _mover(self, interaction, paso):
        self.indice = max(0, min(self.indice + paso, len(self.embeds) - 1))
        self._actualizar_botones()
        await interaction.response.edit_message(embed=self.embed_actual(), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._mover(interaction, -1)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._mover(interaction, 1)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
