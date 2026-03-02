import streamlit as st
from module.sidebar import show_sidebar
from module.navigation import redirect_to_start_page
from module.footer import copyright_footer
from diagnostikmodul import diagnostik_und_befunde_routine
from befundmodul import generiere_befund
from module.offline import display_offline_banner, is_offline
from module.loading_indicator import task_spinner
from module.gpt_timing import messe_gpt_aktion

show_sidebar()
display_offline_banner()

# Sollte jemand diese Seite ohne vorbereiteten Fall aufrufen, leiten wir automatisch
# zurück zur Startseite. Dadurch bleibt der Ablauf konsistent und fehlende
# Session-State-Einträge führen nicht mehr zu schwer nachvollziehbaren Fehlern.
if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
    redirect_to_start_page(
        "⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite."
    )

st.session_state.setdefault("befund_generating", False)
st.session_state.setdefault("befund_generierung_gescheitert", False)
# Initialisierung der Nutzereingaben für Diagnostik, damit spätere Zugriffe
# (z.B. im Anzeige-Block) keinen Session-State-Fehler auslösen.
# Debug-Hinweis: Falls unerwartete Werte angezeigt werden, kann dieser Key
# temporär geleert werden, um die Datenquelle zu überprüfen.
st.session_state.setdefault("user_diagnostics", "")
# Das Versorgungssetting zur Verdachtsdiagnose wird direkt im Diagnostik-Teil
# erfasst. Damit Streamlit keinen ungültigen Default erhält, holen wir zuerst
# den letzten persistierten Wert und nutzen ihn als Initialwert.
# Debugging-Hinweis: Bei Bedarf kann der Key gezielt entfernt werden, um die
# Auswahl neu aufzubauen (z. B. via st.session_state.pop(...)).
therapie_setting_verdacht_default = st.session_state.get(
    "therapie_setting_verdacht_persisted",
    "Einweisung Notaufnahme",
)
st.session_state.setdefault("therapie_setting_verdacht", therapie_setting_verdacht_default)


def _is_stationaeres_setting(setting_wert: str) -> bool:
    """Liefert True, wenn das gewählte Setting stationär/notfallbezogen ist."""

    return not setting_wert.startswith("ambulant")


def _diagnostik_label_fuer_setting(setting_wert: str) -> str:
    """Erzeugt die passende Frage zur Diagnostik abhängig vom Versorgungssetting."""

    if _is_stationaeres_setting(setting_wert):
        return "Welche konkreten kurzfristigen diagnostischen Maßnahmen möchten Sie prästationär noch veranlassen?"
    return "Welche konkreten diagnostischen Maßnahmen möchten Sie vorschlagen?"


def pruefe_setting_kongruenz_diagnostik(client, setting_wert: str, diagnostik_text: str) -> tuple[bool, str]:
    """Prüft per GPT, ob die Diagnostik zum gewählten Setting passt.

    Debug-Hinweis: Für eine manuelle Fehlersuche kann der finale Prompt temporär
    per `st.write(prompt)` ausgegeben werden. Danach wieder entfernen.
    """

    if not diagnostik_text.strip():
        return True, ""
    if client is None or is_offline():
        # Im Offline-Modus wird keine künstliche Heuristik verwendet, damit die
        # Nutzenden transparent sehen, dass diese Prüfung online erfolgt.
        return True, ""

    setting_kontext = (
        "ambulant" if setting_wert.startswith("ambulant") else "Einweisung/Notaufnahme"
    )
    prompt = f"""
Bewerte, ob folgende diagnostische Maßnahmen im angegebenen Versorgungssetting kurzfristig sinnvoll durchführbar sind.

Versorgungssetting: {setting_kontext}
Diagnostische Maßnahmen:
{diagnostik_text}

Antworte ausschließlich als JSON mit genau diesen Schlüsseln:
{{
  "is_congruent": true oder false,
  "reason": "Kurze Begründung auf Deutsch."
}}

Kriterien:
- Ambulant: keine OP-Planung oder stationär-exklusive Notfalllogik als ambulante Sofortmaßnahme.
- Bei geplanter Notfalleinweisung sollen prästationäre Maßnahmen realistisch kurzzeitig machbar sein.
- Wenn Maßnahmen dem Setting deutlich widersprechen, setze is_congruent auf false.
"""

    try:
        antwort = messe_gpt_aktion(
            lambda: client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            ),
            kontext="Setting-Kongruenz Diagnostik",
        )
        raw_text = (antwort.choices[0].message.content or "").strip()
        json_start = raw_text.find("{")
        json_ende = raw_text.rfind("}")
        if json_start == -1 or json_ende == -1:
            return True, ""
        import json

        parsed = json.loads(raw_text[json_start : json_ende + 1])
        return bool(parsed.get("is_congruent", True)), str(parsed.get("reason", "")).strip()
    except Exception:
        # Fehler in dieser Zusatzprüfung blockieren nicht die Seite; für
        # Debugging kann hier temporär `st.exception(...)` ergänzt werden.
        return True, ""


