---
name: fable-context-maxxing
description: >
  Mandatory development workflow for any task that changes production code,
  fixes a bug, adds a feature, performs a refactor, or creates a commit.
  MUST be loaded before implementation begins. Maximizes the Fable
  subscription (lean orchestrator context, delegation to Opus subagents,
  index navigation, evidence ledger) and enforces Commit Contract, Red
  Proof, frozen acceptance tests, delegated implementation, independent
  verification, bounded repair loops, Commit Gate, and requirement-first
  audit via global hooks.
---

# fable-context-maxxing

## Teil 0: Die Tool-Calling-Entscheidung (Selbst-Triage)

Vor allem anderen wird entschieden, ob diese Aufgabe den Harness
überhaupt braucht. Die Entscheidung ist explizit, wird aufgezeichnet
und folgt dem gemessenen Break-even des eigenen Benchmarks, keiner
Gewohnheit. Die Rollen sind modell-agnostisch: "Orchestrator" ist das
starke Modell der Session, "Implementierer" eine günstigere Stufe, an
die delegiert wird. Gemessen wurden ein Frontier-Orchestrator, der an
einen starken Implementierer delegiert (Token-Verteilung), und
schwache Implementierer-Stufen unter Gates (Gate-Nutzen); andere
Paarungen, auch lokale Modelle als Implementierer, erben die Mechanik,
nicht die Zahlen.

Drei Stufen:

**solo** (kein Harness): direkt in der Session implementieren. Wenn
ALLE Kriterien gelten: eine Datei oder trivial lokalisierbar; der
erwartete Diff ist auf einen Blick reviewbar; das fehlerhafte
Verhalten spezifiziert den Fix vollständig; keine öffentliche
Schnittstelle, Persistenz, Security-, Audit- oder Idempotenzfläche.
Mechanik: trotzdem `RP exempt --reason "triage: solo - <warum>"`
ausführen, damit die Hooks ehrlich bleiben und die Entscheidung
protokolliert ist. Messbasis: beim kleinen Ein-Modul-Task (ein
Greenfield-Modul) kostete Delegation 7% MEHR auf dem teuren Modell und
119% mehr insgesamt bei gleichem Ergebnis; und im gepaarten Benchmark
verlor der inline-Arm auf der Klasse kleiner Tasks über 12 Paare keine
Hidden-Suite-Passes gegen den delegierten Arm, bei 0.45x seiner
Median-Gesamtkosten, alle 24 Läufe hidden-grün.

**light** (der Default für echte Arbeit): der volle Commit-Zyklus
dieses Skills (Contract, Red, Freeze, delegierte Implementierung,
Targeted- und Full-Suite, Diff-Review, Attest, Commit-Gate) OHNE
zusätzliche `--require`-Gates. Wenn eines gilt: die Änderung geht
über Module; die Anforderungen sind interpretationsbedürftig; die
Implementierung bedeutet viel Suchen, viele Tool-Calls oder lange
Testläufe. Messbasis: bei implementierungslastiger Arbeit sparte der
delegierte Zyklus 28% Tokens auf dem teuren Modell bei identischer
Erfolgsrate (16.576 zu 11.864), während der Gesamtverbrauch über
beide Modelle um 37% stieg; gekauft wird Reichweite auf dem teuren
Modell, nicht Gesamtsparsamkeit.

**full** (light plus deklarierte Gates): dazu `--require static` (und
`quality`, `coverage`, wo der Contract es rechtfertigt),
Checker-Agenten in frischen Kontexten und ein finaler Audit. Wenn
"Tests grün" als Evidenz nicht reicht: Security-, Persistenz-,
Audit-Trail-, Idempotenz- oder Mandantentrennungs-Fläche; oder wenn
die Implementierer-Stufe schwach ist (günstige oder lokale Modelle)
UND die Spezifikation beispielbasiert ist, sodass ein plausibler
Beinahe-Treffer die sichtbaren Tests bestehen würde. Messbasis: das
Stufe-1-Gate wandelte echte verdeckte Fehlschläge genau in diesem
Fenster um (schwacher Implementierer, beispielbasierte Spec); mit
einem Frontier-Implementierer maß es nichts (net 0), und mit der
Sonnet-Stufe ebenfalls keinen Rückhalt (net -1 über 12 Paare).

