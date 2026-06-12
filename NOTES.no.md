# FGI Subsidiary Management

## Hva applikasjonen gjør

**Review** er kjernen i verktøyet. Ett klikk, og KI-en leser alle tre
datakildene og lister opp hver governance-risiko den finner, hver rangert
etter risikonivå (High / Medium / Low), med en enkel forklaring og et
anbefalt tiltak. Der to kilder er uenige, vises begge side om side: "Ifølge
agentbrevet: 2026-06-19. Ifølge registeret vårt: 2028-01-10."

**Register** er selve datterselskapsregisteret, endelig søkbart: alle 100
enheter i en tabell du kan filtrere og sortere, fargekodet etter status.
Klikk på en enhet for å se hele oppføringen, hvem som eier den, hva den
eier, og eventuelle risikoer funnet på den.

**Ask** svarer på spørsmål i naturlig språk med kildehenvisninger, for
eksempel "Hvilke enheter i Singapore har åpne compliance-saker?" eller
"Hvilke styremandater utløper de neste 60 dagene?"

## Hvordan det fungerer

Tre trinn: rydd opp i de rotete dataene, gjør dem søkbare, og la så KI-en
resonnere over dem.

```
   1. PREPARE              2. STORE & INDEX            3. USE IT (the AI)
   ----------             ----------------            ------------------

   CSV  ─┐                SQLite  the register,       REVIEW  one click runs
   JSON  ├─►  ingest ─►           queried with SQL ─► 5 LLM passes and lists
   PDFs ─┘                BM25    keyword index       every issue + a fix
                          vector  meaning index   ─► ASK     ask in plain
                                                     English, get an answer
                                                     with its sources cited
                                                            │
                                                            ▼
                                                      React frontend
```

Review-veien og Ask-veien leser de samme lagrede dataene; Review går gjennom
alt i ett søk, mens Ask henter bare de tekstutdragene et spørsmål trenger.
Det hentetrinnet er hybrid RAG-pipelinen:

```
   How Ask finds the right text (hybrid RAG):

   your question ─┬─► BM25 search    (exact words: names, IDs, "S.à r.l.") ─┐
                  │                                                         ├─► merge ─► top passages ─► LLM answer
                  └─► vector search  (meaning: "compliance problems")      ─┘
```

De to søkene fanger opp forskjellige ting, så vi kjører begge og slår
sammen rangeringene (reciprocal rank fusion). De sammenslåtte tekstutdragene,
sammen med fakta fra SQL, sendes til LLM-en, som skriver svaret og oppgir
hvor hver del kommer fra.

**1. Klargjør dataene.** Ingest leser de tre kildene, henter ut tekst fra
PDF-ene, og normaliserer datoene (varslene blander dataformater, så vi
fester dem til en felles kalender). Resultatet er en ren, sporbar kopi av
alt.

**2. Lagre og indeksere (SQLite + hybrid RAG).** Registeret ligger i SQLite
som strukturerte fakta, spurt med vanlig SQL. Fritekstdokumentene (brev,
varselnotater) får også to søkeindekser: en nøkkelordindeks (BM25) for
eksakte treff som enhetsnavn og juridiske suffikser, og en vektorindeks for
betydningsbaserte treff som "compliance problems". Å søke i begge og slå
sammen resultatene er "hybrid RAG": det finner ting som ingen av indeksene
ville funnet alene, og det driver Ask-siden.

**3. Review (KI-pipelinen).** En forespørsel (`POST /api/digest`) kjører
analysen som en serie fokuserte LLM-pass:

1. **Entity resolution**: koble hvert rotete varselnavn til registeret.
   "Ingen match" er et gyldig svar; hvert varsel uten match blir et funn om
   ukjent enhet.
2. **Register-analyse** i tre pass: gjennomgang per enhet (mandater,
   innleveringer, status), struktur på tvers av enheter (dupliserte navn,
   styrekonsentrasjon), og varselhygiene (duplikater, motsigelser).
3. **Brevavstemming**: sjekk hvilke enheter hvert brev nevner som finnes i
   registeret, sammenlign så resten felt for felt for å fange opp uenigheter.
4. **Deduplisering**: slå sammen samme sak funnet av to pass til ett funn.
5. **Anbefalinger**: ett tiltak per funn, pluss sammendraget for ledelsen.

Resultatene vises i React-frontenden, stilsatt etter nbim.no sine
designtokens.

**Teknologistakk:** FastAPI + SQLite i backend, React i frontend, LLM-er
via Groq (gratis åpne modeller) med lokal Ollama som reserve og Anthropic
som et konfigurasjonsvalg.

## Kjøre det lokalt

Forutsetninger: Python 3.11+, Node 18+, og en gratis
[Groq API-nøkkel](https://console.groq.com).
Valgfritt: [Ollama](https://ollama.com) kjørende lokalt for ubegrenset
offline-reserve.

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env          # lim inn GROQ_API_KEY i .env
uvicorn app.main:app --port 8000
```

Databasen og søkeindeksene bygges automatisk fra `data/` ved første oppstart.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Åpne http://localhost:5173 og trykk **Run review**. Første kjøring tar omtrent
ett minutt; deretter er resultatene cachet og momentane.