def aktualisiere_kumulative_befunde_page(neuer_befund: str) -> None:
    """Pflegt den Primärbefund und die kumulativen Texte für Export/Feedback ein."""

    st.session_state["befunde"] = neuer_befund

    passagen = [f"### Termin 1\n{neuer_befund}".strip()]
    gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
    for termin in range(2, gesamt + 1):
        key = f"befunde_runde_{termin}"
        text = st.session_state.get(key, "").strip()
        if text:
            passagen.append(f"### Termin {termin}\n{text}")

    st.session_state["gpt_befunde"] = neuer_befund
    st.session_state["gpt_befunde_kumuliert"] = "\n---\n".join(passagen).strip()


def starte_automatische_befundgenerierung_page(client) -> None:
    """Startet ohne Nutzereingriff die Befundgenerierung, sobald alle Daten vorliegen."""

    if st.session_state.get("befund_generating", False):
        return
    if st.session_state.get("befunde"):
        return
    if st.session_state.get("befund_generierung_gescheitert", False):
        return
    if client is None:
        return  # Sicherheitsnetz, falls der Client nicht initialisiert wurde.

    diagnostik_text = st.session_state.get("user_diagnostics", "").strip()
    ddx_text = st.session_state.get("user_ddx2", "").strip()
    if not diagnostik_text or not ddx_text:
        return

    st.session_state["befund_generating"] = True
    st.session_state.pop("befund_generierungsfehler", None)

    try:
        szenario = st.session_state.get("diagnose_szenario", "")
        if is_offline():
            befund = generiere_befund(client, szenario, diagnostik_text)
            aktualisiere_kumulative_befunde_page(befund)
        else:
            ladeaufgaben = [
                "Lese Falldaten ein",
                "Analysiere diagnostische Eingaben",
                "Erstelle strukturierten Befund",
            ]
            with task_spinner("Befunde werden automatisch generiert...", ladeaufgaben) as indikator:
                indikator.advance(1)
                befund = generiere_befund(client, szenario, diagnostik_text)
                indikator.advance(1)
                aktualisiere_kumulative_befunde_page(befund)
                indikator.advance(1)
    except Exception as error:
        st.session_state["befund_generierung_gescheitert"] = True
        st.session_state["befund_generierungsfehler"] = str(error)
    else:
        st.session_state["befund_generierung_gescheitert"] = False
    finally:
        st.session_state["befund_generating"] = False

    if not st.session_state.get("befund_generierung_gescheitert", False):
        st.rerun()

# st.subheader("Diagnostik und Befunde")

