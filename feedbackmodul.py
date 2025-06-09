def feedback_erzeugen(
    client,
    final_diagnose,
    therapie_vorschlag,
    user_ddx2,
    diagnostik_eingaben,
    gpt_befunde,
    koerper_befund,
    user_verlauf,
    anzahl_termine
):
    prompt = f"""
Die Nutzerin hat folgende finale Diagnose angegeben:
{final_diagnose}

Therapiekonzept:
{therapie_vorschlag}

Differentialdiagnosen:
{user_ddx2}

Durchgeführte Diagnostik:
{diagnostik_eingaben}

Befunde (GPT-generiert):
{gpt_befunde}

Körperliche Untersuchung:
{koerper_befund}

Benutzereingaben im Chat:
{user_verlauf}

Die Fallbearbeitung umfasste {anzahl_termine} Diagnostik-Termine.

Bitte gib eine strukturierte Rückmeldung in drei Teilen:
1. Vollständigkeit und Relevanz der Differentialdiagnosen
2. Qualität und Zielgerichtetheit der diagnostischen Strategie
3. Schlüssigkeit und Praktikabilität des Therapievorschlags

Jeder Teil soll in einem Absatz beantwortet werden.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content
