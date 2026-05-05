import streamlit as st
from datetime import datetime
import streamlit.components.v1 as components
from module.untersuchungsmodul import (
    generiere_koerperbefund,
    generiere_sonderuntersuchung,
)
from module.navigation import redirect_to_start_page, render_next_page_link
from openai import RateLimitError
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline
from module.loading_indicator import task_spinner

copyright_footer()
show_sidebar()
display_offline_banner()

st.session_state.setdefault("koerper_befund_generating", False)
st.session_state.setdefault("sonder_untersuchung_generating", False)

# Die Eingabe für Sonderuntersuchungen erhält einen definierten Ausgangswert.
# So bleibt das Textfeld auch beim ersten Laden der Seite konsistent befüllt
# (hier: bewusst leer) und wir vermeiden Fehlermeldungen durch späte Zuweisungen.
st.session_state.setdefault("sonderuntersuchung_input", "")

# Falls ein vorheriger Durchlauf das Textfeld gezielt leeren wollte, wird dies
# hier umgesetzt. Die Pop-Operation erfolgt vor der Widget-Instanziierung,
# damit Streamlit keine Mutation eines bereits existierenden Widgets meldet.
if st.session_state.pop("sonderuntersuchung_input_leeren", False):
    st.session_state["sonderuntersuchung_input"] = ""


def aktualisiere_befundanzeige() -> None:
    """Bereitet den Basisbefund plus alle Zusatzblöcke für die Anzeige auf."""
    basis = st.session_state.get("koerper_befund_basis", "").strip()
    zusatzbloecke = [
        eintrag.get("anzeige", "").strip()
        for eintrag in st.session_state.get("sonderuntersuchungen", [])
        if eintrag.get("anzeige")
    ]
    teile = [abschnitt for abschnitt in [basis, *zusatzbloecke] if abschnitt]
    st.session_state["koerper_befund"] = "\n\n".join(teile).strip()


def aktualisiere_sonderdiagnostik_prefix() -> None:
    """Synchronisiert Zusatzuntersuchungen für Diagnostik- und Befundexporte."""

    def _rekonstruiere_befundgrundlage() -> str:
        """Setzt alle bisher generierten Befunde (Termin 1 ff.) erneut zusammen."""

        passagen = []
        erster_befund = st.session_state.get("befunde", "").strip()
        if erster_befund:
            passagen.append(f"### Termin 1\n{erster_befund}")

        gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
        for termin in range(2, gesamt + 1):
            key = f"befunde_runde_{termin}"
            text = st.session_state.get(key, "").strip()
            if text:
                passagen.append(f"### Termin {termin}\n{text}")

        return "\n---\n".join(passagen).strip()

    sonderliste = st.session_state.get("sonderuntersuchungen", [])
    if not sonderliste:
        # Sobald keine Zusatzuntersuchungen mehr vorhanden sind, entfernen wir
        # alle Zusatzfelder aus dem Session-State und stellen die Basiswerte her.
        st.session_state.pop("sonderdiagnostik_text", None)
        st.session_state.pop("sonderdiagnostik_befund_text", None)

        basis_diag = st.session_state.get("diagnostik_eingaben_basis", "").strip()
        st.session_state["diagnostik_eingaben_kumuliert"] = basis_diag

        basis_befund = _rekonstruiere_befundgrundlage()
        if basis_befund:
            st.session_state["gpt_befunde_kumuliert"] = basis_befund
        elif "gpt_befunde_kumuliert" in st.session_state:
            st.session_state["gpt_befunde_kumuliert"] = ""
        return

    diag_abschnitte = []
    befund_abschnitte = []
    for index, eintrag in enumerate(sonderliste, start=1):
        anforderung = eintrag.get("anforderung", "").strip() or "(keine Angabe)"
        ergebnis = eintrag.get("diagnostik", "").strip()

        # Die Diagnostik-Dokumentation erhält nur den Wunsch selbst – Supabase
        # erwartet hier ausdrücklich keinen Ergebnistext.
        diag_abschnitte.append(f"- erweiterte Untersuchung: {anforderung}")

        if ergebnis:
            kurzfassung = ergebnis.strip()
            befund_abschnitte.append(
                f"- Erweiterte Untersuchung {index}: {kurzfassung or '(kein Ergebnis hinterlegt)'}"
            )
        else:
            befund_abschnitte.append(
                f"- Erweiterte Untersuchung {index}: (kein Ergebnis hinterlegt)"
            )

    sondertext_diag = "\n".join(diag_abschnitte).strip()
    sondertext_befund = "\n".join(befund_abschnitte).strip()

    if sondertext_diag:
        sondertext_diag = f"### Erweiterte Untersuchungen\n{sondertext_diag}"
        st.session_state["sonderdiagnostik_text"] = sondertext_diag

    if sondertext_befund:
        sondertext_befund = f"### Erweiterte Untersuchungen\n{sondertext_befund}"
        st.session_state["sonderdiagnostik_befund_text"] = sondertext_befund

    basis_diag = st.session_state.get("diagnostik_eingaben_basis", "").strip()
    kombinierte_diag = "\n\n".join(teil for teil in [basis_diag, sondertext_diag] if teil).strip()
    st.session_state["diagnostik_eingaben_kumuliert"] = kombinierte_diag

    basis_befund = _rekonstruiere_befundgrundlage()
    kombinierte_befunde = "\n\n".join(
        teil for teil in [basis_befund, sondertext_befund] if teil
    ).strip()
    st.session_state["gpt_befunde_kumuliert"] = kombinierte_befunde