Mutation- und Property-Gates sind nie Default: im Benchmark fanden sie
denselben seltenen Blind-Spot-Defekt, den die günstigeren Gates
übersahen, verdienten ihre Kosten aber nicht (3.08x bei Stufe 2). Das
Quality-Ceilings-Gate existiert, ist aber ungemessen (seine Hypothese
ist unfinanziert registriert). Solche Gates werden bewusst nur auf
blockabschließenden Contracts kritischen Codes deklariert. (Alle
Zahlen aus dem Entwicklungs-Benchmark dieses Workflows.)

## Teil 1: Subscription-Maximierung (zuerst lesen)

Fable ist das teuerste und knappste Kontingent der Subscription. Dieses
Setup ist so gebaut, dass Fable-Tokens fast ausschließlich in
Entscheidungen fließen, nicht in Volumen:

1. **Implementierung wird delegiert.** Opus-Subagenten (`model: "opus"`)
   schreiben den Produktivcode in eigenen, frischen Kontexten. Lange
   Implementierungs-Transkripte, Suchläufe, Fehlversuche und Testausgaben
   verbrauchen Opus-Kontingent, nicht das Fable-Fenster. Fable sieht nur
   die kompakte strukturierte Rückgabe.
2. **Contract-Handoffs statt Verlaufs-Mitschleppen.** Die Übergabe an Opus
   ist ein kleiner, in sich vollständiger Commit-Contract. Die Codebase
   muss nicht pro Runde neu erklärt werden, und der Fable-Kontext muss
   keine Implementierungsdetails halten.
3. **Index-Navigation statt Datei-Dumps.** `codebase-memory-mcp`
   (`search_code`, `get_code_snippet`, `search_graph`, `trace_path`)
   liefert gezielte Snippets. Volle Dateien werden nur für die tatsächlich
   zu prüfenden Hunks gelesen.
4. **Evidence Ledger statt Rekonstruktion.** Nachweise pro Commit stehen
   in einem kompakten strukturierten Eintrag (300 bis 800 Tokens). Block-
   und Final-Audits navigieren über das Ledger, statt alte Chats oder
   Agent-Transkripte erneut einzulesen.
5. **Begrenzte Reparaturschleifen.** Maximal zwei Repairs pro Defect,
   danach Re-plan. Das verhindert die teuerste Token-Senke agentischer
   Entwicklung: endlose Fix-Schleifen mit wachsendem Kontext.
6. **Frischer Audit-Kontext.** Die Abschluss-Abnahme läuft in einem
   eigenen Agenten und verbraucht kein Hauptfenster. Sie ist gleichzeitig
   unabhängiger (kein Anchoring an "alles erfüllt"-Zusammenfassungen).
7. **Mechanische Gates statt Modell-Disziplin.** Freeze- und Commit-Gates
   werden von Hooks und einem CLI deterministisch geprüft. Fable muss den
   Prozesszustand nicht im Kontext halten oder wiederholen; er liegt in
   `~/.claude/red-proof/state/`.

Effekt: das Fable-Fenster enthält Plan, Contracts, Diffs und
Entscheidungen. Alles Volumen (Implementieren, Suchen, Testläufe, Audit)
läuft in delegierten oder frischen Kontexten.

## Teil 2: Der erzwungene Commit-Zyklus (red-proof)

### 0. Grundprinzip

Die Entwicklung folgt einem strikt getrennten Maker-Checker-Auditor-Modell:

- Orchestrator (das Hauptmodell der Session, aktuell Fable 5): Orchestrierung, Anforderungsableitung, Commit-Planung, Test-Spezifikation, Red-Proof, Review, Verifikation, Staging und Commit-Entscheidung.
- Opus (Implementierer): ausschließlich Implementierung und Reparatur des Produktivcodes.
- Audit-Agent: unabhängige Vollständigkeits-Abnahme in frischem Kontext.
- Checker-Agenten (Stufen-Gates): ein frischer Kontext pro Constraint-Check (static, coverage, spätere Stufen), siehe 6.6.
- Kontroll-Agent (optional pro Arbeitspaket): unabhängiger Reviewer mit frischem Kontext, der einen abgeschlossenen Zyklus vor dem Block-Audit gegen seinen Contract prüft; in der Praxis bei größeren Plänen im Einsatz.

