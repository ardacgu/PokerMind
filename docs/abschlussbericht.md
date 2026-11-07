# PokerMind – Abschlussbericht Etappe 8

Die abschließende Etappe bereitet die professionelle Schulabgabe vor. Modell, Teacher, Trainingsdaten, Splits, Pokerregeln und wissenschaftliche Ergebnisse bleiben unverändert. Die README, Ergebnisübersicht, Reproduktionsanleitung, Lizenzhinweise und alle sechs CRISP-DM-Phasen sind auf Englisch dokumentiert. Dieser technische Abschlussbericht ist auf Deutsch; die Spieloberfläche bleibt ebenfalls deutsch.

## Vorbereitete Abgabe

- Eigenständiges Git-Repository ausschließlich für PokerMind; keine Änderung übergeordneter Repositories.
- Modell und Daten vollständig verfügbar, ohne kostenpflichtige Dienste oder notwendigen LFS-Speicher.
- Veröffentlichbare Prüfnachweise ohne persönliche Mac-Verzeichnisse; Originale lokal erhalten, Änderungen durch Hash-Ledger nachvollziehbar.
- Ein schlanker GitHub-Actions-Workflow mit Python- und JavaScript-Tests und Integritätsprüfung.
- [Englischer Abschlussbericht](final-report.md) mit wissenschaftlichen Grenzen und Reproduktionshinweisen.

## Abnahme und Veröffentlichung

Eine unabhängige Projektkopie mit neu angelegter virtueller Umgebung wurde vollständig installiert. Alle geprüften Bibliotheken wurden aus dieser neuen Umgebung geladen. **68 Python- und 7 JavaScript-Tests bestanden, null fehlgeschlagen.** Datenvalidierung, Abhängigkeitsprüfung, Dateiintegrität und erneute Bewertung der gespeicherten Modelle waren erfolgreich; die Kennzahlen stimmen exakt mit den Originalwerten überein.

Im echten Browser wurde eine vollständige Hand mit allen drei trainierten Gegnern gespielt. Ada erhielt 6.020 Chips; vorzeitige Offenlegung gegnerischer Karten trat nicht auf. Der bestätigte Neustart stellte viermal 2.000 Chips wieder her. Der Lauf meldete 6 Modellentscheidungen, null Fallbacks und null Fehler. Zusätzlich bestanden dieselben 75 Tests im Hauptprojekt und im ersten GitHub-Actions-Lauf auf Ubuntu. Die Testanzahl meint 75 unterschiedliche Tests; Wiederholungen sind keine zusätzlichen unabhängigen Testfälle.

## Öffentliches Repository und Release

Das Repository wurde unter dem tatsächlich authentifizierten Konto **ardacgu** erstellt und erfolgreich gepusht. Öffentliche Sichtbarkeit und ein anonymer Download aller 707 Dateien des ersten Abgabe-Commits wurden überprüft; alle Dateiinhalte stimmen bytegenau überein.

- [Öffentliches PokerMind-Repository](https://github.com/ardacgu/PokerMind)
- [Release v1.0.0 mit portabler ZIP und SHA-256](https://github.com/ardacgu/PokerMind/releases/tag/v1.0.0)
- [Erfolgreicher erster Actions-Lauf](https://github.com/ardacgu/PokerMind/actions/runs/42422707979)
- [Aktueller Workflow-Status](https://github.com/ardacgu/PokerMind/actions/workflows/tests.yml)

Der endgültige Release-Commit wird vor Tag und Veröffentlichung nochmals durch Actions geprüft. Der Release enthält `PokerMind-v1.0.0.zip` und die zugehörige Prüfsumme; die ZIP wird auf CRC, eindeutige Pfade und sämtliche Dateiinhalte geprüft. Der tatsächliche abschließende Tag-/Asset-Status wird bei Veröffentlichung separat bestätigt. Frühere Wissenschafts- und Etappennachweise bleiben erhalten.

## Weiterhin geltende Einschränkungen

Keine optimale Pokerstrategie nachgewiesen. 78,70 % Accuracy beschreibt Teacher-Nachahmung. Das seltene eigenständige All-in-Label hat nur vier Testbeispiele. Die Spielstärke-Evaluation gilt für die dokumentierten Gegner, Seeds und Turniergrenzen. Das Spiel verwaltet einen lokalen Tisch ohne Speicherung über einen Serverneustart hinaus. Eine Entscheidung des Eigentümers über die Projektlizenz bleibt offen; es wurde keine Lizenz erfunden.
