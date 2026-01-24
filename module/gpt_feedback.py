import streamlit as st
from supabase import create_client
from datetime import datetime
# import json
from module.token_counter import init_token_counters, get_token_sums
from module.offline import is_offline


def _spalte_verfuegbar(supabase, spaltenname: str) -> bool:
    """Prüft, ob eine Spalte in ``feedback_gpt`` vorhanden ist.

    Der leichte ``select``-Check vermeidet Insert-Fehler, wenn Deployments die
    neuen optionalen Felder (z. B. ``diagnostik_runden_gesamt``) noch nicht
    migriert haben. Für tiefergehende Analysen kann temporär
    ``st.write(spaltenname, probe)`` aktiviert werden, um die Server-Antwort zu
    inspizieren.
    """

    try:
        probe = supabase.table("feedback_gpt").select(spaltenname).limit(0).execute()
    except Exception:
        return False

    return not getattr(probe, "error", None)

def speichere_gpt_feedback_in_supabase():
    if is_offline():
        st.info("🔌 Offline-Modus: Feedback wird nicht in Supabase gespeichert.")
        st.session_state.pop("feedback_row_id", None)
        return

    jetzt = datetime.now()
    start = st.session_state.get("startzeit", jetzt)
    dauer_min = round((jetzt - start).total_seconds() / 60, 1)

    # Token-Summen holen
    init_token_counters()
    prompt_sum, completion_sum, total_sum = get_token_sums()

    # Chatverlauf ohne system-prompt
    patient_name = st.session_state.get("patient_name", "Patient")
    verlauf = "\n".join([
        f"Du: {m['content']}" if m['role'] == 'user' else f"{patient_name}: {m['content']}"
        for m in st.session_state.get("messages", [])[1:]
    ])

    # Befunde aus erster Runde
    befunde = st.session_state.get("befunde", "")

    # Weitere Befunde
    weitere_befunde = ""
    gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
    for i in range(2, gesamt + 1):
        bef_key = f"befunde_runde_{i}"
        inhalt = st.session_state.get(bef_key, "")
        if inhalt:
            weitere_befunde += f"\n\n📅 Termin {i}:{inhalt}"

    alle_befunde = befunde + weitere_befunde

    # Sammlung aller zu speichernden Felder für Supabase. Alle Schlüssel
    # spiegeln die Tabellenspalten von ``feedback_gpt`` wider, sodass Admins
    # die Fälle später unverändert wiederverwenden können. Zusätzliche
    # Debug-Ausgaben (z. B. ``st.write(gpt_row)``) können bei Bedarf aktiviert
    # werden, um fehlerhafte oder fehlende Werte schnell zu erkennen.
    gpt_row = {
        "datum": jetzt.strftime("%Y-%m-%d"),
        "uhrzeit": jetzt.strftime("%H:%M:%S"),
        "bearbeitungsdauer_min": dauer_min,
        "szenario": st.session_state.get("diagnose_szenario", ""),
        "name": st.session_state.get("patient_name", ""),
        # Geschlecht wird explizit gespeichert. Falls die Spalte im Schema
        # fehlt, kann sie über den README-SQL-Block nachgezogen werden.
        "geschlecht": str(st.session_state.get("patient_gender", "")).strip(),
        "alter": int(st.session_state.get("patient_age", 0)),
        "beruf": st.session_state.get("patient_job", ""),
        "verhalten": st.session_state.get("patient_verhalten_memo", "unbekannt"),
        "verdachtsdiagnosen": st.session_state.get("user_ddx2", ""),
        "diagnostik": st.session_state.get("diagnostik_eingaben_kumuliert", ""),
        "finale_diagnose": st.session_state.get("final_diagnose", ""),
        "therapie": st.session_state.get("therapie_vorschlag", ""),
        "gpt_feedback": st.session_state.get("final_feedback", ""),
        "chatverlauf": verlauf,
        "befunde": alle_befunde,
        "prompt_tokens_sum": int(prompt_sum),
        "completion_tokens_sum": int(completion_sum),
        "total_tokens_sum": int(total_sum),
        # Der Feedback-Modus wird als "Client" gespeichert, damit im Supabase-Export
        # nachvollzogen werden kann, ob AMBOSS-Daten eingeflossen sind.
        "Client": st.session_state.get("feedback_mode", "ChatGPT"),
    }

    try:
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

        optionale_spalten = {
            # Gesamtanzahl der diagnostischen Runden wird als Zahl persistiert.
            # Bei nicht migriertem Schema wird die Spalte ausgelassen, damit der
            # Insert nicht scheitert. Die Werte bleiben trotzdem im RAM und
            # können nach einer Schema-Aktualisierung erneut gespeichert werden.
            "diagnostik_runden_gesamt": int(st.session_state.get("diagnostik_runden_gesamt", 1) or 1),
            # Zusammenfassung der körperlichen Untersuchung. Bleibt leer, wenn
            # kein Befund eingegeben wurde.
            "koerper_befund": st.session_state.get("koerper_befund", ""),
            # Versorgungssetting zur Verdachtsdiagnose. Dieses Feld hilft später
            # bei der Auswertung, ob ambulant/stationär korrekt eingeschätzt wurde.
            "therapie_setting_verdacht": st.session_state.get("therapie_setting_verdacht", ""),
            # Finales Therapiesetting, inklusive möglicher Facharzt-Option.
            "therapie_setting_final": st.session_state.get("therapie_setting_final", ""),
            # Kumulierte Laufzeit aller GPT-Aktionen in Sekunden. Diese Summe
            # basiert auf jedem einzelnen Modellaufruf in der Sitzung.
            "gpt_aktionsdauer_gesamt_sek": round(
                float(st.session_state.get("gpt_aktionsdauer_gesamt_sek", 0.0)),
                2,
            ),
        }

        for spaltenname, wert in optionale_spalten.items():
            if _spalte_verfuegbar(supabase, spaltenname):
                gpt_row[spaltenname] = wert
            else:
                st.warning(
                    f"⚠️ Supabase-Spalte '{spaltenname}' fehlt. Bitte den README-SQL-Block "
                    "zur Schema-Aktualisierung ausführen."
                )

        res = supabase.table("feedback_gpt").insert(gpt_row).execute()
        st.session_state["feedback_row_id"] = res.data[0]["ID"]
        # gpt_row_serialisiert = json.loads(json.dumps(gpt_row, default=str))
        # supabase.table("feedback_gpt").insert(gpt_row_serialisiert).execute()
        # DEBUG 
        # st.success("✅ GPT-Feedback wurde gespeichert.")
    except Exception as e:
        st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")