Grundregeln:

1. Der Implementierer entscheidet niemals über die eigene Abnahme.
2. Der Implementierer darf die Abnahmekriterien nicht verändern.
3. Ein grüner Testlauf beweist Konformität mit Tests, nicht automatisch Korrektheit der Spezifikation.
4. Die finale Aussage lautet daher nicht "das Feature ist korrekt", sondern "das Feature entspricht nachweisbar den spezifizierten Anforderungen, soweit diese durch Audit und Verifikation abgedeckt sind".

### 1. Commit-Contract (Orchestrator)

Vor jeder Implementierung erstellt der Orchestrator einen kleinen verbindlichen Commit-Contract.

Requirement Provenance: Jedes Akzeptanzkriterium wird auf seinen Ursprung zurückgeführt:

`Originalanforderung -> Commit-Ziel -> Akzeptanzkriterium`

Damit darf kein Akzeptanzkriterium lediglich aus der bereits entstandenen Implementierung abgeleitet werden.

Contract-Inhalt:

- Ziel und erwartetes Verhalten
- konkrete Akzeptanzkriterien
- Nicht-Ziele
- relevante ursprüngliche Anforderungen
- erlaubte beziehungsweise erwartete Änderungsfläche
- relevante bestehende Invarianten
- erforderliche neue Tests
- unveränderliche Regression-Gates
- öffentliche beziehungsweise externe Schnittstellen
- relevante Security-, Persistenz-, Audit- oder Idempotenz-Invarianten

Der Commit muss so klein sein, dass er atomar, unabhängig prüfbar, verständlich und einzeln revertierbar bleibt.

Eine notwendige Scope-Erweiterung führt zurück zu Phase 1. Keine stillschweigende Scope-Erweiterung während der Implementierung.

### 2. Red Phase (Orchestrator)

Der Orchestrator schreibt die verbindlichen Akzeptanz- und Regressionstests. Es gibt zwei legitime Red-Arten.

**A. Behavior-Red** (für bereits existierende Schnittstellen): Der Test muss wegen des fachlich falschen oder fehlenden Verhaltens scheitern. Beispiele: erwarteter Status fehlt; falsche Validierung; falsches Audit-Ergebnis; Idempotenzverletzung.

**B. Contract-Red** (für bewusst neu einzuführende Module, Klassen, Funktionen oder Methoden): Hier darf der erwartete Fehler ausdrücklich beispielsweise `ImportError`, `ModuleNotFoundError` oder `AttributeError` sein, aber nur dann, wenn exakt das fehlende Symbol Bestandteil des eingefrorenen Commit-Contracts ist. Ein fehlendes neues API-Symbol ist in diesem Fall der erwartete Contract-Red und kein ungültiger Setup-Fehler. Der Orchestrator schreibt niemals Produktivcode oder Interface-Skelette.

**C. Scenario-Red** (für als Gherkin-Szenarien formulierte Akzeptanzkriterien): Der erwartete Fehler ist ein fehlschlagendes Szenario, entweder eine fehlende Step-Definition oder ein fehlschlagender Step, der exakt einem Akzeptanzkriterium des Contracts entspricht. Feature-Dateien sind Spezifikation, kein Produktivcode: Sie dürfen vor dem Freeze geschrieben werden und werden zusammen mit ihren Step-Skeletten eingefroren.

**Ungültiges Rot**: Nicht akzeptiert werden unbeabsichtigte Fehler wie Syntaxfehler im Test, falscher Importpfad, kaputte Testkonfiguration, fehlerhafte Testdaten, unbeabsichtigte Fixture-Probleme oder Fehler ohne Bezug zum Commit-Contract.

