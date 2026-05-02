"""
styled_widgets.py — Widgets CTk réutilisables pour TreeForge.

STATUT v1.0 : fichier réservé — non utilisé en production.
Les widgets ci-dessous sont des CANDIDATS identifiés lors du développement
de generator_tab, recaper_tab et templates_tab.

À implémenter et brancher dans un refactoring post-v1.0 pour éviter
la duplication de code entre les onglets.

─────────────────────────────────────────────────────────────────────────────
CANDIDATS IDENTIFIÉS
─────────────────────────────────────────────────────────────────────────────

1. FolderPicker
   Duo Entry(readonly) + Button("📂 Choisir…") pour sélectionner un dossier.
   Utilisé dans : GeneratorTab, RecaperTab (×2), TemplatesTab.

   Interface souhaitée :
       picker = FolderPicker(parent, label="Destination", on_change=callback)
       picker.get()   → str (chemin sélectionné ou "")
       picker.set(path)
       picker.clear()

2. SectionLabel
   Label bold Consolas avec séparateur horizontal en dessous.
   Utilisé comme titre de section dans le panneau droit du GeneratorTab
   et dans RecaperTab.

   Interface souhaitée :
       SectionLabel(parent, text="Mode de parsing")

3. SeparatorLine
   CTkFrame height=1 avec fg_color adaptatif light/dark.
   Utilisé entre chaque section du panneau droit.

   Interface souhaitée :
       SeparatorLine(parent).pack(fill="x", padx=12, pady=8)

─────────────────────────────────────────────────────────────────────────────
"""

# Rien à importer pour l'instant — ce fichier sera complété post-v1.0.