"""Visualisiert parallele Aufgabenlisten mit einem coolen Typewriter-Effekt.

Nutzt st.status für den Haupt-Ladekreis oben und eine CSS-Animation
für den Schreibmaschinen-Effekt der aktiven Unteraufgaben.
"""

from __future__ import annotations
from contextlib import contextmanager
from typing import Iterable
import streamlit as st

# CSS für den Typewriter-Effekt (Schreibmaschine)
# Nutzt max-width und steps(), um das Tippen von Buchstaben zu simulieren
SPINNER_CSS = """
<style>
@keyframes type-in {
    from { max-width: 0; }
    to { max-width: 100%; }
}
@keyframes blink-cursor {
    50% { border-color: transparent; }
}
.typewriter {
    display: inline-block;
    overflow: hidden;
    white-space: nowrap;
    vertical-align: bottom;
    /* Der blinkende Cursor am Ende des Textes */
    border-right: 2px solid #64B5F6; 
    /* Animation: 1.2 Sekunden Tippen (in 40 Stufen) + unendliches Blinken */
    animation: 
        type-in 1.2s steps(40, end) forwards, 
        blink-cursor 0.7s step-end infinite;
}
.task-done {
    color: #81C784;
    font-size: 0.95rem;
    margin-bottom: 8px;
}
.task-active {
    color: #E0E0E0;
    font-size: 0.95rem;
    margin-bottom: 8px;
}
.task-pending {
    color: #757575;
    font-size: 0.95rem;
    margin-bottom: 8px;
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
                # ERLEDIGT: Grüner Haken, Text ist voll sichtbar
                lines.append(
                    f"<div class='task-done'>"
                    f"<span style='margin-right: 8px;'>✓</span>{task}</div>"
                )
            elif index == self.current_index:
                # AKTIV: Blaue Pfeil-Klammer und Typewriter-Animation
                lines.append(
                    f"<div class='task-active'>"
                    f"<span style='color: #64B5F6; margin-right: 8px; font-weight: bold;'>&gt;</span>"
                    f"<span class='typewriter'>{task}</span></div>"
                )
            else:
                # AUSSTEHEND: Ausgegraut, ohne Symbol davor (durch margin eingerückt)
                lines.append(
                    f"<div class='task-pending'>"
                    f"<span style='visibility: hidden; margin-right: 8px;'>&gt;</span>{task}</div>"
                )
        self.placeholder.markdown("".join(lines), unsafe_allow_html=True)


@contextmanager
def task_spinner(spinner_text: str, tasks: Iterable[str]):
    st.markdown(SPINNER_CSS, unsafe_allow_html=True)
    
    # Der native Streamlit-Status erzeugt oben weiterhin den sich drehenden Haupt-Kreis
    with st.status(spinner_text, expanded=True) as status:
        placeholder = st.empty()
        tracker = _TaskTracker(list(tasks), placeholder)

        try:
            yield tracker
        finally:
            tracker.complete()
            status.update(label="Abgeschlossen", state="complete", expanded=False)
