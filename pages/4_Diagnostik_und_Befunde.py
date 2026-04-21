import streamlit as st
from module.sidebar import show_sidebar
from module.navigation import redirect_to_start_page, render_next_page_link
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
st.session_state.setdefault("diagnostik_edit_mode", True)
st.session_state.setdefault("user_diagnostics", "")

therapie_setting_verdacht_default = st.session_state.get(
    "therapie_setting_verdacht_persisted",
    "Einweisung Notaufnahme",
)
st.session_state.setdefault("therapie_setting_verdacht", therapie_setting_verdacht_default)

# --- Labor Kategorien Definition ---
LABOR_KATEGORIEN = {
    "Hämatologie": ["Kleines Blutbild", "Großes Blutbild"],
    "Gerinnung": ["D-Dimere", "Quick / INR", "PTT"],
    "Klin. Chemie": ["Elektrolyte", "CRP", "BSG", "LDH", "HbA1C", "Procalcitonin"],
    "Stuhldiagnostik": ["Mikrobiologie Stuhl", "Calprotectin", "iFOBT"],
    "Leber / Pankreas": ["GOT & GPT", "Gamma-GT", "Alk. Phosphatase", "Bilirubin gesamt", "Lipase"],
    "Kardial": ["Troponin", "CK", "NT-proBNP"],
    "Weitere Organe": ["Kreatinin & GFR", "TSH mit fT3 & fT4"],
    "Infektionsserologie": ["SARS-CoV-2", "Influenza PCR", "HBs-Antigen", "Anti-HBc"],
    "Urindiagnostik": ["Urinstatus", "Urinkultur"],
    "Blutkulturen": ["Blutkultur"]
}

def _is_stationaeres_setting(setting_wert: str) -> bool:
    return not setting_wert.startswith("ambulant")

def _diagnostik_label_fuer_setting(setting_wert: str) -> str:
    if _is_stationaeres_setting(setting_wert):
        return "Welche konkreten kurzfristigen diagnostischen Maßnahmen möchten Sie prästationär noch veranlassen? (Bildgebung, EKG etc.)"
    return "Welche konkreten diagnostischen Maßnahmen möchten Sie vorschlagen? (Bildgebung, EKG etc.)"

def pruefe_setting_kongruenz_diagnostik(client, setting_wert: str, diagnostik_text: str) -> tuple[bool, str]:
    if not diagnostik_text.strip():
        return True, ""
    if client is None or is_offline():
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
        is_congruent_raw = parsed.get("is_congruent", True)
        if isinstance(is_congruent_raw, bool):
            is_congruent = is_congruent_raw
        elif isinstance(is_congruent_raw, str):
            normalisiert = is_congruent_raw.strip().lower()
            if normalisiert in {"true", "1", "ja"}:
                is_congruent = True
            elif normalisiert in {"false", "0", "nein"}:
                is_congruent = False
            else:
                is_congruent = True
        else:
            is_congruent = True

        return is_congruent, str(parsed.get("reason", "")).strip()
    except Exception:
        return True, ""

def aktualisiere_kumulative_befunde_page(neuer_befund: str) -> None:
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
    if st.session_state.get("befund_generating", False):
        return
    if st.session_state.get("befunde"):
        return
    if st.session_state.get("befund_generierung_gescheitert", False):
        return
    if client is None:
        return 

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