# --- Voraussetzungen wie in Hauptdatei beachten ---
if "koerper_befund" in st.session_state:
        if "user_ddx2" not in st.session_state:
                # Hinweis: Das Versorgungssetting soll nach den DDx und vor der
                # konkreten Diagnostik erfragt werden. Dadurch überlegen die
                # Studierenden früh, ob die weitere Abklärung ambulant oder
                # stationär/notfallmäßig erfolgen soll.
                # Wichtig: Das Radio liegt außerhalb des Formulars, damit der
                # Hinweistext sofort auf Button-Wechsel reagiert (Formulare
                # aktualisieren Inhalte erst nach dem Absenden).
                setting_optionen_verdacht = [
                    "Einweisung Notaufnahme",
                    "Einweisung elektiv",
                    "ambulant (zeitnahe Wiedervorstellung)",
                    "ambulant (Vorstellung im nächsten Quartal)",
                ]
                bestehendes_setting = st.session_state.get("therapie_setting_verdacht", "")
                # Debugging-Hinweis: Wenn ein unerwarteter Wert auftaucht, kann
                # das Setting temporär aus dem Session-State entfernt werden,
                # um die Auswahl erneut zu erzwingen.
                if bestehendes_setting in setting_optionen_verdacht:
                    default_index = setting_optionen_verdacht.index(bestehendes_setting)
                else:
                    # Streamlit wirft einen Fehler, wenn ein Session-State-Wert
                    # nicht zu den Optionen passt. Für Debugging kann hier
                    # temporär st.write(bestehendes_setting) aktiviert werden.
                    # Debug-Hinweis (beschriftet): Zeigt den fehlerhaften
                    # Session-State-Wert vor dem Entfernen an.
                    # TODO: Debug-Ausgabe später entfernen.
                    # st.write("Debug Seite 4 > Ungültiges Setting verdacht:", bestehendes_setting)
                    st.session_state.pop("therapie_setting_verdacht", None)
                    default_index = 0
                with st.form("differentialdiagnosen_diagnostik_formular"):
                    ddx_input2 = st.text_area(
                        "Welche drei Differentialdiagnosen halten Sie nach Anamnese und Untersuchung für möglich?",
                        key="ddx_input2",
                    )

                    setting_verdacht = st.radio(
                        "Wie planen Sie unter Beachtung Ihrer bisherigen Befunde die weitere Versorgung Ihres Patienten?\nDie Entscheidung kann im Verlauf revidiert werden",
                        options=setting_optionen_verdacht,
                        index=default_index,
                        key="therapie_setting_verdacht",
                    )
                    # Debug-Hinweis (beschriftet): Aktivieren, um Auswahl und
                    # Session-State nach dem Radio eindeutig zu prüfen.
                    # TODO: Debug-Ausgaben später entfernen.
                    # st.write("Debug Seite 4 > Auswahl verdacht (Radio):", setting_verdacht)
                    # st.write("Debug Seite 4 > Session verdacht (nach Radio):", st.session_state.get("therapie_setting_verdacht"))
                    st.session_state["debug_snapshot_therapie_setting_verdacht"] = setting_verdacht
                    st.session_state["therapie_setting_verdacht_persisted"] = setting_verdacht

                    with st.expander("ℹ️ Hinweise zum gewählten Versorgungssetting", expanded=False):
                        if setting_verdacht.startswith("ambulant"):
                            st.markdown(
                                "**Hinweis zur Diagnostik (ambulant):** Die diagnostischen Möglichkeiten in diesem Schritt sind nicht limitiert, weitere Anforderungen sind bei neuen Terminen möglich. Versuchen Sie die Diagnostik möglichst rationell zu veranlassen.\n\n"
                                "💡Weitere Untersuchungen können Sie, falls es Ihnen erforderlich erscheint, in einem nächsten Schritt anfordern.\n\n"
                                "💡Sie können sich auch später noch für eine stationäre Therapie entscheiden."
                            )
                        else:
                            st.markdown(
                                "**Hinweis zur Diagnostik (Einweisung/Notaufnahme):**\n"
                                "ℹ️ Die stationäre Therapie führt im nächsten Schritt zu einem Rollenwechsel: Die weitere Versorgung erfolgt im Krankenhaus/Notaufnahme, Sie übernehmen *im nächsten Schritt* die ärztliche Diagnostik und Therapie im Krankenhaus. Bitte richten Sie Diagnostik- und Therapievorschläge konsequent an diesem Setting aus."
                            )

                    diag_input2 = st.text_area(
                        _diagnostik_label_fuer_setting(setting_verdacht),
                        key="diag_input2",
                    )

                    if not _is_stationaeres_setting(setting_verdacht):
                        st.info(
                            "Hinweis zur Diagnostik (ambulant): Die diagnostischen Möglichkeiten in diesem Schritt sind nicht limitiert, weitere Anforderungen sind bei neuen Terminen möglich. Versuchen Sie die Diagnostik möglichst rationell zu veranlassen.\n\n"
                            "💡Weitere Untersuchungen können Sie, falls es Ihnen erforderlich erscheint, in einem nächsten Schritt anfordern.\n\n"
                            "💡Sie können sich auch später noch für eine stationäre Therapie entscheiden."
                        )
                    else:
                        st.info(
                            "Hinweis zur Diagnostik (Einweisung/Notaufnahme):\n"
                            "ℹ️ Die stationäre Therapie führt im nächsten Schritt zu einem Rollenwechsel: Die weitere Versorgung erfolgt im Krankenhaus/Notaufnahme, Sie übernehmen *im nächsten Schritt* die ärztliche Diagnostik und Therapie im Krankenhaus. Bitte richten Sie Diagnostik- und Therapievorschläge konsequent an diesem Setting aus."
                        )

                    submitted_diag = st.form_submit_button("✅ Eingaben speichern")

                if submitted_diag:
                    from sprachmodul import sprach_check
                    client = st.session_state.get("openai_client")
                    st.session_state.user_ddx2 = sprach_check(ddx_input2, client)
                    # Das Versorgungssetting stammt direkt aus dem Radio-Widget.
                    # Wichtig: Nach der Widget-Initialisierung darf der Key nicht
                    # erneut gesetzt werden, sonst bricht Streamlit mit einem
                    # "cannot be modified"-Fehler ab. Debug-Hinweis: Falls ein
                    # ungültiger Wert auftaucht, kann der Key per
                    # st.session_state.pop("therapie_setting_verdacht", None)
                    # gelöscht und die Seite neu geladen werden.
                    st.session_state.user_diagnostics = sprach_check(diag_input2, client)

                    kongruent, begruendung = pruefe_setting_kongruenz_diagnostik(
                        client,
                        setting_verdacht,
                        st.session_state.user_diagnostics,
                    )
                    st.session_state["diagnostik_setting_kongruent"] = kongruent
                    st.session_state["diagnostik_setting_kongruenz_hinweis"] = begruendung
                    if not kongruent:
                        st.warning(
                            "⚠️ Die diagnostischen Maßnahmen wirken im gewählten Setting nicht vollständig stimmig. "
                            "Bitte passen Sie Ihre Eingabe unter 'Diagnostik und Befunde' an und speichern Sie erneut."
                        )
                        if begruendung:
                            st.info(f"Begründung der KI-Prüfung: {begruendung}")
                    else:
                        starte_automatische_befundgenerierung_page(client)

        else:
                st.markdown(f"**Differentialdiagnosen:**  \n{st.session_state.user_ddx2}")
                # Das Setting der Verdachtsdiagnose wird im Verlauf sichtbar
                # angezeigt, damit der Kontext erhalten bleibt.
                st.markdown(
                    f"**Versorgungssetting (Verdacht):**  \n{st.session_state.get('therapie_setting_verdacht', '')}"
                )
                st.markdown(f"**Diagnostische Maßnahmen:**  \n{st.session_state.user_diagnostics}")
                if st.session_state.get("diagnostik_setting_kongruent") is False:
                    st.warning(
                        "⚠️ Für diese Eingabe liegt eine Setting-Diskrepanz vor. "
                        "Bitte überarbeiten Sie die Diagnostik in diesem Schritt."
                    )
                    if st.session_state.get("diagnostik_setting_kongruenz_hinweis"):
                        st.info(
                            f"Begründung der KI-Prüfung: {st.session_state.get('diagnostik_setting_kongruenz_hinweis')}"
                        )

        starte_automatische_befundgenerierung_page(st.session_state.get("openai_client"))