**Red-Proof**: Festgehalten werden Test-ID, Red-Art (`contract`, `behavior` oder `scenario`), erwarteter Fehlergrund, tatsächlicher Fehlergrund, Ergebnis (erwartetes Rot bestätigt / nicht bestätigt). Nur bei bestätigtem Red-Proof darf die Implementierung beginnen. Rote Tests werden nicht als dauerhaft roter Zwischenstand committet; der finale Commit muss grün und einzeln bisectable sein.

### 3. Mechanischer Freeze (Orchestrator)

**Git-Index-Eigentum**: Nur der Orchestrator darf `git add` ausführen, Staging verändern und Commits erstellen. Opus darf niemals stagen, den Index verändern oder committen.

Der Orchestrator staged vor der Delegation die verbindlichen Akzeptanztests. Vor dem Staging lässt er den Projekt-Linter über die Acceptance-Test-Dateien laufen, die er einfrieren wird; ein Befund wird vor dem Freeze behoben, nie danach per Amendment. Anschließend wird ein Freeze-Fingerprint über den eingefrorenen Test-Patch erzeugt (Testpfade, Testnamen, Hash des Acceptance-Test-Patches, Hash des Commit-Contracts).

**Freeze-Regel**: Während der Implementierung darf Opus eingefrorene Tests nicht verändern. Vor der Abnahme wird mechanisch geprüft: staged Test-Patch byte-identisch; keine Working-Tree-Änderungen an eingefrorenen Tests; keine Assertions entfernt oder verändert; kein `skip`/`xfail` hinzugefügt. Mismatch bedeutet automatische Ablehnung, keine Ermessensentscheidung.

**Zusätzliche Tests**: Opus darf zusätzliche Tests in nicht eingefrorenen Testbereichen ergänzen, sofern sie keine Akzeptanztests verändern, keine bestehenden Erwartungen abschwächen und im Commit-Scope bleiben.

### 4. Implementierung (Opus)

Delegation über das Agent-Tool mit `model: "opus"`. Bewusst keine Unterversion gepinnt: `opus` bedeutet die aktuell bereitgestellte Opus-Version.

Übergabe-Prompt enthält: Commit-Contract, Requirement Provenance, Akzeptanzkriterien, Red-Proof, relevante Testnamen, erwartete Änderungsfläche, harte Projekt-Leitplanken, explizite Nicht-Ziele, unveränderliche Invarianten.

Codebase-Navigation: zuerst `codebase-memory-mcp`, direktes Lesen nur für relevante Bereiche. Der Index ist Navigationsquelle, keine Verifikationsquelle.

Opus darf: Produktivcode implementieren, interne Helfer ergänzen, zusätzliche Tests innerhalb der Regeln ergänzen. Opus darf nicht: Akzeptanztests verändern; Assertions abschwächen; Tests entfernen, skippen oder xfailen; Scope erweitern; unrelated Refactorings; stagen; committen.

### 5. Implementierungs-Rückgabe (Opus)

Kompakte strukturierte Rückgabe: geänderte Dateien, erfüllte Akzeptanzkriterien, Designentscheidungen, ergänzte Tests, Risiken, Unsicherheiten. Die Rückgabe ist kein Beweis, nur Navigationsindex für das Review.

### 6. Verification Gate (Orchestrator)

**6.1 Freeze Gate** (zuerst, mechanisch): Contract- und Acceptance-Test-Fingerprint unverändert, keine Test-Abschwächung. Bei Fehler sofortige Ablehnung ohne weitere Review-Arbeit.

**6.2 Targeted Verification**: neue Akzeptanztests, unmittelbar betroffene Tests, relevante Regressionstests. Alle grün.

**6.3 Impact Review**: `detect_changes` bestimmt die Impact-Fläche, danach wird jeder tatsächlich geänderte Hunk direkt gelesen. Bei Änderungen an öffentlichen APIs, Core-Code, Persistenz, Audit, Security, Idempotenz, Tenant-Isolation oder Lifecycle-State zusätzlich Call-/Dependency-Pfade über den Code-Graph. `detect_changes` ersetzt niemals das Lesen der Hunks.

