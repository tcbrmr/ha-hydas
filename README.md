<p align="center">
  <img src="https://raw.githubusercontent.com/tcbrmr/ha-hydas/main/custom_components/hydas/brand/icon.png" alt="HyDAS API" width="160">
</p>

<h1 align="center">HyDAS API für Home Assistant</h1>

<p align="center">
  Hydrologische Messdaten aus standardisierten HydroDaten-APIs direkt in
  Home Assistant nutzen.
</p>

<p align="center">
  <a href="https://github.com/tcbrmr/ha-hydas/releases/latest"><img src="https://img.shields.io/github/v/release/tcbrmr/ha-hydas?display_name=tag&sort=semver&cacheSeconds=300&v=0.1.5" alt="GitHub Release"></a>
  <a href="https://github.com/tcbrmr/ha-hydas/blob/main/LICENSE"><img src="https://img.shields.io/github/license/tcbrmr/ha-hydas" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/HACS-Custom-41BDF5" alt="HACS Custom Repository">
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.6%2B-41BDF5" alt="Home Assistant 2024.6 oder neuer">
</p>

**HyDAS API** ist eine inoffizielle Home-Assistant-Custom-Integration für
Schnittstellen nach dem deutschen
[HydroDaten API Standard (HyDAS)](https://dev.hochwasserzentralen.de/hydrodaten-api/).
Sie erkennt die angebotenen Messstationen und Messparameter automatisch und
stellt die jeweils aktuellen Werte als Home-Assistant-Sensoren bereit.

Damit lassen sich öffentliche hydrologische Daten in Dashboards,
Benachrichtigungen und Automationen einbinden – vom privaten Pegelmonitoring bis
zu **Smart-City**, **Open-Data**, **Hochwasservorsorge**, **Klimaanpassung** und
kommunalem **Umweltmonitoring**.

> [!IMPORTANT]
> Diese Integration ist kein amtliches Warnsystem. Messwerte können ungeprüft,
> verzögert oder zeitweise nicht verfügbar sein. Für sicherheitskritische
> Entscheidungen sind ausschließlich die offiziellen Veröffentlichungen und
> Warnkanäle der zuständigen Behörden maßgeblich.

## Was kann die Integration?

- beliebig viele HyDAS-API-Instanzen parallel anbinden
- Stationen nach Gewässer, Name, Bundesland oder Stationsnummer durchsuchen
- eine oder mehrere Stationen je API auswählen
- Messparameter und Einheiten automatisch erkennen
- pro Stationsparameter einen Home-Assistant-Sensor erzeugen
- neue Messparameter bei späteren Aktualisierungen dynamisch ergänzen
- Aktualisierungsintervall ab 60 Sekunden konfigurieren
- API-Verfügbarkeit über den optionalen `/health`-Endpunkt überwachen
- Stations- und Parameterstatus als Diagnoseinformationen bereitstellen
- typabhängige Gerätebezeichnungen und passende Messwertsymbole verwenden
- deutsche und englische Benutzeroberfläche anzeigen

Je nach Datenanbieter können unter anderem folgende Messgrößen verfügbar sein:

- relativer und absoluter Wasserstand
- Abfluss und Durchfluss
- Grundwasserstand und Grundwassertemperatur
- Wassertemperatur
- Lufttemperatur
- Windgeschwindigkeit

Die tatsächlich erzeugten Sensoren richten sich immer nach den Parametern, die
die ausgewählte Station über ihre API bereitstellt.

## Mögliche Anwendungsfälle

- Pegelstände und Abflüsse im Home-Assistant-Dashboard visualisieren
- Benachrichtigungen bei selbst definierten Wasserstandsgrenzen auslösen
- kommunale Smart-City-Dashboards um offene Umweltdaten ergänzen
- Grundwasser- und Wetterdaten gemeinsam mit lokalen IoT-Sensoren auswerten
- die technische Erreichbarkeit einer Daten-API überwachen
- Stationsstörungen oder Wartungszustände in Automationen berücksichtigen
- Daten verschiedener Länder- und Bundesanbieter in einer Oberfläche bündeln

## Installation über HACS

Dieses Projekt ist derzeit ein **benutzerdefiniertes HACS-Repository** und noch
nicht Bestandteil des offiziellen HACS-Standardkatalogs.

Über den folgenden Button kann das Repository direkt in HACS geöffnet und als
benutzerdefiniertes Repository hinzugefügt werden:

[![HyDAS API direkt in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tcbrmr&repository=ha-hydas)

*Oder manuell:*

1. [HACS installieren](https://www.hacs.xyz/docs/use/download/download/), falls
   es noch nicht eingerichtet ist.
2. HACS in Home Assistant öffnen und zu **Integrationen** wechseln.
3. Oben rechts das Drei-Punkte-Menü öffnen und
   **Benutzerdefinierte Repositories** auswählen.
4. Als Repository diese URL eintragen:

   ```text
   https://github.com/tcbrmr/ha-hydas
   ```

5. Als Kategorie **Integration** auswählen und das Repository hinzufügen.
6. Nach **HyDAS API** suchen und **Herunterladen** auswählen.
7. Home Assistant neu starten.
8. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   **HyDAS API** suchen.

Bei Aktualisierungen bleiben bestehende Konfigurationseinträge und Entity-IDs
erhalten. Neu hinzugekommene Sensorarten werden nach dem Neuladen der
Integration automatisch ergänzt.


## Manuelle Installation

1. Das Archiv des [neuesten Releases](https://github.com/tcbrmr/ha-hydas/releases/latest)
   herunterladen und entpacken.
2. Den enthaltenen Ordner `custom_components/hydas` in das
   Home-Assistant-Konfigurationsverzeichnis kopieren. Das Ergebnis muss so
   aussehen:

   ```text
   <config>/custom_components/hydas/manifest.json
   ```

3. Home Assistant neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   **HyDAS API** suchen und die Integration einrichten.

Für diese Integration muss keine Dashboard-Ressource und kein JavaScript-Modul
registriert werden. Bei einer manuellen Aktualisierung wird der vorhandene
Ordner `custom_components/hydas` durch den Ordner aus dem neuen Release ersetzt
und Home Assistant anschließend neu gestartet.

## Einrichtung

Beim Hinzufügen der Integration werden benötigt:

- die Basis-URL der HyDAS-API, ohne `/stations` am Ende
- das gewünschte Aktualisierungsintervall in Sekunden

Als öffentliches Beispiel kann PEGELONLINE verwendet werden:

```text
https://pegelonline.wsv.de/api/v1
```

Nach erfolgreicher Prüfung lädt die Integration `/stations`. Anschließend
können die Stationen in einer durchsuchbaren Mehrfachauswahl gefiltert und
ausgewählt werden. Weitere APIs lassen sich als zusätzliche Integrationseinträge
einrichten. Die Stationsauswahl kann später über **Konfigurieren** geändert
werden.

## Geräte- und Sensorbenennung

Die Gerätenamen richten sich nach dem Stationstyp des HyDAS-Standards:

- Oberflächenwasser: `Gewässer - Messstellenname`, etwa `EMS - LINGEN-DARME`
- Grundwasser: `Grundwasserkörper - Messstellenname`, sofern vorhanden
- Meteorologie: Messstellenname

API-Implementierungen wie PEGELONLINE liefern derzeit nicht zwingend ein
`type`-Feld. Ist stattdessen `waterBodyName` vorhanden, behandelt die
Integration die Station als Oberflächenwasser.

Die Sensorbezeichnung wird aus dem vom Anbieter gelieferten Parameternamen
gebildet. Beispiele:

```text
EMS - LINGEN-DARME Wasserstand
Rhein - Pegel Köln Wasserstand, relativ
Rhein - Pegel Köln Abfluss
```

## Diagnose

### API-Health

Unterstützt eine API `GET /health`, legt die Integration ein eigenes
API-Diagnosegerät mit folgenden Sensoren an:

- Status: `healthy`, `degraded` oder `unhealthy`
- Uptime in Sekunden
- Zeitpunkt des letzten Health-Checks

Die optionale Statusnachricht wird als Attribut des Statussensors geführt. Ein
fehlender Health-Endpunkt (HTTP 404) beeinträchtigt die normalen Messsensoren
nicht und erzeugt keine Health-Entitäten.

### Stationsstatus

Bietet eine Station einen `status`-Block an, werden folgende
Diagnose-Sensoren angelegt:

- **Stationsstatus** – standardmäßig aktiviert
- **Status seit** – standardmäßig deaktiviert
- **Voraussichtliches Statusende** – standardmäßig deaktiviert

`message` und `contact` werden als Attribute des Stationsstatus geführt. Der
Parameterstatus ist zusätzlich am jeweiligen Messsensor verfügbar.

## Unterstützte Schnittstelle

Für die Messwertintegration werden mindestens diese Endpunkte erwartet:

```text
GET /stations
GET /stations/{stationId}/parameters
GET /stations/{stationId}/parameters/{parameterId}/values
```

Die jeweiligen Nutzdaten müssen entsprechend der HyDAS-Basisstruktur im
JSON-Feld `data` bereitgestellt werden. Der optionale Endpunkt `GET /health`
entspricht der erweiterten Variante des Standards.

## Über den HydroDaten API Standard

Der HydroDaten API Standard ist eine deutschlandweit abgestimmte Spezifikation
für einheitliche REST-Schnittstellen zu hydrologischen Daten. Er entstand 2025
im Rahmen des unabhängigen Projekts **HydroDaten API** auf Initiative der
deutschen Bundesländer. An der Projektgruppe sind Vertretungen verschiedener
Länder- und Bundesbehörden sowie des Online-Dienstes PEGELONLINE beteiligt.

Der Standard soll den öffentlichen Zugang zu hydrologischen Daten vereinfachen
und eine interoperable Grundlage für Fachanwendungen sowie den Datenaustausch
zwischen Bund, Ländern und Dritten schaffen.

Weiterführende offizielle Informationen:

- [Projektseite des HydroDaten API Standards](https://dev.hochwasserzentralen.de/hydrodaten-api/)
- [Einführung und Ressourcenmodell](https://dev.hochwasserzentralen.de/hydrodaten-api/intro)
- [Interaktive Dokumentation](https://dev.hochwasserzentralen.de/hydrodaten-api/docs-extended-stable-elements)
- [Übersicht aktiver API-Implementierungen](https://dev.hochwasserzentralen.de/hydrodaten-api/reals)
- [PEGELONLINE](https://www.pegelonline.wsv.de/)

## Haftung und Projektstatus

Dieses Repository ist ein unabhängiges Community-Projekt. Es wird weder vom
Projekt HydroDaten API noch von den beteiligten Behörden oder PEGELONLINE
entwickelt, betrieben oder offiziell unterstützt.

Fehler und Funktionswünsche können über die
[GitHub Issues](https://github.com/tcbrmr/ha-hydas/issues) gemeldet werden.

## Entwicklung und Tests

Die vollständige Release-Prüfung benötigt Python 3.14. Lokal kann sie in einer
virtuellen Umgebung ausgeführt werden:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements_test.txt
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest
```

GitHub Actions führt diese Prüfungen sowie HACS Validation und `hassfest` bei
Pushes, Pull Requests und Release-Tags automatisch aus. Bei Tags prüft die
Testsuite zusätzlich, ob der Tag (zum Beispiel `v0.2.0`) mit der Version in
`manifest.json` übereinstimmt.

## Lizenz

Der Quellcode dieser Integration steht unter der [MIT-Lizenz](LICENSE). Für die
über angebundene APIs abgerufenen Daten gelten die Lizenz- und
Nutzungsbedingungen des jeweiligen Datenanbieters.