else:
    st.subheader("Diagnostik und Befunde")
    st.button("Untersuchung durchführen", disabled=True)
    st.info("❗Bitte führen Sie zuerst die körperliche Untersuchung durch.")

# --- Befunde anzeigen oder generieren ---
st.markdown("---")

if (
    "koerper_befund" in st.session_state
    and "user_diagnostics" in st.session_state
    and "user_ddx2" in st.session_state
):
    st.subheader("📄 Befunde")

    if "befunde" in st.session_state:
        st.markdown(st.session_state.befunde)
        if st.session_state.get("befund_generierungsfehler"):
            st.info(
                "ℹ️ Der automatische Lauf meldete zuvor einen Fehler. Der Hinweis verbleibt zur Transparenz."
            )
    else:
        if st.session_state.get("befund_generierungsfehler"):
            st.error(
                "❌ Automatische Befundgenerierung fehlgeschlagen: "
                f"{st.session_state['befund_generierungsfehler']}"
            )
        if st.session_state.get("befund_generierung_gescheitert", False):
            client = st.session_state.get("openai_client")
            if st.button("🧪 Befunde generieren lassen"):
                try:
                    st.session_state["befund_generating"] = True
                    diagnostik_eingabe = st.session_state.user_diagnostics
                    diagnose_szenario = st.session_state.diagnose_szenario

                    if is_offline():
                        befund = generiere_befund(client, diagnose_szenario, diagnostik_eingabe)
                        aktualisiere_kumulative_befunde_page(befund)
                    else:
                        ladeaufgaben = [
                            "Bereite diagnostische Eingaben auf",
                            "Führe erneute Analyse durch",
                            "Formuliere aktualisierten Befund",
                        ]
                        with task_spinner("Befunde werden erneut generiert...", ladeaufgaben) as indikator:
                            indikator.advance(1)
                            befund = generiere_befund(client, diagnose_szenario, diagnostik_eingabe)
                            indikator.advance(1)
                            aktualisiere_kumulative_befunde_page(befund)
                            indikator.advance(1)
                    st.session_state["befund_generierung_gescheitert"] = False
                    st.session_state.pop("befund_generierungsfehler", None)
                    st.session_state["befund_generating"] = False
                    if is_offline():
                        st.info("🔌 Offline-Befund gespeichert. Für erneute KI-Ergebnisse kann der Online-Modus genutzt werden.")
                    st.success("✅ Befunde generiert")
                    st.rerun()

                except Exception as error:
                    st.session_state["befund_generating"] = False
                    st.error(f"❌ Manueller Fallback fehlgeschlagen: {error}")
                    # Hinweis: Zusätzliche Debug-Ausgaben können hier bei Bedarf ergänzt werden.
