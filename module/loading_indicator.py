"""Visualisiert parallele Aufgabenlisten im ruhigen, klinischen Design."""

from __future__ import annotations
from contextlib import contextmanager
from typing import Iterable
import streamlit as st

# Das CSS wird EINMALIG außerhalb der Schleife definiert.
# So wird die Animation nicht bei jedem Fortschritt zurückgesetzt!
SPINNER_CSS = """
<style>
@keyframes spin-animation {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.spinning-icon {
    display: inline-block;
    animation: spin-animation 1.2s linear infinite;
    transform-origin: 50% 45%; /* Zentriert die Drehung perfekt */
    margin-right: 6px;
    width: 14px;
    text-align: center;
}
.task-icon {
    display: inline-block;
    margin-right: 6px;
    width: 14px;
    text-align: center;
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
                # ERLEDIGT
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #81C784; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>✓</span> {task}</div>"
                )
            elif index == self.current_index:
                # AKTIV (Hier greift jetzt die ungestörte CSS-Klasse)
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #E0E0E0; font-size: 0.95rem;'>"
                    f"<span class='spinning-icon'>↻</span> {task}</div>"
                )
            else:
                # AUSSTEHEND
                lines.append(
                    f"<div style='margin-bottom: 8px; color: #757575; font-size: 0.95rem;'>"
                    f"<span class='task-icon'>○</span> {task}</div>"
                )
        self.placeholder.markdown("".join(lines), unsafe_allow_html=True)


@contextmanager
def task_spinner(spinner_text: str, tasks: Iterable[str]):
    # CSS wird nur einmal eingefügt
    st.markdown(SPINNER_CSS, unsafe_allow_html=True)
    
    with st.status(spinner_text, expanded=True) as status:
        placeholder = st.empty()
        tracker = _TaskTracker(list(tasks), placeholder)

        try:
            yield tracker
        finally:
            tracker.complete()
            status.update(label="Abgeschlossen", state="complete", expanded=False)