# --- Hauptanzeige ---
if "koerper_befund" in st.session_state:
        if st.session_state.get("diagnostik_setting_kongruent") is False:
                st.session_state["diagnostik_edit_mode"] = True

        if st.session_state.get("diagnostik_edit_mode", True):
                setting_optionen_verdacht = [
                    "Einweisung Notaufnahme",
                    "Einweisung elektiv",
                    "ambulant (zeitnahe Wiedervorstellung)",
                    "ambulant (Vorstellung im nächsten Quartal)",
                ]
                bestehendes_setting = st.session_state.get("therapie_setting_verdacht", "")
                
                if bestehendes_setting in setting_optionen_verdacht:
                    default_index = setting_optionen_verdacht.index(bestehendes_setting)
                else:
                    st.session_state.pop("therapie_setting_verdacht", None)
                    default_index = 0
                
                ddx_input2 = st.text_area(
                    "Welche drei Differentialdiagnosen halten Sie nach Anamnese und Untersuchung für möglich?",
                    key="ddx_input2",
                )

                setting_verdacht = st.radio(
                    "Wie planen Sie unter Beachtung Ihrer bisherigen Befunde die weitere Versorgung Ihres Patienten?\n\n 💡Die Entscheidung kann im Verlauf revidiert werden",
                    options=setting_optionen_verdacht,
                    index=default_index,
                    key="therapie_setting_verdacht",
                )
                
                st.session_state["debug_snapshot_therapie_setting_verdacht"] = setting_verdacht
                st.session_state["therapie_setting_verdacht_persisted"] = setting_verdacht

                with st.expander("ℹ️ Hinweise zum gewählten Versorgungssetting", expanded=False):
                    if setting_verdacht.startswith("ambulant"):
                        st.markdown(
                            "**Hinweis zur Diagnostik (ambulant):**\n\nDie diagnostischen Möglichkeiten in diesem Schritt sind nicht begrenzt, sollten aber zum ambulanten Behandlungskonzept passen. Weitere Anforderungen sind bei neuen Terminen möglich."
                            "Veranlassen Sie Diagnostik so umfangreich wie nötig, aber auch so gezielt wie möglich.\n\n"
                            "💡Weitere Untersuchungen können Sie, falls es Ihnen erforderlich erscheint, in einem nächsten Schritt anfordern.\n\n"
                            "💡Sie können sich auch später noch für eine stationäre Therapie entscheiden."
                        )
                    else:
                        st.markdown(
                            "**Hinweis zur Diagnostik (Einweisung/Notaufnahme):**\n\n"
                            "ℹ️ Sie möchten den Patienten stationär einweisen. Im folgenden können Sie Untersuchungen anfordern, die die vorstationär noch durchführen lassen möchten.\n\n"
                            "💡Sie können sich auch später noch für eine stationäre Therapie entscheiden."
                        )

                # --- Neues Labor Modul ---
                st.markdown("### 🧪 Laboranforderung")
                with st.expander("Laborwerte auswählen (Zentrallabor)"):
                    st.info("Markieren Sie die Parameter, die Sie bestimmen lassen möchten. Weitere Parameter können Sie im Feld unten ergänzen.")
                    
                    lab_checkboxes_r1 = {}
                    cols = st.columns(3)
                    
                    # Verteilung der neuen Kategorien auf 3 Spalten
                    with cols[0]:
                        for cat in ["Hämatologie", "Gerinnung", "Kardial", "Blutkulturen"]:
                            st.markdown(f"**{cat}**")
                            for item in LABOR_KATEGORIEN[cat]:
                                lab_checkboxes_r1[item] = st.checkbox(item, key=f"lab_{item}_r1")
                    
                    with cols[1]:
                        for cat in ["Klin. Chemie", "Leber / Pankreas", "Weitere Organe"]:
                            st.markdown(f"**{cat}**")
                            for item in LABOR_KATEGORIEN[cat]:
                                lab_checkboxes_r1[item] = st.checkbox(item, key=f"lab_{item}_r1")
                                
                    with cols[2]:
                        for cat in ["Infektionsserologie", "Urindiagnostik", "Stuhldiagnostik"]:
                            st.markdown(f"**{cat}**")
                            for item in LABOR_KATEGORIEN[cat]:
                                lab_checkboxes_r1[item] = st.checkbox(item, key=f"lab_{item}_r1")

                    st.markdown("---")
                    labor_freitext = st.text_input("Weitere Laborparameter (Freitext):", key="labor_freitext_r1", placeholder="z. B. Zöliakie-Serologie")

                # --- Weitere Diagnostik ---
                diag_input2 = st.text_area(
                    _diagnostik_label_fuer_setting(setting_verdacht),
                    key="diag_input2",
                )

                if _is_stationaeres_setting(setting_verdacht):
                    st.info(
                        "Hinweis zur Diagnostik (Einweisung/Notaufnahme):\n"
                        "ℹ️ Die stationäre Therapie führt im nächsten Schritt zu einem Rollenwechsel: Die weitere Versorgung erfolgt im Krankenhaus/Notaufnahme, Sie übernehmen *im nächsten Schritt* die ärztliche Diagnostik und Therapie im Krankenhaus. Bitte richten Sie Diagnostik- und Therapievorschläge konsequent an diesem Setting aus."
                    )

                submitted_diag = st.button("✅ Eingaben speichern", key="btn_diag_erste_runde")

                if submitted_diag:
                    from sprachmodul import sprach_check
                    client = st.session_state.get("openai_client")
                    
                    ddx_korrigiert = sprach_check(ddx_input2, client)
                    
                    # Laborauswahl extrahieren
                    gewaehlte_labore = [lab for lab, checked in lab_checkboxes_r1.items() if checked]
                    if labor_freitext.strip():
                        gewaehlte_labore.append(labor_freitext.strip())
                        
                    labor_string = ", ".join(gewaehlte_labore) if gewaehlte_labore else "Kein spezifisches Labor angefordert"
                    
                    # Kombinierter Text für die KI
                    if diag_input2.strip():
                        kombinierte_diagnostik = f"{diag_input2}\n\nAngeforderte Laborwerte: {labor_string}"
                    else:
                        kombinierte_diagnostik = f"Angeforderte Laborwerte: {labor_string}"
                    
                    diagnostik_korrigiert = sprach_check(kombinierte_diagnostik, client)

                    kongruent, begruendung = pruefe_setting_kongruenz_diagnostik(
                        client,
                        setting_verdacht,
                        diagnostik_korrigiert,
                    )

                    st.session_state["diagnostik_setting_kongruent"] = kongruent
                    st.session_state["diagnostik_setting_kongruenz_hinweis"] = begruendung
                    
                    if not kongruent:
                        st.session_state.pop("user_ddx2", None)
                        st.session_state.pop("user_diagnostics", None)
                        st.session_state["diagnostik_edit_mode"] = True
                        st.warning(
                            "⚠️ Die diagnostischen Maßnahmen wirken im gewählten Setting nicht vollständig stimmig. "
                            "Bitte passen Sie Ihre Eingabe an und speichern Sie erneut."
                        )
                        if begruendung:
                            st.info(f"Begründung der KI-Prüfung: {begruendung}")
                        st.rerun()
                    else:
                        st.session_state.user_ddx2 = ddx_korrigiert
                        st.session_state.user_diagnostics = diagnostik_korrigiert
                        st.session_state["diagnostik_edit_mode"] = False
                        starte_automatische_befundgenerierung_page(client)

        else:
                st.markdown(f"**Differentialdiagnosen:** \n{st.session_state.user_ddx2}")
                st.markdown(
                    f"**Versorgungssetting (Verdacht):** \n{st.session_state.get('therapie_setting_verdacht', '')}"
                )
                st.markdown(f"**Diagnostische Maßnahmen:** \n{st.session_state.user_diagnostics}")
                if st.session_state.get("diagnostik_setting_kongruent") is False:
                    st.warning(
                        "⚠️ Für diese Eingabe liegt eine Setting-Diskrepanz vor. "
                        "Bitte überarbeiten Sie die Diagnostik in diesem Schritt."
                    )
                    if st.session_state.get("diagnostik_setting_kongruenz_hinweis"):
                        st.info(
                            f"Begründung der KI-Prüfung: {st.session_state.get('diagnostik_setting_kongruenz_hinweis')}"
                        )

        if (
            not st.session_state.get("diagnostik_edit_mode", True)
            and st.session_state.get("diagnostik_setting_kongruent", False) is True
            and st.session_state.get("user_ddx2", "").strip()
            and st.session_state.get("user_diagnostics", "").strip()
        ):
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
        
        # --- Labor Modul für zusätzliche Runden ---
        with st.expander("🧪 Laboranforderung für diesen Termin"):
            st.info("Markieren Sie die Parameter für die Verlaufskontrolle.")
            lab_checkboxes_rX = {}
            cols2 = st.columns(3)
            
            with cols2[0]:
                for cat in ["Hämatologie", "Gerinnung", "Kardial", "Blutkulturen"]:
                    st.markdown(f"**{cat}**")
                    for item in LABOR_KATEGORIEN[cat]:
                        lab_checkboxes_rX[item] = st.checkbox(item, key=f"lab_{item}_r{neuer_termin}")
            
            with cols2[1]:
                for cat in ["Klin. Chemie", "Leber / Pankreas", "Weitere Organe"]:
                    st.markdown(f"**{cat}**")
                    for item in LABOR_KATEGORIEN[cat]:
                        lab_checkboxes_rX[item] = st.checkbox(item, key=f"lab_{item}_r{neuer_termin}")
                        
            with cols2[2]:
                for cat in ["Infektionsserologie", "Urindiagnostik", "Stuhldiagnostik"]:
                    st.markdown(f"**{cat}**")
                    for item in LABOR_KATEGORIEN[cat]:
                        lab_checkboxes_rX[item] = st.checkbox(item, key=f"lab_{item}_r{neuer_termin}")

            st.markdown("---")
            labor_freitext_rX = st.text_input("Weitere Laborparameter (Freitext):", key=f"labor_freitext_r{neuer_termin}")

        neue_diagnostik = st.text_area(
            "Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern? (EKG, Bildgebung)",
            key=f"eingabe_diag_r{neuer_termin}"
        )
        submitted = st.form_submit_button("✅ Diagnostik anfordern")

    if submitted:
        # Labor für neue Runde extrahieren
        gewaehlte_labore_rX = [lab for lab, checked in lab_checkboxes_rX.items() if checked]
        if labor_freitext_rX.strip():
            gewaehlte_labore_rX.append(labor_freitext_rX.strip())
            
        labor_string_rX = ", ".join(gewaehlte_labore_rX) if gewaehlte_labore_rX else "Kein spezifisches Labor angefordert"

        if neue_diagnostik.strip():
            kombinierte_eingabe = f"{neue_diagnostik.strip()}\n\nAngeforderte Laborwerte: {labor_string_rX}"
        else:
            kombinierte_eingabe = f"Angeforderte Laborwerte: {labor_string_rX}"

        st.session_state[f"diagnostik_runde_{neuer_termin}"] = kombinierte_eingabe

        szenario = st.session_state.get("diagnose_szenario", "")
        client = st.session_state.get("openai_client")
        if is_offline():
            befund = generiere_befund(client, szenario, kombinierte_eingabe)
            st.session_state[f"befunde_runde_{neuer_termin}"] = befund
        else:
            ladeaufgaben = [
                "Übertrage neue Diagnostik an das Modell",
                "Stimme Ergebnisse mit bisherigen Befunden ab",
                "Bereite Rückmeldung für die Anzeige auf",
            ]
            with task_spinner("GPT erstellt Befunde...", ladeaufgaben) as indikator:
                indikator.advance(1)
                befund = generiere_befund(client, szenario, kombinierte_eingabe)
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

st.markdown(
    """
    <style>
    div.st-key-weiter-diagnose-therapie button[kind="secondary"] {
        background-color: #22a06b;
        color: #ffffff;
        border: 1px solid #1b7f54;
        border-radius: 0.75rem;
        font-weight: 600;
        padding: 0.6rem 1rem;
    }

    div.st-key-weiter-diagnose-therapie button[kind="secondary"]:hover {
        background-color: #1b7f54;
        border-color: #166c47;
    }

    div.st-key-weiter-diagnose-therapie button[kind="secondary"]:disabled {
        background-color: #d5d8de;
        color: #5d6573;
        border: 1px solid #bcc2cc;
        cursor: not-allowed;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

render_next_page_link(
    "pages/5_Diagnose_und_Therapie.py",
    label="Weiter zur Diagnose und Therapie",
    icon="💊",
    disabled="befunde" not in st.session_state,
    as_button=True,
    button_key="weiter-diagnose-therapie",
)

copyright_footer()
