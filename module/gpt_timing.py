"""Hilfsfunktionen zum Messen der kumulierten GPT-Laufzeiten."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

import streamlit as st

T = TypeVar("T")


def messe_gpt_aktion(aktion: Callable[[], T], *, kontext: str = "") -> T:
    """Misst die Dauer einer GPT-Aktion und addiert sie im Session-State.

    Die Funktion sammelt alle Laufzeiten in ``st.session_state`` unter dem
    Schlüssel ``gpt_aktionsdauer_gesamt_sek``. Damit entsteht eine kumulierte
    Summe über die gesamte Session hinweg. Die Rohwerte bleiben absichtlich
    in Sekunden, um spätere Auswertungen (Minuten/Median/etc.) flexibel zu
    halten.
    """

    start = time.perf_counter()
    try:
        return aktion()
    finally:
        dauer = time.perf_counter() - start
        bisher = float(st.session_state.get("gpt_aktionsdauer_gesamt_sek", 0.0))
        st.session_state["gpt_aktionsdauer_gesamt_sek"] = bisher + dauer
        # Debug-Hinweis: Bei Bedarf kann hier temporär ein
        # ``st.write(kontext, dauer, st.session_state["gpt_aktionsdauer_gesamt_sek"])``
        # aktiviert werden, um einzelne Laufzeiten im UI zu prüfen.


def add_gpt_duration(dauer: float, *, kontext: str = "") -> None:
    """Addiert eine bereits gemessene Dauer zur kumulierten Session-Summe.

    Diese Funktion ist für Fälle gedacht, in denen die Messung außerhalb des
    Streamlit-Mainthreads erfolgt (z. B. in Background-Threads) und die
    Summierung erst anschließend im Hauptthread erfolgen soll.
    """

    bisher = float(st.session_state.get("gpt_aktionsdauer_gesamt_sek", 0.0))
    st.session_state["gpt_aktionsdauer_gesamt_sek"] = bisher + float(dauer)
    # Debug-Hinweis: Bei Bedarf kann ``st.write(kontext, dauer)`` ergänzt werden,
    # um zeitintensive Abschnitte zu identifizieren.