**6.4 Contract Review**: Für jedes Akzeptanzkriterium ein konkreter Nachweis: `Akzeptanzkriterium -> Code -> Test/Probe -> Ergebnis`. Nicht zulässig: "sieht korrekt aus", "Opus sagt, es sei umgesetzt", "Suite ist grün" ohne Bezug zum Kriterium.

**6.5 Scope Review**: Änderungen außerhalb des Contracts, unnötige Refactorings, unbeabsichtigte API-Änderungen, neue Persistenz, neue personenbezogene Kopien, Audit-/Security-/Idempotenz-Auswirkungen, Freeze-Invarianten.

**6.6 Constraint Gate (Stufe 1)**: Static Analysis, die Quality-Obergrenzen und Coverage laufen in jedem Commit-Zyklus, dessen Contract sie deklariert (`RP contract --require static,quality,coverage`). Ausgeführt werden sie von unabhängigen Checker-Agenten, niemals vom Orchestrator und niemals vom Implementierer.

**Checker-Agenten-Muster**: Ein Checker startet in frischem Kontext über das Agent-Tool. Er erhält: Repository-Pfad, das exakte Check-Kommando inklusive Schwelle, die für sein Gate relevanten Akzeptanzkriterien des Contracts und das erwartete Reportformat (PASS oder FAIL, Messwert, Top-Befunde als Datei:Zeile). Er erhält nicht: Implementierer-Transkripte, die Implementierer-Rückgabe, frühere Nachweise oder Einschätzungen des Orchestrators. Der Checker führt `RP check <name> ...` selbst aus; der Nachweis ist damit mechanisch an den Code-Fingerprint gebunden und kann nicht behauptet werden. Befunde gehen als Grundlage für Defect Contracts (Abschnitt 7) an den Orchestrator zurück; der Checker repariert nie.

Rollen, noch einmal: Die Maschine liest Unit-Tests und Implementierungsausgabe; der Mensch liest Spezifikationen und QA-Reports. Implementierer und Checker teilen in keiner Richtung Kontext.

### 7. Repair Loop

Bei fehlgeschlagenem Verification Gate implementiert der Orchestrator nicht selbst, sondern erstellt einen Defect Contract: beobachtetes Verhalten, erwartetes Verhalten, reproduzierender Test, betroffenes Akzeptanzkriterium, erlaubter Fix-Scope. Reparatur geht an Opus.

**Repair-Verifikation** (in dieser Reihenfolge): 1. Freeze Gate; 2. reproduzierender Defect-Test; 3. relevante Akzeptanztests; 4. unmittelbar betroffene Regressionstests; 5. Review aller durch die Reparatur geänderten Hunks.

Vollsuite pro Repair-Iteration nicht zwingend, aber sofort bei: Core-Code, öffentlichen Interfaces, Persistenz, Audit-Verhalten, Security-/Trust-Grenzen, Idempotenz/Lifecycle-State, unerwartet sichtbar gewordener Regression. Am Commit Gate ist die Vollsuite immer zwingend.

**Repair-Eskalation**: Maximal zwei Repair-Zyklen pro Defect Contract. Danach: Stop repairing. Re-plan. Zurück zu Phase 1 (Commit zu groß? Contract falsch? Architekturentscheidung fehlt? Aufteilen?). Keine unbegrenzten Reparaturschleifen.

### 8. Commit Gate (Orchestrator)

Pflicht: Freeze Gate grün; alle Akzeptanztests grün; betroffene Regressionstests grün; vollständige Suite grün; jeder im Contract per required_evidence deklarierte Nachweis-Key grün und frisch (hier leben die projektspezifischen Checks); vollständiger Diff reviewed; Contract vollständig erfüllt; kein Scope Creep; keine offenen Regressionen; keine unerklärten TODOs; Diff atomar und revertierbar.

Erst danach staged der Orchestrator den Produktivcode und committet. Jeder Commit der Hauptserie ist einzeln grün, verständlich, bisectable, revertierbar.

### 9. Evidence Ledger

