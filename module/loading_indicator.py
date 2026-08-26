"""Visualisiert parallele Aufgabenlisten im ruhigen, klinischen Design."""

from __future__ import annotations
from contextlib import contextmanager
from typing import Iterable
import streamlit as st

# CSS mit einem echten, mathematisch perfekten Ladekreis statt eines Textzeichens
SPINNER_CSS = """
<style>
@keyframes spin-animation {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.css-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(100, 181, 246, 0.2); /* Halbtransparenter blauer Hintergrundring */
    border-top-color: #64B5F6; /* Kräftiges AMBOSS-Blau für den rotierenden Teil */
    border-radius: 50%; /* Macht das Viereck zu einem perfekten Kreis */
    animation: spin-animation 0.85s linear infinite; /* Etwas schnellere, weiche Drehung */
    margin-right: 8px;
    vertical-align: -2px; /* Richtet den Kreis perfekt am Text aus */
}
.task-icon {
    display: inline-block;
    margin-right: 8px;
    width: 14px;
    text-align: center;
    font-weight: 600;
}
</style>
"""

class _TaskTracker:
    def __init__(self, tasks: list[str], placeholder: "st.delta_generator.DeltaGenerator"):
        self.tasks = tasks
        self.current_index = 0
        self.placeholder = placeholder
        self._render()

    def advance(self, steps: int = 1) -> None:
        self.current_index = min(len(self.tasks), self.current_index + steps)
        self._render()

    def complete(self) -> None:
        self.current_index = len(self.tasks)
        self._render()

    def _render(self) -> None:
        lines = []
        for index, task in enumerate(self.tasks):
            if index < self.current_index:
                # ERLEDIGT: Grüner Haken
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #81C784; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>✓</span> {task}</div>"
                )
            elif index == self.current_index:
                # AKTIV: Der neue, perfekte CSS-Spinner
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #E0E0E0; font-size: 0.95rem;'>"
                    f"<span class='css-spinner'></span> {task}</div>"
                )
            else:
                # AUSSTEHEND: Leerer Kreis
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #757575; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>○</span> {task}</div>"
                )
        self.placeholder.markdown("".join(lines), unsafe_allow_html=True)


@contextmanager
def task_spinner(spinner_text: str, tasks: Iterable[str]):
    st.markdown(SPINNER_CSS, unsafe_allow_html=True)
    
    with st.status(spinner_text, expanded=True) as status:
        placeholder = st.empty()
        tracker = _TaskTracker(list(tasks), placeholder)

        try:
            yield tracker
        finally:
            tracker.complete()
            status.update(label="Abgeschlossen", state="complete", expanded=False)
