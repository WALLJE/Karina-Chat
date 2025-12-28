from module.token_counter import init_token_counters, add_usage
from module.gpt_timing import messe_gpt_aktion
from module.patient_language import get_patient_forms
from module.offline import get_offline_befund, is_offline

def generiere_befund(client, szenario, neue_diagnostik):
    if is_offline():
        return get_offline_befund(neue_diagnostik)

    patient_forms = get_patient_forms()

    prompt = f"""{patient_forms.phrase("nom", capitalize=True)} hat laut Szenario: {szenario}.
Folgende zusätzliche Diagnostik wurde angefordert:
{neue_diagnostik}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen.

Falls **Laborwerte** angefordert wurden, gib sie bitte **nur in folgender Tabellenform** aus:

**Parameter** | **Wert** | **Referenzbereich (SI-Einheit)**

🔒 Verwende **ausschließlich SI-Einheiten** (z. B. mmol/l, µmol/l, Gpt/l, g/L, U/l). Werte in mg/dL oder µg/mL sind **nicht erlaubt**.

📌 Nutze niemals Einheiten wie mg/dL, ng/mL, µg/L oder % – ersetze diese durch SI-konforme Angaben.  

Gib die Befunde **strukturiert, sachlich und ohne Interpretation** wieder. Nenne **nicht das Diagnose-Szenario**. Ergänze keine nicht angeforderten Untersuchungen."""
    init_token_counters()
    # Für strukturierte Diagnostik-Befunde ist ein präzises, aber kosteneffizientes
    # Modell ausreichend und liefert konsistente Tabellenformate.
    response = messe_gpt_aktion(
        lambda: client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        ),
        kontext="Diagnostik-Befund",
    )
    add_usage(
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens
    )
    return response.choices[0].message.content.strip()