else:
    # Hinweis für Entwickler*innen: In dieser Verzweigung liegen noch keine Diagnostik-
    # Eingaben vor. Früher haben wir hier die Überschrift "Befunde" sowie einen
    # deaktivierten Button und einen erklärenden Hinweis ausgegeben. Dieses Layout hat bei
    # Nutzer*innen den Eindruck erweckt, dass ein Bedienfehler vorliegt. Um eine klare und
    # reduzierte Oberfläche zu gewährleisten, lassen wir den Bereich nun bewusst leer.
    # Für Debugging-Zwecke können die alten Elemente über die auskommentierten Zeilen
    # reaktiviert werden.
    # st.subheader("📄 Befunde")
    # st.button("🧪 Befunde generieren lassen", disabled=True)
    # st.info("❗Bitte fordern Sie zunächst Untersuchungen an.")
    pass  # Bewusst keine Ausgabe: Kommentare oben erläutern die Hintergründe für Debugging-Zwecke.

# Weitere Diagnostik-Termine
if not st.session_state.get("final_diagnose", "").strip():
    if (
        "diagnostik_eingaben" not in st.session_state
        or "gpt_befunde" not in st.session_state
        or st.session_state.get("diagnostik_aktiv", False)
    ):
        client = st.session_state.get("openai_client")
        diagnostik_eingaben, gpt_befunde = diagnostik_und_befunde_routine(
            client,
            start_runde=2,
            weitere_diagnostik_aktiv=False
        )
        st.session_state["diagnostik_eingaben"] = diagnostik_eingaben
        st.session_state["gpt_befunde"] = gpt_befunde
    else:
        diagnostik_eingaben = st.session_state["diagnostik_eingaben"]
        gpt_befunde = st.session_state["gpt_befunde"]

    # Anzeige bestehender Befunde
    gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
    for i in range(2, gesamt + 1):
        bef_key = f"befunde_runde_{i}"
        bef = st.session_state.get(bef_key, "")
        if bef:
            st.markdown(f"📅 Termin {i}")
            st.markdown(bef)

