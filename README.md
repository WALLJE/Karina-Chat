<!-- HINWEIS: Diese README wurde umfassend dokumentiert, damit neue Administratorinnen und Administratoren den Aufbau der Anwendung schnell nachvollziehen können. -->
# Karina-Chat

## Inhaltsverzeichnis
1. [Überblick](#überblick)
2. [Systemvoraussetzungen](#systemvoraussetzungen)
3. [Installation](#installation)
4. [Starten der Anwendung](#starten-der-anwendung)
5. [Grundlegende Nutzung](#grundlegende-nutzung)
    1. [Automatisches Zurücksetzen bei Direktaufrufen](#automatisches-zurücksetzen-bei-direktaufrufen)
6. [Admin-Modus](#admin-modus)
    1. [Anmeldung](#anmeldung)
    2. [Verwaltung von Fallbeispielen](#verwaltung-von-fallbeispielen)
    3. [Feedback- und Befundmodule](#feedback--und-befundmodule)
    4. [Diagnostische Funktionen](#diagnostische-funktionen)
    5. [Debugging-Hilfen](#debugging-hilfen)
7. [Fehlerbehebung](#fehlerbehebung)
8. [Weiterführende Ressourcen](#weiterführende-ressourcen)

## Überblick
Der Karina-Chat unterstützt medizinische Ausbildungsszenarien, indem realistische Patientinnen- und Patientengespräche simuliert werden. Nutzerinnen und Nutzer können zwischen verschiedenen Modulen (z. B. Sprach-, Feedback- oder Befundmodul) wechseln. Diese README fokussiert sich darauf, die wichtigsten Bedienwege zu erläutern.

<!-- Tipp: Dieser Abschnitt kann bei Bedarf erweitert werden, falls neue Module hinzukommen. -->

## Modellauswahl (optimiert für Genauigkeit, Datensparsamkeit und Kosten)
- **Patientensimulation & Sprachkorrektur:** `gpt-4o-mini` für kurze, natürliche Antworten bei geringer Latenz.
- **Körperliche Untersuchung & Diagnostik-Befunde:** `gpt-4o` für präzise, strukturierte Befundtexte mit guter Kostenkontrolle.
- **Abschlussfeedback (Prüfer-Modul):** `gpt-4.1` für hohe Instruktionsstabilität bei regelreichen Feedback-Prompts.
- **Aufklapp-Vertiefung pro Unterpunkt:** `gpt-4.1-mini` für schnelle, token-sparsame Lehrbuchtexte (ca. 150 Wörter) mit guter medizinischer Präzision.
- **AMBOSS-Zusammenfassungen:** `gpt-4o-mini` für kompakte Verdichtung großer JSON-Payloads.

Hinweis: Änderungen an der Modellauswahl erfolgen direkt in den jeweiligen Modulen. Für Debugging können Kommentare in den Dateien aktiviert werden (z. B. `st.write(prompt)`), damit Prompt und Antwortstruktur nachvollziehbar bleiben.

### Aufklapp-Vertiefung (Variante 2) – Caching und Tokenlogik
- Die Lehrbuch-Vertiefung wird **nicht vorab**, sondern erst beim Klick auf den jeweiligen Aufklappbereich erzeugt.
- Falls ein passender Text schon im Cache liegt und jünger als 3 Monate ist, wird er aus Supabase geladen.
- Ist der Cache älter als 3 Monate, wird der Text KI-gestützt aktualisiert und erneut gespeichert.
- Dadurch bleiben die Standarddurchläufe mit kompakter Bewertung tokenarm; zusätzliche Kosten entstehen nur bei tatsächlicher Nutzung.

## Systemvoraussetzungen
- Python 3.10 oder neuer
- Virtuelle Umgebung (empfohlen)
- Abhängigkeiten aus `requirements.txt`
- Optional: Zugriff auf Streamlit-Frontend (bereits vorkonfiguriert und muss nicht separat getestet werden)

## Installation
1. Repository klonen:
   ```bash
   git clone <REPOSITORY-URL>
   cd Karina_Chat_Testmodul
   ```
2. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

## Starten der Anwendung
1. Sicherstellen, dass die virtuelle Umgebung aktiv ist.
2. Streamlit-Anwendung starten:
   ```bash
   streamlit run Karina_Chat_2.py
   ```
3. Die Oberfläche ist anschließend über den lokal ausgegebenen Link erreichbar.

<!-- Hinweis: Bei Deployment auf einem Server können hier spezifische Schritte ergänzt werden. -->

## Grundlegende Nutzung
- **Modulauswahl:** Über das Seitenmenü lassen sich die verschiedenen Module aufrufen (z. B. Sprach-, Befund- oder Feedbackmodul).
- **Startseite als Einstieg:** `Karina_Chat_2.py` dient ausschließlich der Fallvorbereitung und führt nach Bestätigung der Instruktionen automatisch zur ersten Seite der Multipage-App.
- **Klinik-Logo beim Start:** Solange noch kein patientenspezifisches Foto vorliegt, zeigt die Sidebar zu Beginn immer `pics/Logo_Klinik.png` in vergrößerter Darstellung an, damit das Branding deutlich sichtbar ist. Die Logo-Anzeige bleibt bestehen, bis im alters- und geschlechtsspezifischen Ordner passende Bilder gefunden werden; ein zufälliges Backup-Bild kommt nicht zum Einsatz.
- **Interaktion:** Dialoge werden Schritt für Schritt geführt. Eingaben können über Textfelder oder vordefinierte Auswahlmöglichkeiten erfolgen.
- **Speicherung:** Relevante Eingaben werden intern abgelegt, sodass ein Wechsel zwischen Modulen ohne Datenverlust möglich ist.
- **Körperliche Untersuchung:** Der automatisch generierte Befund führt immer mit den Vitalparametern Blutdruck (mmHg) und Herzfrequenz (/Minute) ein, damit Lernende sofort einen vollständigen Überblick erhalten.
- **Zusätzliche Untersuchungen:** Nach dem Erstbefund kann im Abschnitt „➕ Gesonderte Untersuchungen anfordern“ eine frei formulierte Wunschuntersuchung eingetragen werden. Die KI ergänzt den Befundblock und markiert ihn für spätere Auswertungen in Supabase. Die Anforderung landet dabei im Supabase-Feld **Diagnostik** unter dem Stichwort „erweiterte Untersuchung“, während das Ergebnis unverändert in der vom Untersuchungsmodul gelieferten Kurzfassung im Feld **Befunde** gespeichert wird. Der neu generierte Text beschränkt sich strikt auf den zusätzlichen Befund und wiederholt keine früheren Untersuchungsergebnisse.

### Neustart nach der Evaluation
- **Button „🔄 Neues Szenario starten“:** Nach Abschluss der Evaluation erscheint am unteren Seitenrand ein klar erkennbarer Button. Ein Klick darauf leert alle fallbezogenen Angaben (z. B. Chatverlauf, Befunde, diagnostische Entscheidungen) und setzt die Startinstruktionen zurück.
- **Automatisch frisches Szenario:** Beim Klick merken wir uns das gerade abgeschlossene Szenario. Bei der nächsten Auswahl wird es übersprungen, bis alle Fälle einmal gespielt wurden. Erst wenn die Liste erschöpft ist, wird sie automatisch geleert, sodass der Zufallszug wieder aus dem kompletten Pool erfolgen kann.
- **Sauberer Neustart:** Direkt im Anschluss leitet die Anwendung automatisch mit `st.switch_page("Karina_Chat_2.py")` zur Startseite. Dort läuft die Fallvorbereitung erneut durch, damit keine Datenreste aus der vorherigen Sitzung sichtbar bleiben.
- **Debugging-Hinweis:** Sollte der Reset ausnahmsweise nicht greifen, kann auf der Evaluationsseite kurzfristig `st.write(st.session_state)` aktiviert werden. So lassen sich verbleibende Schlüssel identifizieren und gezielt entfernen.

### Automatisches Zurücksetzen bei Direktaufrufen
- **Direkte Aufrufe werden abgefangen:** Wenn Nutzerinnen oder Nutzer versuchen, eine Unterseite ohne vorbereiteten Fall direkt
  über die URL zu öffnen, leitet die Anwendung automatisch zur Startseite zurück.
- **Hinweis auf der Startseite:** Die ausgelöste Unterseite hinterlegt einen Hinweistext im `st.session_state`. Beim nächsten
  Laden zeigt die Startseite diesen Warnhinweis einmalig an und entfernt ihn anschließend wieder, damit keine veralteten Meldungen
  sichtbar bleiben.
- **Debugging-Tipp:** Für Fehlersuchen kann der Session-State über `st.write(st.session_state)` ausgegeben werden. Die Stelle ist
  im Startskript kommentiert, sodass die zusätzliche Ausgabe bei Bedarf schnell aktiviert werden kann.

## Admin-Modus
Der Admin-Modus ermöglicht es befugten Personen, Inhalte und Konfigurationen des Systems anzupassen. Im Folgenden werden die wichtigsten Funktionen erläutert.

### Anmeldung
- **Zugang:** Der Admin-Modus wird über den entsprechenden Menüpunkt oder eine Tastenkombination aktiviert. Standardmäßig ist ein Passwortschutz vorgesehen.
- **Berechtigungen:** Nach erfolgreicher Anmeldung stehen administrative Werkzeuge zur Verfügung, die nur Lesenden mit Administratorrechten zugänglich sind.

### Verwaltung von Fallbeispielen
- **Zentrales Datenmodell:** Sämtliche Szenarien liegen in der Supabase-Tabelle `fallbeispiele`. Der Adminbereich lädt die Inhalte direkt aus dieser Quelle und verzichtet vollständig auf die bisherige Excel-Datei.
- **SQL-Beispiel:** Die folgende Definition kann in der Supabase-SQL-Konsole ausgeführt werden und legt die Tabelle inklusive Trigger für automatische Zeitstempel an:

```sql
create table if not exists public.fallbeispiele (
    id bigint generated by default as identity primary key,
    szenario text not null unique,
    beschreibung text not null,
    koerperliche_untersuchung text not null,
    besonderheit text,
    alter integer,
    geschlecht text check (geschlecht in ('m', 'w', 'n')),
    amboss_input text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create trigger set_fallbeispiele_updated_at
    before update on public.fallbeispiele
    for each row
    execute function public.set_updated_at();
```

- **Hinweis zur Trigger-Funktion:** Supabase liefert mit jeder neuen Datenbank die Funktion `public.set_updated_at()`. Falls sie entfernt wurde, kann sie wie folgt wiederhergestellt werden:

```sql
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$ language plpgsql;
```
- **Bearbeitung:** Neue Fälle werden im Admin-Formular erfasst und landen unmittelbar in Supabase. Über denselben Weg lassen sich bestehende Szenarien aktualisieren oder löschen (z. B. via Supabase-Konsole).
- **Formularhinweise:** Im Abschnitt „Neues Fallbeispiel“ sind die Felder **Szenario/Name**, **Beschreibung**, **Geschlecht** und **Alter** als obligatorisch gekennzeichnet. Für das Feld **Geschlecht** erklärt ein Tooltip die Kodierung (`m`, `w`, `d`, `n`).
- **Optionale Angaben:** Alle übrigen Felder sind freiwillig. Bleiben sie leer, werden sie automatisch so vorbereitet, dass Supabase-Constraints (z. B. NOT NULL bei der körperlichen Untersuchung) eingehalten werden.
- **AMBOSS-Input verwalten:** Die Spalte `amboss_input` speichert je Szenario die komprimierte AMBOSS-Zusammenfassung. Der Adminbereich erlaubt, zwischen dauerhaftem MCP-Abruf, Abruf nur bei leeren Feldern oder einem zufälligen Refresh (mit einstellbarer Wahrscheinlichkeit) zu wechseln.
- **Statuskontrolle:** Während der Fallvorbereitung zeigt der Spinner explizit an, dass der AMBOSS-Text geprüft und bei Bedarf gespeichert wird. Im Adminbereich erscheint anschließend eine Statusmeldung, ob das Supabase-Feld aktualisiert wurde oder aus welchen Gründen der Schritt übersprungen wurde (z. B. Zufallsmodus, Override, Fehler).
- **Persistente Admin-Einstellungen:** Fixierungen für Szenario, Verhalten sowie der bevorzugte AMBOSS-Abrufmodus werden dauerhaft in der Supabase-Tabelle `fall_persistenzen` gespeichert. Der Adminbereich stellt die jeweils aktiven Werte in einem ausklappbaren Abschnitt dar.

### Patient*innenverhalten (Prompt & Begrüßung)
- **Zentrale Tabelle:** Verhaltensbeschreibung und Begrüßungssatz werden gemeinsam in der Supabase-Tabelle `patientenverhalten` gepflegt. Jede Zeile repräsentiert genau ein Verhalten.
- **SQL-Vorlage:** Die folgende Definition erzeugt die Tabelle und ergänzt automatisch gepflegte Zeitstempel. Vorher sollte – falls noch nicht geschehen – die Erweiterung `pgcrypto` aktiviert werden (`create extension if not exists pgcrypto;`).

```sql
create table if not exists public.patientenverhalten (
    id uuid primary key default gen_random_uuid(),
    verhalten_titel text not null unique,
    verhalten_prompt text not null,
    verhalten_begrussung text not null,
    kommentar text,
    is_active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create trigger set_patientenverhalten_updated_at
    before update on public.patientenverhalten
    for each row
    execute function public.set_updated_at();
```

- **Pflicht-Einträge:** Für den Regelbetrieb müssen die Verhaltensvarianten `ängstlich`, `redselig` und `verharmlosend` (weitere Optionen können ergänzt werden) jeweils mit einem Prompt (`verhalten_prompt`) und einem Begrüßungssatz (`verhalten_begrussung`) hinterlegt werden. Die Spalte `verhalten_titel` dient zugleich als Schlüssel und wird automatisch in Kleinbuchstaben umgewandelt.
- **Pflege:** Änderungen an Texten erfolgen direkt in Supabase. Nach Anpassungen lässt sich der Cache bei Bedarf per `module.supabase_content.clear_cached_content()` leeren (z. B. in einer Streamlit-Konsole), damit neue Werte sofort übernommen werden.
- **Fehlersuche:** Wenn die Anwendung meldet, dass kein Verhalten geladen werden konnte, prüfe bitte zuerst, ob `is_active = true` gesetzt ist und ob sowohl Prompt als auch Begrüßung gefüllt wurden. Über kommentierte `st.write`-Ausgaben in `module/supabase_content.py` lassen sich die Rohdaten analysieren.

### Feedback- und Befundmodule
- **Konfiguration:** Administratorinnen und Administratoren können Feedbackregeln anpassen und neue Befundvorlagen hinzufügen.
- **Überwachung:** Es gibt Einsicht in Bewertungsverläufe, sodass Ausbildungsfortschritte nachvollzogen werden können.
- **Anpassung:** Schwellenwerte für automatische Bewertungen lassen sich konfigurieren, um unterschiedliche Ausbildungsniveaus zu berücksichtigen.
- **Frühe Modusbestimmung:** Der aktive Feedback-Modus wird bereits beim Start festgelegt, damit der Adminbereich sofort den tatsächlichen Status ausweist.
- **Variabilitätsanalyse:** Im Adminbereich können gespeicherte Feedback-Fälle aus der Supabase-Tabelle `feedback_gpt` per ID geladen und mehrfach neu berechnet werden. Die Einstellungen erlauben, eine frei wählbare Anzahl von Durchläufen im ChatGPT- oder im kombinierten ChatGPT+AMBOSS-Modus zu starten. Alle benötigten Variablen werden automatisch aus dem Datensatz übernommen; fehlende Felder werden als Hinweis ausgegeben und neutral an den Prompt weitergereicht. Die Ergebnisse landen in einer eigenen Supabase-Tabelle (siehe unten) und bleiben dort vollständig erhalten; ein PDF-Export wurde bewusst entfernt, damit nur die Datenbank als Quelle für Auswertungen dient.
    - **Hinweis bei fehlenden Feldern:** Die Admin-Seite kennzeichnet leere Pflichtfelder (`szenario`, `chatverlauf`, `diagnostik`, `befunde`, `verdachtsdiagnosen`, `finale_diagnose`, `therapie`) sowie fehlende optionale Kontextangaben (`geschlecht`, `alter`, `diagnostik_runden_gesamt`, `koerper_befund`, `therapie_setting_verdacht`, `therapie_setting_final`). Alle fehlenden Werte werden gespeichert, sodass spätere Auswertungen die Datengrundlage nachvollziehen können.
    - **Keine stillen Fallbacks:** Wird im gespeicherten Chatverlauf kein klarer Nutzer:innen-Beitrag erkannt (z. B. fehlendes Präfix „Du:“), übernimmt der Admin-Reload den Verlauf bewusst NICHT. Stattdessen erscheint ein Warnhinweis, und der Rohverlauf kann bei Bedarf über kommentierte `st.write`-Ausgaben analysiert werden, um die Präfixliste anzupassen.
    - **Keine PDF-Ausgabe:** Die erneuten Feedback-Durchläufe werden ausschließlich in Supabase protokolliert. Dadurch entfallen Fehlerquellen rund um den PDF-Export (Fonts, Rückgabetypen, Zeilenumbrüche). Wenn Analyse-Teams eine Datei benötigen, können sie die Daten aus der Tabelle `feedback_gpt_variationen` exportieren und bei Bedarf eigenständig formatieren.
    - **Schema-Warnungen:** Wenn neue optionale Spalten wie `diagnostik_runden_gesamt` oder `koerper_befund` in Supabase noch fehlen, wird im Admin-UI eine Warnung eingeblendet. Die Speicherung läuft weiter, sobald die in diesem README dokumentierten SQL-Befehle ausgeführt wurden.

#### Supabase-Tabelle `feedback_gpt` um fehlende Felder ergänzen
Damit die oben genannten optionalen Kontextfelder dauerhaft mitgespeichert werden, sollten bestehende Installationen die Tabelle `feedback_gpt` in Supabase um zusätzliche Spalten erweitern. Der folgende SQL-Block kann unverändert in der Supabase-SQL-Konsole ausgeführt werden. Er fügt die Spalten hinzu (falls noch nicht vorhanden), setzt einen sinnvollen Default-Wert für die Anzahl der Diagnostikrunden und dokumentiert die Felder über Spaltenkommentare.

```sql
alter table if exists public.feedback_gpt
    add column if not exists geschlecht text,
    add column if not exists diagnostik_runden_gesamt integer default 1,
    add column if not exists koerper_befund text,
    add column if not exists therapie_setting_verdacht text,
    add column if not exists therapie_setting_final text,
    add column if not exists gpt_aktionsdauer_gesamt_sek double precision;

comment on column public.feedback_gpt.geschlecht is 'Kurzform m/w/d/n, wird aus patient_gender übernommen';
comment on column public.feedback_gpt.diagnostik_runden_gesamt is 'Gesamtzahl der eingegebenen Diagnostikrunden (mindestens 1)';
comment on column public.feedback_gpt.koerper_befund is 'Zusammenfassung der körperlichen Untersuchung';
comment on column public.feedback_gpt.therapie_setting_verdacht is 'Versorgungssetting nach Verdachtsdiagnose (ambulant vs. Einweisung)';
comment on column public.feedback_gpt.therapie_setting_final is 'Finales Therapiesetting inkl. Facharztoption';
comment on column public.feedback_gpt.gpt_aktionsdauer_gesamt_sek is 'Kumulierte GPT-Laufzeit der Sitzung in Sekunden';

update public.feedback_gpt
    set diagnostik_runden_gesamt = coalesce(diagnostik_runden_gesamt, 1)
    where diagnostik_runden_gesamt is null;
```

#### SQL nur für die zwei neuen Versorgungssettings
Falls ausschließlich die zwei neuen Spalten ergänzt werden sollen, kann der folgende, schlanke SQL-Block genutzt werden. Er entspricht genau den neuen Variablen und enthält die passenden Spaltenkommentare.

```sql
alter table if exists public.feedback_gpt
    add column if not exists therapie_setting_verdacht text,
    add column if not exists therapie_setting_final text;

comment on column public.feedback_gpt.therapie_setting_verdacht is 'Versorgungssetting nach Verdachtsdiagnose (ambulant vs. Einweisung)';
comment on column public.feedback_gpt.therapie_setting_final is 'Finales Therapiesetting inkl. Facharztoption';
```

*Hinweis:* Falls bestehende Datensätze für `geschlecht` oder `koerper_befund` nachgetragen werden sollen, können diese Felder in Supabase manuell befüllt werden. Die Anwendung verwendet die Werte automatisch beim nächsten Laden der Fälle im Admin-Modus.

#### Supabase-Tabelle für GPT-Feedback-Durchläufe
Die Admin-Funktion schreibt jede Serie von Feedback-Neuberechnungen in die Tabelle `feedback_gpt_variationen`. Das folgende SQL legt die benötigte Struktur an und kann direkt in der Supabase-SQL-Konsole ausgeführt werden:

```sql
create extension if not exists pgcrypto;

create table if not exists public.feedback_gpt_variationen (
    id bigint generated by default as identity primary key,
    laufgruppe uuid not null,
    feedback_id bigint not null references public.feedback_gpt("ID") on delete cascade,
    szenario text,
    fall_datum date,
    modus text not null check (modus in ('ChatGPT', 'Amboss_ChatGPT')),
    lauf_index integer not null,
    feedback_text text not null,
    fehlende_variablen text,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists feedback_variationen_gruppe_idx
    on public.feedback_gpt_variationen (laufgruppe);
```

Jeder Lauf erhält eine gemeinsame `laufgruppe`-Nummer (UUID), sodass sich mehrere Feedbacks derselben Serie leicht bündeln lassen. Die Spalte `fehlende_variablen` dokumentiert, welche Felder im Ursprungsdatensatz leer waren, damit spätere Auswertungen die Datenlage nachvollziehen können.

#### Supabase SQL (Option A) für Aufklapp-Tracking + Text-Cache
Für die On-Demand-Aufklapptexte der Feedback-Unterpunkte werden zwei zusätzliche Tabellen verwendet:
1. `feedback_detail_events` protokolliert je Feedback und Unterpunkt, ob geöffnet wurde (inkl. Textinhalt).
2. `feedback_detail_cache` speichert wiederverwendbare Lehrbuchtexte (Ablauf nach 3 Monaten in der App-Logik).

Den folgenden Block im Supabase-**SQL Editor** ausführen:

```sql
create table if not exists public.feedback_detail_events (
    id bigint generated by default as identity primary key,
    feedback_id bigint not null references public.feedback_gpt("ID") on delete cascade,
    section_key text not null,
    section_title text,
    opened boolean not null default false,
    generated_text text not null default 'Nein',
    model text,
    opened_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique (feedback_id, section_key)
);

create table if not exists public.feedback_detail_cache (
    cache_key text primary key,
    feedback_id bigint,
    fall_id text,
    feedback_modus text,
    section_key text not null,
    detail_text text not null,
    model text,
    updated_at timestamptz not null default timezone('utc', now()),
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists feedback_detail_events_feedback_idx
    on public.feedback_detail_events (feedback_id);

create index if not exists feedback_detail_events_section_idx
    on public.feedback_detail_events (section_key);

create index if not exists feedback_detail_cache_ctx_section_idx
    on public.feedback_detail_cache (feedback_id, fall_id, feedback_modus, section_key);
```

Debugging-Hinweis: Bei fehlenden Schreibrechten in Supabase zuerst API-Key und RLS-Policies prüfen. Bei Bedarf kann im Seitenmodul ein temporäres `st.write(exc)` aktiviert werden, um konkrete Fehlermeldungen aus dem Insert/Upsert sichtbar zu machen.

### Diagnostische Funktionen
- **Log-Ansicht:** Der Admin-Modus bietet Zugriff auf System-Logs, in denen Nutzerinteraktionen und Modulwechsel dokumentiert sind.
- **Diagnostikmodul:** Über das `diagnostikmodul.py` können gezielte Prüfungen von Patientengesprächen durchgeführt und Ergebnisse exportiert werden.
- **Fehlerprotokoll:** Administratoren können hier gezielt nach Auffälligkeiten suchen, um technische Probleme schneller zu identifizieren.

### Debugging-Hilfen
- **Deaktivierte Fallbacks:** Statt automatischer Fallbacks stehen kommentierte Debugging-Hilfen bereit. Diese können im Code aktiviert werden, um detaillierte Ausgaben zu erhalten.
- **Versorgungssettings prüfen:** Die Auswahl für Verdacht und finale Therapie wird direkt im Session-State gespeichert. Falls sie im Feedback oder Supabase fehlen, können die kommentierten `st.write(...)`-Hinweise in den Seitenmodulen und im `feedbackmodul.py` aktiviert werden, um die aktuellen Werte nachzuvollziehen.
- **Supabase-Persistenz prüfen:** Für detaillierte Analysen lässt sich die Tabelle `fall_persistenzen` direkt in Supabase öffnen. Zusätzlich zeigt der Adminbereich alle gespeicherten Werte in strukturierter Form an.
- **Praxis-Tipp:** Vor jeder Aktivierung von Debugging-Hilfen sollte eine Sicherung der Konfiguration vorgenommen werden.

## Fehlerbehebung
- **Fehlende Abhängigkeiten:** Prüfen, ob `pip install -r requirements.txt` ohne Fehlermeldung durchlief.
- **Port-Konflikte:** Falls der Standardport von Streamlit bereits belegt ist, kann ein alternativer Port angegeben werden (`streamlit run Karina_Chat_2.py --server.port 8502`).
- **Authentifizierungsprobleme:** Zugangsdaten im Admin-Modus prüfen und bei Bedarf zurücksetzen.
- **Datenbank- oder Dateizugriff:** Prüfen, ob die Supabase-Tabellen (`fallbeispiele`, `fall_persistenzen` usw.) erreichbar sind und ob der verwendete API-Key Schreibrechte besitzt. Optional lokal genutzte Dateien (z. B. CSV für Namenslisten) sollten ebenfalls vorhanden und beschreibbar sein.

<!-- Debugging-Hinweis: Für tiefergehende Analysen kann das Logging-Level im Code angehoben werden. Die entsprechenden Stellen sind im Admin-Modus dokumentiert. -->

## Weiterführende Ressourcen
- Interne Dokumentation (Confluence/SharePoint)
- Ansprechpartnerin/Ansprechpartner im Entwicklungsteam
- Schulungsvideos und Onboarding-Materialien

Wir wünschen viel Erfolg bei der Arbeit mit dem Karina-Chat!