# Standardinitialisierung
st.session_state.setdefault("sonderuntersuchungen", [])

if "koerper_befund" in st.session_state and "koerper_befund_basis" not in st.session_state:
    st.session_state["koerper_befund_basis"] = st.session_state["koerper_befund"]

# Voraussetzungen prüfen
if (
    "diagnose_szenario" not in st.session_state or
    "patient_name" not in st.session_state or
    "patient_age" not in st.session_state or
    "patient_job" not in st.session_state or
    "diagnose_features" not in st.session_state
):
    redirect_to_start_page("⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite.")

if "start_untersuchung" not in st.session_state:
    st.session_state.start_untersuchung = datetime.now()

# Bedingung: mindestens eine Anamnesefrage gestellt
fragen_gestellt = any(m["role"] == "user" for m in st.session_state.get("messages", []))

if "koerper_befund" in st.session_state:
    aktualisiere_befundanzeige()
    st.success("✅ Körperliche Untersuchung erfolgt.")
    st.subheader("🔍 Befund")
    st.markdown(st.session_state.koerper_befund)

    st.markdown("---")
    sonder_input = st.text_area(
        "➕ Option: weitere körperliche Untersuchungen durchführen - bitte spezifizieren:",
        key="sonderuntersuchung_input",
    )

    if st.button(
        "Anforderung absenden",
        disabled=st.session_state.get("sonder_untersuchung_generating", False)
        or st.session_state.get("koerper_befund_generating", False),
    ):
        if not sonder_input.strip():
            st.warning("Bitte gib eine konkrete Untersuchung an, bevor du absendest.")
        else:
            st.session_state["sonder_untersuchung_generating"] = True
            
            try:
                is_labor = False
                client = st.session_state.get("openai_client")
                
                # --- KI Pre-Check ---
                if client and not is_offline():
                    sonderaufgaben = [
                        "Prüfe Untersuchungstyp",
                        "Analysiere Anforderung",
                        "Beziehe bisherigen Befund ein",
                        "Formuliere Zusatzbefund",
                    ]
                    with task_spinner(
                        "Anforderung wird analysiert...",
                        sonderaufgaben,
                    ) as indikator:
                        # 1. Intent-Check
                        check_prompt = f"""Entscheide, ob in der folgenden ärztlichen Anforderung apparative Diagnostik (wie EKG, Röntgen, CT, MRT, Ultraschall) oder Labor (wie Blut, Urin, Abstriche) angefordert wird.
WICHTIG: Rein körperliche Untersuchungen (z.B. Blutdruck messen, Puls, Auskultation, Palpation, Inspektion, Reflexe) sind HIER ERLAUBT.
Antworte AUSSCHLIESSLICH mit 'JA', wenn Labor/Bildgebung/Apparative Diagnostik verlangt wird. Antworte mit 'NEIN', wenn es sich um eine rein körperliche Untersuchung handelt.
Anforderung: {sonder_input.strip()}"""
                        try:
                            antwort = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": check_prompt}],
                                temperature=0,
                                max_tokens=5
                            )
                            if "JA" in antwort.choices[0].message.content.upper():
                                is_labor = True
                        except Exception:
                            pass
                        indikator.advance(1)
                        
                        # 2. Reagieren je nach Typ
                        if is_labor:
                            sonder_befund = "ℹ️ **Hinweis:** In diesem Schritt geht es ausschließlich um die klinisch-körperliche Untersuchung. Laborwerte, Bildgebung und apparative Diagnostik können Sie im nächsten Schritt ('Diagnostik und Befunde') anfordern."
                            indikator.advance(1)
                            indikator.advance(1)
                            indikator.advance(1)
                        else:
                            indikator.advance(1)
                            sonder_befund = generiere_sonderuntersuchung(
                                client,
                                st.session_state.diagnose_szenario,
                                st.session_state.diagnose_features,
                                sonder_input.strip(),
                                st.session_state.get("koerper_befund_basis", ""),
                            )
                            indikator.advance(1)
                            indikator.advance(1)
                else:
                    # Fallback für den Offline-Modus
                    lower_input = sonder_input.lower()
                    labor_keywords = ["labor", "blutab", "urin", "röntgen", "xray", "ct ", "mrt", "sono", "ultraschall", "ekg", "bga", "crp"]
                    if "blutdruck" not in lower_input and any(kw in lower_input for kw in labor_keywords):
                        is_labor = True

                    if is_labor:
                        sonder_befund = "ℹ️ **Hinweis:** In diesem Schritt geht es ausschließlich um die klinisch-körperliche Untersuchung. Laborwerte, Bildgebung und apparative Diagnostik können Sie im nächsten Schritt ('Diagnostik und Befunde') anfordern."
                    else:
                        sonder_befund = generiere_sonderuntersuchung(
                            client,
                            st.session_state.diagnose_szenario,
                            st.session_state.diagnose_features,
                            sonder_input.strip(),
                            st.session_state.get("koerper_befund_basis", ""),
                        )
                # --- Ende KI Pre-Check ---

                neuer_block = {
                    "anforderung": sonder_input.strip(),
                    "diagnostik": sonder_befund,
                    "anzeige": sonder_befund,
                }
                st.session_state["sonderuntersuchungen"].append(neuer_block)
                aktualisiere_befundanzeige()
                aktualisiere_sonderdiagnostik_prefix()
                st.session_state["sonder_untersuchung_generating"] = False
                st.session_state["sonderuntersuchung_input_leeren"] = True
                st.success("Die Eingabe wurde verarbeitet.")
                st.rerun()
            except RateLimitError:
                st.session_state["sonder_untersuchung_generating"] = False
                st.error(
                    "🚫 Die Verarbeitung konnte nicht erfolgen. Die OpenAI-API ist aktuell ausgelastet."
                )
            except Exception as err:
                st.session_state["sonder_untersuchung_generating"] = False
                st.error(f"❌ Fehler bei der Verarbeitung: {err}")