# Zusätzlicher Termin
gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
neuer_termin = gesamt + 1

if (
    st.session_state.get("diagnostik_aktiv", False)
    and f"diagnostik_runde_{neuer_termin}" not in st.session_state
):
    st.markdown(f"### 📅 Termin {neuer_termin}")
    with st.form(key=f"diagnostik_formular_runde_{neuer_termin}_hauptskript"):
        neue_diagnostik = st.text_area(
            "Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern?",
            key=f"eingabe_diag_r{neuer_termin}"
        )
        submitted = st.form_submit_button("✅ Diagnostik anfordern")

    if submitted and neue_diagnostik.strip():
        neue_diagnostik = neue_diagnostik.strip()
        st.session_state[f"diagnostik_runde_{neuer_termin}"] = neue_diagnostik

        szenario = st.session_state.get("diagnose_szenario", "")
        client = st.session_state.get("openai_client")
        if is_offline():
            befund = generiere_befund(client, szenario, neue_diagnostik)
            st.session_state[f"befunde_runde_{neuer_termin}"] = befund
        else:
            ladeaufgaben = [
                "Übertrage neue Diagnostik an das Modell",
                "Stimme Ergebnisse mit bisherigen Befunden ab",
                "Bereite Rückmeldung für die Anzeige auf",
            ]
            with task_spinner("GPT erstellt Befunde...", ladeaufgaben) as indikator:
                indikator.advance(1)
                befund = generiere_befund(client, szenario, neue_diagnostik)
                indikator.advance(1)
                st.session_state[f"befunde_runde_{neuer_termin}"] = befund
                indikator.advance(1)
        st.session_state["diagnostik_runden_gesamt"] = neuer_termin
        st.session_state["diagnostik_aktiv"] = False
        if is_offline():
            st.info("🔌 Offline-Befund gespeichert. Schalte den Online-Modus wieder ein, um echte GPT-Ergebnisse zu erhalten.")
        st.rerun()

# Button für neue Diagnostik
if (
    not st.session_state.get("diagnostik_aktiv", False)
    and ("befunde" in st.session_state or gesamt >= 2)
):
    if st.button("➕ Weitere Diagnostik anfordern", key="btn_neue_diagnostik"):
        st.session_state["diagnostik_aktiv"] = True
        st.rerun()

# # Nur für Admin sichtbar:
# if st.session_state.get("admin_mode"):
#     st.page_link("pages/20_Fallbeispiel_Editor.py", label="🔧 Fallbeispiel-Editor", icon="🔧")

# Weiter-Link zur Diagnose und Therapie
st.page_link(
    "pages/5_Diagnose_und_Therapie.py",
    label="Weiter zur Diagnose und Therapie",
    icon="💊",
    disabled="befunde" not in st.session_state
)

copyright_footer()
