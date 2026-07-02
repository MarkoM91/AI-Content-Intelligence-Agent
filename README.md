# AI Content Intelligence Agent per Agenzie Digitali


Portfolio project Streamlit in italiano: un workflow controllato, non un semplice chatbot. Il modello è quello di Discover come feed di interessi: se un articolo ha performato, contenuti con gli stessi tratti editoriali possono ripetere il risultato. Il flusso: analizza i contenuti vincenti della finestra selezionata, estrae i pattern ricorrenti (titolo, sottotitolo, tema, angolo, formato, tono) confrontandoli con il resto del sito, cerca sul web coperture comparabili che confermino che l'interesse è vivo, e produce brief operativi per replicare il successo. Le azioni esterne restano in una coda di approvazione umana.

## Avvio

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Nessuna API a pagamento è necessaria: `Demo CSV`, `Piano locale` e `Regole locali` completano il percorso offline. Google News RSS e feed personalizzati sono gratuiti. OpenAI e Anthropic sono opzionali tramite `.env`; in caso di errore il sistema torna alle regole locali. Tavily e Brave sono evoluzioni future dichiarate.

## Demo

1. Caricare la demo in **01 Signals**.
2. In **02 What Worked** avviare il crawler (opzionale, migliora i titoli reali) ed estrarre i pattern ricorrenti: ogni pattern mostra prevalenza tra i vincitori, baseline sul resto del sito e lift.
3. In **03 Next Bets** cercare contenuti comparabili sul web (Piano locale o Google News RSS senza API): le fonti esterne vengono annotate con i pattern che condividono con i vincitori e alimentano una shortlist di idee con replication score trasparente.
4. In **04 Brief & Decide** trasformare un'idea in brief operativo (il titolo applica i pattern osservati) e gestire la coda approvazioni.
5. In **05 Results** registrare pubblicazione e feedback, poi esportare Markdown, CSV, ricerca e workflow JSON.

I dati restano in `st.session_state`: cambiare da Regole locali ad AI con LLM non azzera l'analisi.

Ogni import GSC riuscito viene inoltre archiviato in `data/content_intelligence.db`. Dalla scheda **Dati → Archivio dati locale** è possibile ripristinare uno snapshot senza interrogare nuovamente Google. Il token OAuth viene salvato nel percorso privato indicato da `token_path`, così l'autorizzazione viene riutilizzata. La cartella `data/`, i database e i token non vengono versionati.

L'import Discover usa per impostazione predefinita gli ultimi **90 giorni completi disponibili** e li confronta con i 90 giorni immediatamente precedenti. La durata è modificabile nell'interfaccia da 7 a 480 giorni.

Nota deployment: il filesystem di Streamlit Community Cloud è effimero. Per persistenza durevole in cloud, sostituire il backend SQLite con un database gestito (per esempio PostgreSQL/Supabase); SQLite è pensato per la demo locale.

### GSC su Streamlit Community Cloud

Il cloud non può leggere `gsc_config.yaml` o i file OAuth del computer locale. Copiare la struttura di `.streamlit/secrets.toml.example` in **Manage app → Settings → Secrets**, usando i valori del token OAuth locale autorizzato. L'app rileva automaticamente `[gsc]` e `[google_oauth]` e usa il refresh token senza avviare un browser OAuth sul server. Non inserire mai questi valori nel repository.

Per generare automaticamente il file locale pronto da copiare:

```powershell
python scripts/generate_streamlit_secrets.py
notepad .streamlit\secrets.toml
```

Il file reale è escluso da Git; soltanto il template senza credenziali viene versionato.

## Google Search Console

Copiare `gsc_config.example.yaml` in `gsc_config.yaml` e indicare proprietà e credenziali OAuth Desktop App. Per Discover viene inviato `type: discover`; per Search `type: web`, senza filtro `searchAppearance`. Non versionare le credenziali.

Lo scoring è trasparente e dimostrativo, non causale: combina volume, gap CTR e momentum normalizzato sulla durata delle finestre.

## Ricerca web e Hermes Agent

`AI (LLM) + Web scraper` è il percorso AI consigliato: oltre al web scraping, calcola il match con i temi Discover tramite **similarità semantica (embeddings OpenAI)** invece del semplice overlap di parole, e raffina le evidenze in 3 contenuti originali con OpenAI/Anthropic. Richiede una API key in `.env`; senza key valida (o senza quota) torna automaticamente alle euristiche e allo scoring locali.

`Web scraper + Google News` è il percorso senza API: parte dalle pagine Discover migliori, cerca fonti reali, deduplica i risultati (anche per URL canonicalizzata, ignorando parametri di tracking), estrae il testo delle pagine e genera suggerimenti editoriali motivati.

`Hermes Agent + Web scraper` passa le evidenze raccolte all'installazione locale ufficiale di Hermes tramite la modalità one-shot `hermes -z`. Hermes deve essere installato e autenticato separatamente; se non è disponibile, l'app mantiene il risultato del web scraper e mostra un fallback esplicito. Documentazione ufficiale: https://hermes-agent.nousresearch.com/docs/reference/cli-commands

## Esecuzione automatica multi-sito

Il runner `main.py` elabora più proprietà Discover senza interfaccia: legge gli ultimi 3 e 7 giorni, analizza e scansiona le pagine, cerca fonti recenti con Google News, Reddit e Serper opzionale, salva CSV e può aggiornare un Google Sheet condiviso.

1. Creare un service account Google e abilitare Search Console API, Google Sheets API e Google Drive API.
2. Aggiungere l'email del service account come utente di ogni proprietà Search Console e condividere con la stessa email il foglio Google di destinazione.
3. Copiare `multi_site.example.yaml` in `multi_site.yaml`, quindi configurare siti, percorso del JSON privato e ID del foglio.
4. Non inserire mai il JSON del service account o `multi_site.yaml` nel repository.

```powershell
python main.py --config multi_site.yaml --dry-run
python main.py --config multi_site.yaml
python main.py --config multi_site.yaml --site "Affaritaliani"
```

`--dry-run` evita la scrittura su Google Sheets ma produce comunque i CSV in `outputs/`. La chiave Serper può essere impostata nel file privato oppure nella variabile d'ambiente `SERPER_API_KEY`; senza chiave restano attivi Google News RSS e Reddit.

## Export pageview ed engagement

La modalità **Export engagement CSV (7 giorni)** accetta file con URL, pageview, tempo totale, tempo medio per view e un flag opzionale. L'app riconosce le intestazioni comuni oppure usa l'ordine delle prime cinque colonne.

L'analisi mantiene distinti tre segnali:

- traffico, per individuare i contenuti che generano volume;
- permanenza media, per trovare nicchie con lettori realmente coinvolti;
- engagement totale, per bilanciare scala e qualità.

Gli articoli vengono classificati come headliner, nicchie ad alta fedeltà, contenuti ad alto traffico ma retention debole o cadence filler. I filoni editoriali ricorrenti vengono aggregati e possono diventare direttamente i seed della ricerca competitor tramite **Top per engagement totale**, **Alta permanenza** o **Filoni ricorrenti**.
