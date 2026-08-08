from __future__ import annotations

"""
Compatibilité SDK Mistral :
- SDK v1 : from mistralai import Mistral
- SDK v2 : from mistralai.client import Mistral

Le projet accepte les deux formes afin d'éviter le bug d'import déjà rencontré.
"""

try:
    from mistralai import Mistral  # SDK v1
except ImportError:  # pragma: no cover - dépend de la version installée
    from mistralai.client import Mistral  # SDK v2

__all__ = ["Mistral"]
