def generiere_befund(client, szenario, neue_diagnostik):
    prompt = f"""Die Patientin hat laut Szenario: {szenario}.
Folgende zusätzliche Diagnostik wurde angefordert:
{neue_diagnostik}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen.

Falls **Laborwerte** angefordert wurden, gib sie bitte **nur in folgender Tabellenform** aus:

**Parameter** | **Wert** | **Referenzbereich (SI-Einheit)**

🔒 Verwende **ausschließlich SI-Einheiten** (z. B. mmol/l, µmol/l, Gpt/l, g/L, U/l). Werte in mg/dL oder µg/mL sind **nicht erlaubt**.

📌 Nutze niemals Einheiten wie mg/dL, ng/mL, µg/L oder % – ersetze diese durch SI-konforme Angaben.  

Gib die Befunde **strukturiert, sachlich und ohne Interpretation** wieder. Nenne **nicht das Diagnose-Szenario**. Ergänze keine nicht angeforderten Untersuchungen."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()