elif fragen_gestellt:
    if not st.session_state.get("koerper_befund_generating", False):
        st.session_state.koerper_befund_generating = True
        try:
            if is_offline():
                koerper_befund = generiere_koerperbefund(
                    st.session_state.get("openai_client"),
                    st.session_state.diagnose_szenario,
                    st.session_state.diagnose_features,
                    st.session_state.get("koerper_befund_tip", ""),
                )
                st.session_state.koerper_befund_basis = koerper_befund
                st.session_state["sonderuntersuchungen"] = []
                aktualisiere_befundanzeige()
                aktualisiere_sonderdiagnostik_prefix()
            else:
                untersuchungsaufgaben = [
                    "Sammle anamnestische Schlüsselhinweise",
                    "Berechne passende Untersuchungsbefunde",
                    "Bereite Ergebnistext für die Anzeige auf",
                ]
                with task_spinner(
                    f"{st.session_state.patient_name} wird untersucht...",
                    untersuchungsaufgaben,
                ) as indikator:
                    indikator.advance(1)
                    koerper_befund = generiere_koerperbefund(
                        st.session_state["openai_client"],
                        st.session_state.diagnose_szenario,
                        st.session_state.diagnose_features,
                        st.session_state.get("koerper_befund_tip", ""),
                    )
                    indikator.advance(1)
                    st.session_state.koerper_befund_basis = koerper_befund
                    st.session_state["sonderuntersuchungen"] = []
                    aktualisiere_befundanzeige()
                    aktualisiere_sonderdiagnostik_prefix()
                    indikator.advance(1)
            st.session_state.koerper_befund_generating = False
            if is_offline():
                st.info(
                    "🔌 Offline-Befund geladen. Sobald der Online-Modus aktiv ist, kannst du einen KI-generierten Befund abrufen."
                )
            st.rerun()
        except RateLimitError:
            st.session_state.koerper_befund_generating = False
            st.error("🚫 Die Untersuchung konnte nicht erstellt werden. Die OpenAI-API ist derzeit überlastet.")
        except Exception as err:
            st.session_state.koerper_befund_generating = False
            st.error(f"❌ Unerwarteter Fehler bei der Untersuchung: {err}")

    if st.button(
        "🩺 Untersuchung durchführen",
        disabled=st.session_state.get("koerper_befund_generating", False),
    ):
        st.session_state.koerper_befund_generating = True
        try:
            if is_offline():
                koerper_befund = generiere_koerperbefund(
                    st.session_state.get("openai_client"),
                    st.session_state.diagnose_szenario,
                    st.session_state.diagnose_features,
                    st.session_state.get("koerper_befund_tip", "")
                )
                st.session_state.koerper_befund_basis = koerper_befund
                st.session_state["sonderuntersuchungen"] = []
                aktualisiere_befundanzeige()
                aktualisiere_sonderdiagnostik_prefix()
            else:
                untersuchungsaufgaben = [
                    "Sammle anamnestische Schlüsselhinweise",
                    "Berechne passende Untersuchungsbefunde",
                    "Bereite Ergebnistext für die Anzeige auf",
                ]
                with task_spinner(
                    f"{st.session_state.patient_name} wird untersucht...",
                    untersuchungsaufgaben,
                ) as indikator:
                    indikator.advance(1)
                    koerper_befund = generiere_koerperbefund(
                        st.session_state["openai_client"],
                        st.session_state.diagnose_szenario,
                        st.session_state.diagnose_features,
                        st.session_state.get("koerper_befund_tip", "")
                    )
                    indikator.advance(1)
                    st.session_state.koerper_befund_basis = koerper_befund
                    st.session_state["sonderuntersuchungen"] = []
                    aktualisiere_befundanzeige()
                    aktualisiere_sonderdiagnostik_prefix()
                    indikator.advance(1)
            st.session_state.koerper_befund_generating = False
            if is_offline():
                st.info("🔌 Offline-Befund geladen. Sobald der Online-Modus aktiv ist, kannst du einen KI-generierten Befund abrufen.")
            st.rerun()
        except RateLimitError:
            st.session_state.koerper_befund_generating = False
            st.error("🚫 Die Untersuchung konnte nicht erstellt werden. Die OpenAI-API ist derzeit überlastet.")
        except Exception as err:
            st.session_state.koerper_befund_generating = False
            st.error(f"❌ Unerwarteter Fehler bei der Untersuchung: {err}")
else:
    st.subheader("🩺 Untersuchung")
    st.button(
        "Untersuchung durchführen",
        disabled=True,
    )
    st.info(f"Zuerst bitte mit {st.session_state.patient_name} sprechen.", icon="🔒")
    st.page_link("pages/1_Anamnese.py", label="Zurück zur Anamnese", icon="⬅")
    
if "untersuchung_done" not in st.session_state:
    st.session_state.untersuchung_done = True

st.markdown("---")

st.markdown(
    """
    <style>
    div.st-key-weiter-diagnostik button[kind="secondary"] {
        background-color: #22a06b;
        color: #ffffff;
        border: 1px solid #1b7f54;
        border-radius: 0.75rem;
        font-weight: 600;
        padding: 0.6rem 1rem;
    }

    div.st-key-weiter-diagnostik button[kind="secondary"]:hover {
        background-color: #1b7f54;
        border-color: #166c47;
    }

    div.st-key-weiter-diagnostik button[kind="secondary"]:disabled {
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
    "pages/4_Diagnostik_und_Befunde.py",
    label="Weiter zur Diagnostik",
    icon="🧪",
    disabled="koerper_befund" not in st.session_state,
    as_button=True,
    button_key="weiter-diagnostik",
)
