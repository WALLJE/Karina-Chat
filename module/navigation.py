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
) -> None:
    """Rendert den standardisierten "Weiter"-Block mit klarem Aktiv/Deaktiv-Zustand.

    Warum zentral?
    - Alle Seiten verwenden denselben visuellen Zustand für die nächste Navigation.
    - Klickbar (aktiv): grün hinterlegt, damit der nächste Schritt deutlich sichtbar ist.
    - Nicht klickbar (deaktiviert): ausgegraut, damit der Zustand sofort erkennbar bleibt.

    Debug-Hinweis:
    Falls die Einfärbung unerwartet nicht greift, kann temporär
    `st.write("next_link_disabled", disabled)` aktiviert werden.
    """

    # CSS-Konzept:
    # Wir stylen das *gleiche* Element, das auch die Navigation ausführt (st.page_link),
    # damit keine losgelösten Balken entstehen. Die Farbgebung hängt über aria-disabled
    # direkt am Interaktionszustand: aktiv = grün, deaktiviert = grau.
    #
    # Hinweis: Die CSS-Definition ist absichtlich in dieser Funktion, damit alle Seiten,
    # die render_next_page_link nutzen, automatisch denselben Stil erhalten.
    st.markdown(
        """
        <style>
        div[data-testid="stPageLink"] a {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 0.68rem 0.85rem;
            margin: 0.35rem 0 0.65rem 0;
            border-radius: 0.75rem;
            border: 1px solid #95d5a6;
            background: #e9f9ee;
            color: #23412c;
            text-decoration: none;
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }

        div[data-testid="stPageLink"] a:hover {
            background: #ddf5e5;
            border-color: #80c795;
        }

        div[data-testid="stPageLink"] a[aria-disabled="true"] {
            background: #eceff3;
            border-color: #d5dbe3;
            color: #7a8290;
            cursor: not-allowed;
            pointer-events: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.page_link(target_page, label=label, icon=icon, disabled=disabled)

    # Optionaler Hilfetext bleibt wie bisher unterhalb des Navigations-Elements sichtbar.
    if helper_text:
        st.caption(helper_text)