Pro Commit ein kompakter strukturierter Eintrag: `commit_id`, `contract_hash`, `requirement_ids`, `frozen_test_hash`, `red_proof`, `changed_files`, `targeted_tests`, `regression_tests`, `full_suite`, `project_gates`, `review_status`, `known_risks`, `final_commit_hash`. Das Ledger ist Navigations- und Nachweisindex; es ersetzt nicht Code, Tests, Git-Historie oder eigene Ausführung durch den Audit-Agenten.

### 10. Block Gate

Nach jedem im Plan definierten Block: vollständige Suite; projektspezifische Reproduktions-Gates; Mutation-Hardening, wo das Projekt es deklariert (mutation-Nachweis am blockschließenden Contract, ausgeführt vom eigenen Checker-Agenten; der Nachweis nutzt Production-Staleness und überlebt reine Test- und Doku-Änderungen); Block-Invarianten; Plan-vs-Commit-Abgleich; Prüfung auf ausgelassenen Scope; Prüfung des Evidence Ledgers; erst danach Fast-Reindex (kein fehlerhafter Zwischenstand als Navigationsbasis).

### 11. Unabhängige Vollständigkeits-Abnahme

Frischer Audit-Kontext. Der Audit-Agent erhält: Gesamtplan, ursprüngliche Nutzerentscheidungen, Leitplanken, finales Repository, Commit-Serie, Tests, Evidence Ledger. Er erhält nicht: Implementierungsdiskussionen, Reparaturrechtfertigungen, Selbsteinschätzungen, "alles erfüllt"-Zusammenfassungen.

**Requirement-First**: Der Auditor interpretiert die Anforderungen selbst und erstellt `Anforderung -> Commit -> Implementierung -> Test/Probe -> eigener Nachweis`. Ergebnisse: erfüllt und nachgewiesen; teilweise erfüllt; nicht erfüllt; nicht nachweisbar.

**Eigenständige Verifikation**: Der Auditor führt relevante Prüfungen selbst aus (Akzeptanztests, Vollsuite, Projekt-Gates, End-to-End-Demos) und darf eigene adversariale Probes bauen. Findings gehen an den Orchestrator zurück.

**Schwerpunkte**: Anforderungen ohne Test; Tests ohne Anforderung; nominelle statt semantische Umsetzung; ungetestete Negativpfade; stille Scope-Lücken; unbeabsichtigte Verhaltensänderungen; Idempotenzfehler; Persistenz personenbezogener Daten; Audit-Trail-Lücken; Security-/Trust-Model-Verletzungen; Dokumentation vs. Verhalten. Ein grüner Testlauf ist kein Vollständigkeitsnachweis.

### 12. Audit-Finding Loop

Auditor beschreibt Finding und Nachweis; Orchestrator ordnet die betroffene Anforderung zu, erstellt neuen Commit-Contract, schreibt den roten Regressionstest; normaler Zyklus; danach erneute gezielte Audit-Prüfung. Der Auditor implementiert nicht selbst.

### 13. Finales Release Gate

Nach geschlossenem Audit, jeweils sofern im Projekt definiert: sauberer Repository-Zustand; vollständige Testsuite; Reproduktionsprüfung; Fresh-Clone-Prüfung; zentrale End-to-End-Demos; Headline-Benchmark unverändert; Stil-/Zeichen-Gates; Attribution-Check; Plan-vs-Code-Abgleich; Testzahl-Sync; kein offenes Audit Finding.

## Teil 3: Mechanische Durchsetzung (red-proof gate)

Globale PreToolUse-Hooks blockieren Produktivcode-Edits ohne aktiven Zyklus und `git commit` ohne bestandenes Commit Gate. Zustände und Nachweise erzeugt das CLI selbst und bindet sie an einen Content-Fingerprint (HEAD plus Inhalt aller geänderten Dateien). `git add` ändert den Fingerprint nicht (inhaltsbasiert); jede echte Codeänderung invalidiert vorhandene Nachweise automatisch.

