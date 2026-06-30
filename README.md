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

## Google Search Console

Copiare `gsc_config.example.yaml` in `gsc_config.yaml` e indicare proprietà e credenziali OAuth Desktop App. Per Discover viene inviato `type: discover`; per Search `type: web`, senza filtro `searchAppearance`. Non versionare le credenziali.

Lo scoring è trasparente e dimostrativo, non causale: combina volume, gap CTR e momentum normalizzato sulla durata delle finestre.

## Ricerca web e Hermes Agent

`Web scraper + Google News` è il percorso predefinito: parte dalle pagine Discover migliori, cerca fonti reali, deduplica i risultati, estrae il testo delle pagine e genera suggerimenti editoriali motivati. Non richiede API key.

`Hermes Agent + Web scraper` passa le evidenze raccolte all'installazione locale ufficiale di Hermes tramite la modalità one-shot `hermes -z`. Hermes deve essere installato e autenticato separatamente; se non è disponibile, l'app mantiene il risultato del web scraper e mostra un fallback esplicito. Documentazione ufficiale: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
