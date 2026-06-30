# AI Content Intelligence Agent per Agenzie Digitali

Portfolio project Streamlit in italiano: un workflow controllato, non un semplice chatbot. Parte da GSC/Discover, identifica opportunità, arricchisce le pagine, cerca coperture competitor coerenti con temi già validati, produce brief e ferma le azioni esterne in una coda di approvazione.

## Avvio

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Nessuna API a pagamento è necessaria: `Demo CSV`, `Piano locale` e `Regole locali` completano il percorso offline. Google News RSS e feed personalizzati sono gratuiti. OpenAI e Anthropic sono opzionali tramite `.env`; in caso di errore il sistema torna alle regole locali. Tavily e Brave sono evoluzioni future dichiarate.

## Demo

1. Caricare la demo in **Dati**.
2. Consultare score e stati; opzionalmente avviare il crawler.
3. Avviare Piano locale o Google News RSS in **Competitor research**.
4. Generare un brief e gestire la coda approvazioni.
5. Esportare Markdown, CSV, ricerca e workflow JSON.

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