```
RP() { python3 ~/.claude/red-proof/red_proof.py "$@"; }

RP contract --file <contract.md>            # Phase CONTRACT_CREATED, setzt Zyklus zurück
RP contract --file <c.md> --require static,coverage   # Stufen-Gates für diesen Zyklus deklarieren
RP red --test <name> --type contract|behavior|scenario --expected "<Grund>" -- <testcmd>
git add <acceptance-tests> && RP freeze     # Phase TESTS_FROZEN, Patch-Fingerprint
# Implementierung durch Opus
RP check freeze
RP check targeted -- <testcmd>
RP check full-suite -- <suitecmd>
RP check static -- <lintcmd>                # Exit-Code-Gate, ausgeführt vom Checker-Agenten
RP check quality -- <Ceilings-Kommando>     # Exit-Code-Gate: Komplexitäts- und Größenobergrenzen
RP check coverage --min 90 -- <covcmd>      # Metrik-Gate, Schwelle mechanisch erzwungen
RP check mutation --min 80 -- <mutcmd>      # Block-Gate-Stufe: überlebt reine Test-Edits
RP check property -- <cmd mit --hypothesis-seed=N>   # läuft nicht ohne fixierten Seed
RP attest --diff-reviewed --contract-ok     # einzige modell-attestierte Punkte
RP commit-gate                              # COMMIT_READY, an Fingerprint gebunden
git commit ...                              # nur jetzt erlaubt, genau ein Commit pro Gate
RP status                                   # Zustand und Fingerprints anzeigen
RP exempt --reason "<why>"                  # nur für klassifizierte Ausnahmen (4h, geloggt)
```

Hinweis für zsh: `$RP`-Variablen werden nicht wortgesplittet; die Funktion `RP()` wie oben verwenden. Deny-Meldungen der Hooks nennen jeweils den nächsten erforderlichen Schritt.

Ein fehlgeschlagener Check aktiviert einen Worktree-Snapshot-Guard: Derselbe Check mit demselben Kommando auf unverändertem Baum wird verweigert, der Versuch zählt trotzdem, und `contract --max-attempts` (Default 5, beratend) hängt ab Erreichen des Budgets die Aufforderung an, die Reparatur zu stoppen und neu zu planen. Ein korrigiertes Kommando läuft; der Zähler behält seine Historie.

Bekannte Grenze: Die Hooks gaten die Edit- und Write-Tools sowie `git commit`. Schreibzugriffe an diesen Tools vorbei (Bash-Heredocs, `sed -i`, Output-Redirection) werden nicht abgefangen; der Content-Fingerprint invalidiert zwar veraltete Nachweise, der Edit selbst wird aber nicht blockiert. Bash-Schreibzugriffe auf Produktivdateien gelten als außerhalb des Verfahrens.

## Teil 4: Verbindliche Meta-Regeln

- Tests vor Implementierung.
- Neues API darf mit erwartetem Contract-Red beginnen; bestehendes Verhalten verlangt Behavior-Red.
- Der Orchestrator schreibt keinen Produktivcode.
- Opus verändert keine eingefrorenen Akzeptanztests.
- Nur der Orchestrator staged und committet.
- Freeze und Commit Gate werden mechanisch geprüft (Hooks plus CLI).
- Implementierer und Abnehmer sind getrennt.
- Reparaturschleifen sind begrenzt (maximal zwei pro Defect Contract).
- Vollsuite zwingend vor jedem Haupt-Commit.
- `codebase-memory-mcp` ist Navigationshilfe, keine Beweisquelle.
- Tatsächlicher Diff, Tests und Laufzeitverhalten sind Verifikationsquellen.
- Kein Scope Creep ohne neuen Contract.
- Jeder Haupt-Commit ist grün und bisectable.
- Ein grüner Testlauf ist notwendig, aber nicht hinreichend.
- Der Audit-Agent interpretiert die ursprünglichen Anforderungen unabhängig und darf Tests und Demos selbst ausführen.
- Constraint-Checks laufen in unabhängigen Checker-Agenten mit frischem Kontext; der Implementierer sieht keine Checker-Begründungen, der Checker keine Implementierer-Transkripte.
- Ein Checker-Agent repariert nie; seine Befunde werden zu Defect Contracts.
- Das Verfahren beweist Konformität mit der überprüften Spezifikation, nicht absolute Korrektheit der Spezifikation.
