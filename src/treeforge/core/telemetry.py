"""
core/telemetry.py
==================
Module de télémétrie TreeForge — Analytics + Crash Reporting.

Outils :
  - PostHog  : product analytics (events d'utilisation)
  - Sentry   : crash reporting (exceptions non gérées)

Configuration :
  Remplacer les deux placeholders ci-dessous par tes vraies clés :
    POSTHOG_API_KEY  → posthog.com  → Settings → Project API Key
    SENTRY_DSN       → sentry.io    → Project → Settings → Client Keys (DSN)

Consentement :
  Le module vérifie ~/.treeforge/settings.json avant tout envoi.
  Si l'utilisateur a refusé → aucune donnée n'est envoyée, jamais.

Données collectées (anonymes) :
  - Version de TreeForge
  - Nom de l'événement (ex: "app_launched", "generation_success")
  - Paramètres de l'événement (ex: nb_files, mode_parsing)
  - En cas de crash : stack trace + OS + version Python

Données NON collectées :
  - Nom, email, IP
  - Chemins de fichiers locaux
  - Contenu des arborescences
"""
from __future__ import annotations

import json
import platform
import uuid
from pathlib import Path
from typing import Any

from treeforge.config import __version__

# ── Clés à remplacer par les vraies valeurs ───────────────────────────────────
POSTHOG_API_KEY = "REMPLACER_PAR_TA_CLE_POSTHOG"
SENTRY_DSN      = "REMPLACER_PAR_TON_DSN_SENTRY"

# ── Fichier de préférences utilisateur ───────────────────────────────────────
_SETTINGS_PATH = Path.home() / ".treeforge" / "settings.json"

# ── État interne du module ────────────────────────────────────────────────────
_posthog_client = None
_sentry_ready   = False
_user_id: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Persistance des préférences
# ─────────────────────────────────────────────────────────────────────────────

def _load_settings() -> dict:
    """Charge les préférences depuis le fichier JSON."""
    try:
        if _SETTINGS_PATH.exists():
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(data: dict) -> None:
    """Sauvegarde les préférences dans le fichier JSON."""
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# API publique — consentement
# ─────────────────────────────────────────────────────────────────────────────

def has_answered_consent() -> bool:
    """Retourne True si l'utilisateur a déjà répondu (oui ou non)."""
    return "telemetry_enabled" in _load_settings()


def is_enabled() -> bool:
    """Retourne True si l'utilisateur a accepté la télémétrie."""
    return _load_settings().get("telemetry_enabled", False)


def set_consent(enabled: bool) -> None:
    """
    Enregistre le choix de l'utilisateur.
    
    Args:
        enabled: True = accepté, False = refusé
    """
    settings = _load_settings()
    settings["telemetry_enabled"] = enabled
    _save_settings(settings)


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init() -> None:
    """
    Initialise PostHog et Sentry si l'utilisateur a accepté.
    À appeler une seule fois au démarrage, après avoir vérifié le consentement.
    """
    global _user_id, _posthog_client, _sentry_ready

    # Pas de télémétrie si refusé
    if not is_enabled():
        return

    # Pas de télémétrie si les clés n'ont pas été configurées
    if "REMPLACER" in POSTHOG_API_KEY or "REMPLACER" in SENTRY_DSN:
        return

    # Générer un ID anonyme stable si absent
    settings = _load_settings()
    if "anonymous_id" not in settings:
        settings["anonymous_id"] = str(uuid.uuid4())
        _save_settings(settings)
    _user_id = settings["anonymous_id"]

    # ── PostHog ───────────────────────────────────────────────────────────────
    try:
        import posthog as ph
        ph.project_api_key = POSTHOG_API_KEY
        ph.host            = "https://app.posthog.com"
        ph.disabled        = False
        _posthog_client    = ph
    except Exception:
        pass  # posthog non installé → télémétrie analytics silencieusement désactivée

    # ── Sentry ────────────────────────────────────────────────────────────────
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn                = SENTRY_DSN,
            release            = f"treeforge@{__version__}",
            environment        = "production",
            traces_sample_rate = 0.1,
            before_send        = _sentry_filter,
        )
        _sentry_ready = True
    except Exception:
        pass  # sentry non installé → crash reporting silencieusement désactivé


# ─────────────────────────────────────────────────────────────────────────────
# Filtre Sentry — anonymisation des chemins
# ─────────────────────────────────────────────────────────────────────────────

def _sentry_filter(event: dict, hint: dict) -> dict:
    """
    Filtre Sentry : retire tous les chemins locaux des stack traces
    pour garantir l'anonymat.
    """
    try:
        for exc in event.get("exception", {}).get("values", []):
            for frame in exc.get("stacktrace", {}).get("frames", []):
                if "abs_path" in frame:
                    frame["abs_path"] = Path(frame["abs_path"]).name
                if "filename" in frame:
                    frame["filename"] = Path(frame["filename"]).name
    except Exception:
        pass
    return event


# ─────────────────────────────────────────────────────────────────────────────
# API publique — envoi d'événements
# ─────────────────────────────────────────────────────────────────────────────

def capture(event_name: str, properties: dict[str, Any] | None = None) -> None:
    """
    Envoie un événement analytics à PostHog.

    Exemples :
        capture("app_launched")
        capture("generation_success", {"nb_files": 12, "mode": "Souple"})
        capture("template_used", {"template": "react-vite"})
        capture("revers_recaper_used", {"nb_files_restored": 8})
    """
    if not is_enabled() or _posthog_client is None or _user_id is None:
        return

    try:
        props = properties or {}
        # Ajout automatique des métadonnées de contexte
        props.setdefault("app_version", __version__)
        props.setdefault("os",          platform.system())
        props.setdefault("os_version",  platform.version())
        props.setdefault("python",      platform.python_version())

        _posthog_client.capture(
            distinct_id = _user_id,
            event       = event_name,
            properties  = props,
        )
    except Exception:
        pass  # jamais de crash à cause de la télémétrie


def capture_error(message: str, context: dict[str, Any] | None = None) -> None:
    """
    Envoie une erreur manuelle à Sentry (pour les erreurs gérées
    mais que tu veux quand même tracer).

    Exemple :
        capture_error("Parser a échoué silencieusement", {"mode": mode})
    """
    if not is_enabled() or not _sentry_ready:
        return

    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            scope.set_extra("app_version", __version__)
            sentry_sdk.capture_message(message, level="error")
    except Exception:
        pass  # jamais de crash à cause de la télémétrie
