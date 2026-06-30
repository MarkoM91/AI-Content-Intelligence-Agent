# Post LinkedIn

Ho costruito **AI Content Intelligence Agent per Agenzie Digitali**.

Non parte da un prompt generico, ma dai segnali che il sito possiede già: URL e performance GSC/Discover.

GSC → scoring → crawler → ricerca competitor → brief AI → approvazione umana → report.

La ricerca è guidata dai topic performanti ed esclude il dominio proprietario. Il percorso funziona in locale; RSS e LLM sono moduli opzionali con fallback. L'AI non pubblica: propone, e le azioni esterne entrano in una coda controllata.
