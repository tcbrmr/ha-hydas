# HyDAS API für Home Assistant

Eine über HACS installierbare Custom Integration für APIs nach dem
[HydroDaten-API-Standard](https://m.wasserstaende.de/webservice/hydas).

## Funktionen

- Beliebig viele HyDAS-API-Instanzen als getrennte Integrations-Einträge
- Automatische Erkennung von Messstellen und Parametern
- Ein Sensor pro Messstellen-Parameter, inklusive Einheit und Messzeitpunkt
- Dynamisches Hinzufügen neu auftauchender Parameter
- Durchsuchbare Mehrfachauswahl der von der API angebotenen Stationen
- Konfigurierbares Polling (mindestens 60 Sekunden)
- Optionale Diagnose-Sensoren für APIs mit einem `/health`-Endpunkt

## Installation

Das mitgelieferte Integrationsicon wird ab Home Assistant 2026.3 direkt aus
`custom_components/hydas/brand` geladen. In älteren Versionen funktioniert die
Integration weiterhin, dort kann jedoch das generische Integrationssymbol
erscheinen.

### HACS

1. Dieses Repository in HACS als benutzerdefiniertes Repository vom Typ
   **Integration** hinzufügen.
2. **HyDAS API** installieren.
3. Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/hydas` nach
`<config>/custom_components/hydas` kopieren und Home Assistant neu starten.

## Einrichtung

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
**HyDAS API** suchen. Benötigt werden:

- die Basis-URL ohne abschließenden Endpoint, z. B.
  `https://pegelonline.wsv.de/api/v1`,
- das Aktualisierungsintervall in Sekunden.

Nach erfolgreicher Verbindungsprüfung zeigt Home Assistant eine durchsuchbare
Mehrfachauswahl an. Die Einträge beginnen mit dem Gewässer und enthalten danach
Stationsname, Bundesland und Stationsnummer, zum Beispiel
`EMS - RHEINE UNTERSCHLEUSE (DE-NW · 3390020)`. Die Liste ist nach Gewässer und Station
sortiert. Mindestens eine Station muss ausgewählt werden.

Die Gerätenamen richten sich nach dem Stationstyp des HydroDaten-Standards:

- Oberflächenwasser: `Gewässer - Messstellenname`, z. B. `EMS - LINGEN-DARME`
- Grundwasser: `Grundwasserkörper - Messstellenname`, sofern der optionale
  Grundwasserkörper vorhanden ist; andernfalls nur der Messstellenname
- Meteorologie: Messstellenname

Für API-Implementierungen wie PEGELONLINE, die das Feld `type` derzeit nicht
liefern, wird eine Station mit `waterBodyName` als Oberflächenwasser behandelt.

## Sensorsymbole

Die Integration ordnet standardisierten Messgrößen passende Symbole zu:

- Wasserstand: `mdi:waves`
- Grundwasserstand: `mdi:water-well`
- Abfluss und Durchfluss: `mdi:waves-arrow-right`
- Wasser- und Grundwassertemperatur: `mdi:thermometer-water`
- Lufttemperatur: `mdi:thermometer`
- Windgeschwindigkeit: `mdi:weather-windy`

Für PEGELONLINE werden außerdem die Kurzbezeichnungen `W` und `Q` erkannt.

## API-Diagnose

Wenn die angebundene API den standardisierten Endpunkt `GET /health` anbietet,
legt die Integration ein eigenes API-Gerät mit drei Diagnose-Sensoren an:

- Status (`healthy`, `degraded` oder `unhealthy`), inklusive `message`-Attribut
- Uptime in Sekunden
- Zeitpunkt des letzten Health-Checks

Fehlt der Endpunkt (HTTP 404), werden diese Sensoren nicht angelegt. Fehler am
optionalen Health-Endpunkt beeinträchtigen die normalen Messsensoren nicht.

## Stationsdiagnose

Wenn eine Station einen standardisierten `status`-Block anbietet, werden drei
Diagnose-Sensoren am Stationsgerät angelegt:

- **Stationsstatus** ist standardmäßig aktiviert. `message` und `contact`
  werden als Attribute geführt.
- **Status seit** ist ein standardmäßig deaktivierter Zeitstempelsensor.
- **Voraussichtliches Statusende** ist ebenfalls standardmäßig deaktiviert.

Die Zeitstempelsensoren lassen sich bei Bedarf in Home Assistant aktivieren.
Der Parameterstatus bleibt zusätzlich als Attribut am jeweiligen Messsensor
verfügbar, ohne weitere Statusentitäten pro Messreihe anzulegen.

Für weitere APIs den Vorgang einfach wiederholen. Die Stationsauswahl kann
später über **Konfigurieren** am jeweiligen Integrationseintrag geändert werden.

## Unterstützte Endpunkte

Die API muss diese standardisierten JSON-Endpunkte anbieten:

- `GET /stations`
- `GET /stations/{stationId}/parameters`
- `GET /stations/{stationId}/parameters/{parameterId}/values`

Die Nutzlast wird jeweils im Feld `data` erwartet.
