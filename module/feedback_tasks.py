"""Definiert die modularen Arbeitsschritte für das parallele Feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class FeedbackTask:
    """Beschreibt einen einzelnen Abschnitt des Feedbacks."""

    identifier: str
    """Eindeutiger Schlüssel, damit Ergebnisse eindeutig zugeordnet werden können."""

    title: str
    """Überschrift, die im finalen Feedback als Abschnittstitel erscheinen soll."""

    instruction: str
    """Aufgabenbeschreibung, die als Prompt an das Modell gesendet wird."""

    model: Optional[str] = None
    """Optionales Spezialmodell, falls ein Abschnitt mit einem anderen Modell laufen soll."""


def get_default_feedback_tasks() -> List[FeedbackTask]:
    """Stellt die Feedbackabschnitte in der gewünschten Reihenfolge bereit."""

    # Die Liste ist bewusst modular aufgebaut, damit zukünftige Abschnitte
    # einfach ergänzt oder ausgetauscht werden können.
    return [
        FeedbackTask(
            identifier="intro",
            title="Überblick & Szenario",
            instruction=(
                "Stelle zu Beginn das Szenario mit einem klaren Satz vor, benenne die "
                "Anzahl der absolvierten Diagnostik-Termine und bewerte explizit, ob "
                "die finale Diagnose korrekt ist. Formuliere außerdem eine knappe "
                "Gesamtwürdigung (Stärken und grösste Baustelle)."
            ),
        ),
        FeedbackTask(
            identifier="anamnese",
            title="Anamnese",
            instruction=(
                "Bewerte, ob die anamnestischen Fragen vollständig, strukturiert und "
                "patientenorientiert gestellt wurden. Gehe auf verpasste Kernfragen ein "
                "und würdige konkrete gelungene Nachfragen."
            ),
        ),
        # Die nächsten Abschnitte bilden exakt die Reihenfolge der ursprünglichen
        # Stichpunkte ab, damit das Endfeedback vertraut bleibt.
        FeedbackTask(
            identifier="diagnostik_szenario",
            title="Diagnostik für das Szenario",
            instruction=(
                "Analysiere die diagnostischen Maßnahmen im Hinblick auf die vorgegebene "
                "Szenariodiagnose. Erläutere, welche Schritte sinnvoll waren und wo "
                "wichtige Untersuchungen gefehlt haben."
            ),
        ),
        FeedbackTask(
            identifier="diagnostik_ddx",
            title="Diagnostik für Differentialdiagnosen",
            instruction=(
                "Prüfe, ob die gewählte Diagnostik den angegebenen Differentialdiagnosen "
                "gerecht wird. Benenne Lücken sowie besonders treffende Entscheidungen."
            ),
        ),
        FeedbackTask(
            identifier="strategie",
            title="Struktur der Diagnostik",
            instruction=(
                "Beurteile Aufbau und Reihenfolge der Termine. Erwähne unnötige Doppeluntersuchungen, "
                "sinnvolle Eskalationen und fehlende Folgeuntersuchungen."
            ),
        ),
        FeedbackTask(
            identifier="diagnose",
            title="Finale Diagnose",
            instruction=(
                "Erkläre, ob die finale Diagnose anhand der vorliegenden Informationen plausibel ist "
                "und wie gut andere Optionen abgegrenzt wurden."
            ),
        ),
        FeedbackTask(
            identifier="therapie",
            title="Therapiekonzept",
            instruction=(
                "Bewerte das Therapiekonzept hinsichtlich Leitlinien, Plausibilität und praktischer Umsetzung."
            ),
        ),
        FeedbackTask(
            identifier="nachhaltigkeit",
            title="Nachhaltigkeit & Ökonomie",
            instruction=(
                "Analysiere ökologische sowie ökonomische Aspekte. Hebe unnötige Ressourcenbelastungen "
                "oder Einsparpotenziale hervor und begründe, falls zu wenig Diagnostik ebenfalls nachteilig ist."
            ),
        ),
    ]


__all__ = ["FeedbackTask", "get_default_feedback_tasks"]
