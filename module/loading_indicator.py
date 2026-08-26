"""Visualisiert parallele Aufgabenlisten im ruhigen, klinischen Design.

Nutzt st.status für den Haupt-Ladekreis und eine eigene CSS-Animation
für die drehenden Kreise der aktiven Unteraufgaben.
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
        """Erzeugt die HTML-Liste mit animiertem Kreis und unauffälligen Farben."""
        
        # CSS für die Rotations-Animation des aktiven Kreises
        css = """
        <style>
        @keyframes spin-animation {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .spinning-icon {
            display: inline-block;
            animation: spin-animation 1.2s linear infinite;
            margin-right: 6px;
        }
        .task-icon {
            display: inline-block;
            margin-right: 6px;
            width: 14px;
            text-align: center;
        }
        </style>
        """
        
        lines = [css]
        for index, task in enumerate(self.tasks):
            if index < self.current_index:
                # ERLEDIGT: Haken und unauffällige Farbe (gedecktes, ruhiges Grün)
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #81C784; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>✓</span> {task}</div>"
                )
            elif index == self.current_index:
                # AKTIV: Hellgrau mit sich drehendem Kreis
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #E0E0E0; font-size: 0.95rem;'>"
                    f"<span class='spinning-icon'>↻</span> {task}</div>"
                )
            else:
                # AUSSTEHEND: Dunkleres Grau mit leerem Kreis
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #757575; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>○</span> {task}</div>"
                )

        self.placeholder.markdown("".join(lines), unsafe_allow_html=True)


@contextmanager
def task_spinner(spinner_text: str, tasks: Iterable[str]):
    """Kombiniert st.status mit der schrittweisen Aufgabenliste."""
    
    # st.status erzeugt automatisch den Haupt-Ladekreis ganz oben neben dem Text
    with st.status(spinner_text, expanded=True) as status:
        placeholder = st.empty()
        tracker = _TaskTracker(list(tasks), placeholder)

        try:
            yield tracker
        finally:
            # Nach Abschluss wird alles abgehakt und die Box automatisch eingeklappt.
            tracker.complete()
            status.update(label="Abgeschlossen", state="complete", expanded=False)
