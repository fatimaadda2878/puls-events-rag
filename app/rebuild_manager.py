from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime, timezone

from .config import REBUILD_STATUS_PATH
from .indexer import build_index


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RebuildManager:
    """Un seul rebuild à la fois, exécuté hors de la requête HTTP."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._state = {
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "events_indexed": 0,
            "documents_indexed": 0,
            "last_result": None,
            "last_error": None,
        }
        self._persist()

    def snapshot(self) -> dict:
        with self._state_lock:
            return dict(self._state)

    def _set(self, **values):
        with self._state_lock:
            self._state.update(values)
        self._persist()

    def _persist(self):
        try:
            REBUILD_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            REBUILD_STATUS_PATH.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            # Le statut en mémoire reste fonctionnel même si l'écriture échoue.
            pass

    def start(self, on_success=None) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False

            self._thread = threading.Thread(
                target=self._run,
                kwargs={"on_success": on_success},
                name="puls-events-rebuild",
                daemon=True,
            )
            self._thread.start()
            return True

    def _run(self, on_success=None):
        self._set(
            status="running",
            started_at=_utcnow(),
            finished_at=None,
            events_indexed=0,
            documents_indexed=0,
            last_result=None,
            last_error=None,
        )

        def progress(data: dict):
            self._set(
                events_indexed=data.get("events_indexed", 0),
                documents_indexed=data.get("documents_indexed", 0),
            )

        try:
            result = build_index(progress_callback=progress)
            if on_success:
                on_success()
            self._set(
                status="done",
                finished_at=_utcnow(),
                events_indexed=result.get("events_indexed", 0),
                documents_indexed=result.get("documents_indexed", 0),
                last_result=result,
                last_error=None,
            )
        except Exception as exc:
            self._set(
                status="failed",
                finished_at=_utcnow(),
                last_error=(
                    f"{type(exc).__name__}: {exc}\n"
                    f"{traceback.format_exc(limit=6)}"
                ),
            )


rebuild_manager = RebuildManager()
