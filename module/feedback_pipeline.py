"""Hilfsfunktionen für die parallele Erstellung des Abschlussfeedbacks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st

from module.feedback_tasks import FeedbackTask, get_default_feedback_tasks
from module.token_counter import add_usage, init_token_counters


@dataclass
class FeedbackContext:
    """Bündelt alle Rohinformationen, die jeder Abschnitt benötigt."""

    diagnose_szenario: str
    anzahl_termine: int
    user_verlauf: str
    diagnostik_eingaben: str
    gpt_befunde: str
    koerper_befund: str
    user_ddx2: str
    final_diagnose: str
    therapie_vorschlag: str
    patient_forms_dativ: str
    patient_forms_genitiv: str
    amboss_zusammenfassung: str = ""

    def build_context_block(self) -> str:
        """Erstellt den gemeinsamen Kontexttext für alle Modellaufrufe."""

        teile: List[str] = []
        # Kontextblöcke werden als Markdown-Abschnitte formatiert, damit das
        # Modell beim Lesen sofort erkennt, welche Informationen zusammengehören.
        teile.append(
            "### Szenario\n"
            f"{self.diagnose_szenario or 'Kein Szenario hinterlegt.'}\n"
            "\n"
            "### Anzahl der Termine\n"
            f"{self.anzahl_termine} Termin(e) wurden dokumentiert."
        )
        teile.append(
            "### Gesprächsverlauf des Studierenden\n"
            f"{self.user_verlauf or 'Keine Fragen dokumentiert.'}"
        )
        teile.append(
            "### Körperliche Untersuchung & Diagnostikbefunde\n"
            f"{self.koerper_befund or 'Kein körperlicher Befund eingetragen.'}\n"
            f"{self.gpt_befunde or 'Keine diagnostischen Befunde dokumentiert.'}"
        )
        teile.append(
            "### Geplante Diagnostik\n"
            f"{self.diagnostik_eingaben or 'Keine Diagnostikvorschläge hinterlegt.'}"
        )
        teile.append(
            "### Differentialdiagnosen\n"
            f"{self.user_ddx2 or 'Keine Differentialdiagnosen angegeben.'}"
        )
        teile.append(
            "### Finale Diagnose & Therapieplan\n"
            f"Diagnose: {self.final_diagnose or 'Keine Angabe.'}\n"
            f"Therapie: {self.therapie_vorschlag or 'Keine Angabe.'}"
        )
        if self.amboss_zusammenfassung:
            teile.append(
                "### AMBOSS-Kompass\n"
                f"{self.amboss_zusammenfassung}"
            )
        return "\n\n".join(teile)


SYSTEM_PROMPT = (
    "Du agierst als prüfungserfahrene:r Fachärzt:in. Du sprichst die Studierenden in der "
    "zweiten Person an, formulierst wertschätzend und gibst klare Empfehlungen."
)


def _build_messages(context: FeedbackContext, task: FeedbackTask) -> List[Dict[str, str]]:
    """Erzeugt das Nachrichtenformat für den jeweiligen Abschnitt."""

    basistext = (
        "Ein Medizinstudierender hat eine virtuelle Fallbesprechung mit "
        f"{context.patient_forms_dativ} durchgeführt. Du bewertest ausschließlich die "
        f"Eingaben und Entscheidungen des Studierenden – nicht die Antworten {context.patient_forms_genitiv} "
        "oder automatisch erzeugte Inhalte.\n\n"
        f"{context.build_context_block()}"
    )

    aufgabe = (
        f"Erstelle den Abschnitt \"{task.title}\". {task.instruction} "
        "Schreibe höchstens fünf prägnante Sätze, verwende dabei konkrete Beobachtungen "
        "aus dem Kontext."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": basistext + "\n\n" + aufgabe},
    ]


def _run_single_task(
    client,
    task: FeedbackTask,
    messages: Iterable[Dict[str, str]],
    *,
    temperature: float,
) -> Tuple[FeedbackTask, str, Dict[str, int]]:
    """Führt einen einzelnen Modellaufruf aus und sammelt die Tokenwerte."""

    model_name = task.model or getattr(client, "default_model", "gpt-4")
    response = client.chat.completions.create(
        model=model_name,
        messages=list(messages),
        temperature=temperature,
    )
    usage = {
        "prompt": int(getattr(response.usage, "prompt_tokens", 0) or 0),
        "completion": int(getattr(response.usage, "completion_tokens", 0) or 0),
        "total": int(getattr(response.usage, "total_tokens", 0) or 0),
    }
    content = response.choices[0].message.content
    return task, content, usage


def run_feedback_pipeline(
    client,
    context: FeedbackContext,
    *,
    tasks: Optional[List[FeedbackTask]] = None,
    temperature: float = 0.4,
) -> List[Tuple[FeedbackTask, str]]:
    """Startet alle Feedback-Aufgaben parallel und liefert sortierte Ergebnisse."""

    init_token_counters()
    tasks = tasks or get_default_feedback_tasks()
    ergebnisse: Dict[str, Tuple[FeedbackTask, str]] = {}

    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as executor:
        # Jeder Abschnitt wird als eigenständige Future gestartet. Dadurch lassen
        # sich Laufzeiten deutlich reduzieren, wenn mehrere Kerne zur Verfügung
        # stehen.
        futures = {
            executor.submit(
                _run_single_task,
                client,
                task,
                _build_messages(context, task),
                temperature=temperature,
            ): task
            for task in tasks
        }

        for future in as_completed(futures):
            task = futures[future]
            result_task, content, usage = future.result()
            ergebnisse[result_task.identifier] = (result_task, content)
            # Die Token-Auswertung wird zentral im Hauptthread fortgeschrieben,
            # um Race-Conditions mit dem Streamlit-Session-State zu vermeiden.
            add_usage(
                prompt_tokens=usage["prompt"],
                completion_tokens=usage["completion"],
                total_tokens=usage["total"],
            )

    sortierte_ergebnisse = [
        ergebnisse[task.identifier]
        for task in tasks
        if task.identifier in ergebnisse
    ]

    if len(sortierte_ergebnisse) != len(tasks):
        fehlende = [task.identifier for task in tasks if task.identifier not in ergebnisse]
        raise RuntimeError(
            "Mindestens ein Feedbackabschnitt konnte nicht erzeugt werden: "
            + ", ".join(fehlende)
        )

    return sortierte_ergebnisse


def combine_sections(sections: List[Tuple[FeedbackTask, str]]) -> str:
    """Setzt die Modellantworten in der vorgesehenen Reihenfolge zusammen."""

    # Durch das einfache Aneinanderfügen bleibt das Layout der einzelnen
    # Abschnitte erhalten und kann bei Bedarf im UI weiterverarbeitet werden.
    return "\n\n".join(text for _, text in sections)


def preprocess_amboss_payload(
    client,
    payload: Optional[Dict],
    diagnose_szenario: str,
) -> str:
    """Fasst das AMBOSS-Payload mit gpt-4o-mini kompakt zusammen."""

    if not payload:
        return ""

    # Hinweis für spätere Debug-Sessions: Die folgende Zeile kann einkommentiert werden,
    # um den Rohinhalt zu inspizieren: ``st.write(payload)``.

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du extrahierst die wichtigsten Fakten aus einem AMBOSS-JSON. "
                        "Fasse prägnant zusammen, was für die Bewertung der studentischen "
                        "Entscheidungen wichtig ist."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Szenario: "
                        f"{diagnose_szenario or 'unbekannt'}\n"
                        "JSON-Inhalt:\n"
                        f"{json.dumps(payload, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.1,
        )
    except Exception as exc:  # pragma: no cover - reine Laufzeitfehler
        st.warning(
            "⚠️ Das AMBOSS-Payload konnte nicht vorverarbeitet werden. "
            "Details sind im Debug-Log verfügbar."
        )
        # Optionales Debugging: ``st.write('AMBOSS-Preprocessing fehlgeschlagen:', exc)``.
        return ""

    usage = {
        "prompt": int(getattr(response.usage, "prompt_tokens", 0) or 0),
        "completion": int(getattr(response.usage, "completion_tokens", 0) or 0),
        "total": int(getattr(response.usage, "total_tokens", 0) or 0),
    }
    add_usage(
        prompt_tokens=usage["prompt"],
        completion_tokens=usage["completion"],
        total_tokens=usage["total"],
    )

    return response.choices[0].message.content


__all__ = [
    "FeedbackContext",
    "combine_sections",
    "preprocess_amboss_payload",
    "run_feedback_pipeline",
]
