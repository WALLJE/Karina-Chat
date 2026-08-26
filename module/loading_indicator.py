"""Visualisiert parallele Aufgabenlisten im AMBOSS-Stil.

Nutzt die native st.status-Komponente von Streamlit, um einen
Ladekreis zu zeigen, der sich bei Abschluss in einen Haken verwandelt.
"""

from __future__ import annotations
from contextlib import contextmanager
from typing import Iterable
import streamlit as st

class _TaskTracker:
    """Verwaltet den Fortschritt und rendert die Liste im Status-Container."""

    def __init__(self, tasks: list[str], placeholder: "st.delta_generator.DeltaGenerator"):
        self.tasks = tasks
        self.current_index = 0
        self.placeholder = placeholder
        self._render()

    def advance(self, steps: int = 1) -> None:
        """Schaltet auf die nächste Aufgabe weiter und aktualisiert die Anzeige."""
        self.current_index = min(len(self.tasks), self.current_index + steps)
        self._render()

    def complete(self) -> None:
        """Markiert alle Aufgaben als erledigt."""
        self.current_index = len(self.tasks)
        self._render()

    def _render(self) -> None:
        """Erzeugt die HTML-Liste, optimiert für den dunklen Modus."""
        lines = []
        for index, task in enumerate(self.tasks):
            if index < self.current_index:
                # Erledigt (Grüner Haken)
                lines.append(
                    f"<div style='margin-bottom: 6px; color: #4CAF50; font-size: 0.95rem;'>"
                    f"✓ {task}</div>"
                )
            elif index == self.current_index:
                # In Bearbeitung (Blau markiert, etwas dicker)
                lines.append(
                    f"<div style='margin-bottom: 6px; color: #64B5F6; font-size: 0.95rem; font-weight: 600;'>"
                    f"↻ {task}</div>"
                )
            else:
                # Ausstehend (Ausgegraut)
                lines.append(
                    f"<div style='margin-bottom: 6px; color: #888888; font-size: 0.95rem;'>"
                    f"○ {task}</div>"
                )

        self.placeholder.markdown("".join(lines), unsafe_allow_html=True)


@contextmanager
def task_spinner(spinner_text: str, tasks: Iterable[str]):
    """Kombiniert st.status mit der schrittweisen Aufgabenliste."""
    
    # st.status erzeugt automatisch den drehenden Kreis.
    # Bei Abschluss wird dieser durch Streamlit in einen Haken verwandelt.
    with st.status(spinner_text, expanded=True) as status:
        placeholder = st.empty()
        tracker = _TaskTracker(list(tasks), placeholder)

        try:
            yield tracker
        finally:
            # Nach Abschluss wird alles abgehakt und die Box automatisch eingeklappt.
            tracker.complete()
            status.update(label="Antwort bereit", state="complete", expanded=False)
