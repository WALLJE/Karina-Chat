"""Hilfsfunktionen für die Navigation zwischen den Streamlit-Seiten."""

import streamlit as st


# Hinweis: Die ausführlichen Kommentare sind bewusst auf Deutsch gehalten, um den Projektteilnehmenden
# den Einsatzzweck schnell verständlich zu machen. Durch die zentrale Funktion vermeiden wir
# doppelte Logik in den einzelnen Seitenmodulen.
def redirect_to_start_page(warning_message: str | None = None) -> None:
    """Leitet auf die Startseite um und hinterlegt optional eine Warnmeldung."""
    # Wenn der direkte Aufruf einer Unterseite erfolgt, fehlt häufig der notwendige Kontext
    # (z. B. ein zuvor gewählter Fall). In diesem Fall speichern wir eine Warnmeldung in der
    # Session, damit sie nach der automatischen Rückkehr auf der Startseite angezeigt werden kann.
    # Sollte kein Hinweis gewünscht sein, wird auch nichts in den Session State geschrieben.
    if warning_message:
        st.session_state["start_warning"] = warning_message

    # Anschließend erfolgt der unmittelbare Wechsel auf die Startseite. Die Datei "Karina_Chat_2.py"
    # fungiert als Einstiegspunkt der Anwendung. "st.switch_page" bricht die weitere Ausführung der
    # aktuellen Seite ab und lädt stattdessen das Zielskript. So müssen wir kein zusätzliches
    # st.stop() aufrufen.
    st.switch_page("Karina_Chat_2.py")

    # Dieser Rückgabepunkt wird faktisch nie erreicht, da Streamlit nach dem Seitenwechsel den
    # restlichen Code der aktuellen Seite ignoriert. Für Debugging kann hier bei Bedarf ein
    # st.write(...) aktiviert werden, um zu prüfen, ob die Funktion unerwartet weiterläuft.


def render_next_page_link(
    target_page: str,
    label: str,
    *,
    icon: str = "➡️",
    disabled: bool = False,
    helper_text: str | None = None,
    as_button: bool = False,
    button_key: str | None = None,
) -> None:
    """Rendert den standardisierten "Weiter zu ..."-Link für den nächsten Lernschritt.

    Warum zentral?
    - Alle Seiten nutzen dieselbe API für den nächsten Navigationsschritt.
    - Das klickbare Element bleibt ein nativer Streamlit-Link ohne vorgeschaltete
      Deko-Container, damit Layout und Interaktion konsistent bleiben.

    Debug-Hinweis:
    Falls eine Weiterleitung unerwartet deaktiviert wirkt, kann temporär
    `st.write("Next-Link disabled:", disabled)` direkt vor dem Aufruf aktiviert
    werden, um den Status transparent zu prüfen.
    """

    # Neuer optionaler Button-Modus:
    # Wenn as_button=True gesetzt ist, wird die Navigation als echter Button gerendert.
    # Das ist nützlich, wenn ein Schritt bewusst als "freigeschaltet / gesperrt"
    # visualisiert werden soll (z. B. grün bei aktiv, grau bei deaktiviert).
    #
    # Wichtiger Vorteil: Der deaktivierte Zustand ist dann semantisch und visuell an
    # dasselbe UI-Element gekoppelt. Für Lern-Workflows ist das eindeutiger als ein
    # Link mit zusätzlicher Deko.
    if as_button:
        # Der Key macht den Button selektierbar und stabil. So kann auf Seitenebene
        # gezieltes CSS nur für diesen speziellen "Weiter"-Button gesetzt werden,
        # ohne andere Buttons unbeabsichtigt mitzustylen.
        if st.button(
            f"{icon} {label}",
            disabled=disabled,
            key=button_key,
            type="secondary",
        ):
            st.switch_page(target_page)
    else:
        # Standardmodus bleibt erhalten: klassischer Streamlit-Seitenlink.
        # So bleibt die Funktion weiterhin rückwärtskompatibel in allen Modulen,
        # die keinen Button-Look benötigen.
        st.page_link(target_page, label=label, icon=icon, disabled=disabled)

    # Optionaler Debug-Hinweis: Falls der Eindruck entsteht, der Link sei "verschwunden",
    # kann temporär folgende Zeile aktiviert werden:
    # st.write("render_next_page_link", {"target_page": target_page, "disabled": disabled})
    if helper_text:
        st.caption(helper_text)
