def feedback_erzeugen(
    client,
    diagnose,
    therapie,
    ddx,
    untersuchungen,
    befunde,
    koerperlich,
    user_input,
    termine
):
    prompt = f"""
Die Nutzerin hat folgende finale Diagnose angegeben:
{diagnose}

Therapiekonzept:
{therapie}

Differentialdiagnosen:
{ddx}

Durchgeführte Diagnostik:
{untersuchungen}

Befunde (GPT-generiert):
{befunde}

Körperliche Untersuchung:
{koerperlich}

Benutzereingaben im Chat:
{user_input}

Die Fallbearbeitung umfasste {termine} Diagnostik-Termine.

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
