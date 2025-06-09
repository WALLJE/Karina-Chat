def generiere_befund(client, szenario, neue_diagnostik):
    prompt = f"""Die Patientin hat laut Szenario: {szenario}.
Folgende zusätzliche Diagnostik wurde angefordert:
{neue_diagnostik}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen. Falls **Laborwerte** angefordert wurden, gib diese **ausschließlich in einer strukturierten Tabelle** aus, verwende dabei SI bzw. Internationale Einheiten wie mmol/l oder Gpt/l und folgendes Tabellenformat:

**Parameter** | **Wert** | **Referenzbereich (SI-Einheit)**.

**Wichtig:** Interpretationen oder Diagnosen sind nicht erlaubt. Nenne auf keinen Fall das Diagnose-Szenario. Bewerte oder diskutiere nicht die Anforderungen.

Gib die Befunde strukturiert und sachlich wieder. Ergänze keine nicht angeforderten Untersuchungen."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()
