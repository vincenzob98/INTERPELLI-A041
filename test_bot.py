"""Test del riconoscimento degli avvisi, su titoli reali: python -m unittest test_bot"""
import datetime as dt
import unittest

from bot import Item, Post, enrich, extract_items, format_message, is_a041, is_duplicate, is_expired, mim_cards, remember


def post(title, html="", listing=False):
    return Post("AT Test", title, html, "https://esempio.it/avviso", "2026-11-04T10:00:00", listing)


class Riconoscimento(unittest.TestCase):
    def test_varianti_del_codice(self):
        for t in ("Interpello A041", "Interpello A-041", "cdc A41 fino al", "A18-A20-A21-A26-A41-A45-AS2A",
                  "Interpello SCIENZE E TECNOLOGIE INFORMATICHE", "INTERPELLO-A041_08h"):
            self.assertTrue(is_a041(t), t)

    def test_altre_classi_escluse(self):
        for t in ("Interpello A042 Scienze e tecnologie meccaniche", "Interpello A0410",
                  "B016 Laboratori di scienze e tecnologie informatiche", "Interpello AS2A", "laboratorio di informatica"):
            self.assertFalse(is_a041(t), t)

    def test_avviso_singolo(self):
        items = extract_items(post("Interpello c.d.c. A041 10h fino al 30/06/2027 presso I.I.S. Einaudi di Muravera."))
        self.assertEqual(len(items), 1)

    def test_esiti_e_ata_scartati(self):
        self.assertEqual(extract_items(post("Esito interpello A041 IIS Volta")), [])
        self.assertEqual(extract_items(post("Interpello DSGA IIS informatica")), [])

    def test_post_cumulativo_tiene_solo_a041(self):
        html = ('<p><a href="https://e.it/a041.pdf">Interpello A041</a> - ITET Bramante, Pesaro</p>'
                '<p><a href="https://e.it/b007.pdf">Interpello B007</a> - Lab. ottica</p>'
                '<p><a href="https://e.it/a042.pdf">Interpello A042</a> - Fano</p>')
        items = extract_items(post("PERSONALE DOCENTE - INTERPELLI NAZIONALI A.S. 2026/27", html))
        self.assertEqual([i.link for i in items], ["https://e.it/a041.pdf"])


class Pagine(unittest.TestCase):
    def test_scheda_del_ministero(self):
        page = """<article class="article"><span class="article_data"> 29 ottobre 2026 </span>
        <p class="article_tags"><a href="https://www.mim.gov.it/web/milano/interpelli-ricerca-supplenti?x=1">Interpelli</a></p>
        <h3><a href="https://www.mim.gov.it/web/milano/-/itsos-curie">ITSOS Marie Curie- CERNUSCO SUL NAVIGLIO</a></h3>
        <p>Posto Scienze e tecnologie informatiche A041 18 Ore dal 02/11/26 al 31/08/27</p></article>
        <article class="article"><span class="article_data"> 28 ottobre 2026 </span>
        <h3><a href="https://www.mim.gov.it/web/milano/-/altro">IC Manzoni</a></h3><p>Posto comune primaria</p></article>"""
        posts = mim_cards({"name": "AT Milano", "url": "https://www.mim.gov.it/web/milano/interpelli-ricerca-supplenti"}, page)
        self.assertEqual(posts[0].date, "2026-10-29")
        items = [i for p in posts for i in extract_items(p)]
        self.assertEqual([i.link for i in items], ["https://www.mim.gov.it/web/milano/-/itsos-curie"])
        enriched = enrich(items[0])
        self.assertEqual((enriched.regione, enriched.ore), ("Lombardia", "18"))
        self.assertEqual(enriched.fino_dt, dt.date(2027, 8, 31))

    def test_tabella_liguria_ignora_i_filtri(self):
        html = ('<form><select name="cdc"><option value="A041">A041</option></select><a href="?p=GE">Cancella filtri</a></form>'
                '<div class="results-row"><span>A042 IIS Volta</span><a href="interpello.php?id=1">Vai all’interpello ›</a></div>'
                '<div class="results-row"><span>A041 IIS Calvino Genova</span><a href="interpello.php?id=2">Vai all’interpello ›</a></div>')
        items = extract_items(post("AT Genova", html, listing=True))
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].link.endswith("id=2"))
        self.assertEqual(items[0].title, "A041 IIS Calvino Genova")


class Dati(unittest.TestCase):
    def enriched(self, title, extra=""):
        return enrich(Item(key="k", title=title, link="https://www.istruzionepiemonte.it/cuneo/x", source="AT Cuneo"), extra)

    def test_regione_della_scuola_non_di_chi_pubblica(self):
        item = self.enriched("Interpello c.d.c. A041 10h fino al 30/06/2027 presso I.I.S. Einaudi di Muravera.")
        self.assertEqual((item.regione, item.ore), ("Sardegna", "10"))
        self.assertEqual(item.fino_dt, dt.date(2027, 6, 30))

    def test_sigla_tra_parentesi(self):
        self.assertEqual(self.enriched("Interpello nazionale cdc A041 - Lagonegro (PZ)").regione, "Basilicata")

    def test_codice_meccanografico_vince(self):
        self.assertEqual(self.enriched("Interpello A041", "scuola RNTF010004 con sede").regione, "Emilia-Romagna")

    def test_nome_istituto_non_e_un_comune(self):
        self.assertNotEqual(self.enriched("Interpello A041 Liceo Da Vinci").comune, "Vinci")

    def test_regione_ignota_non_viene_inventata(self):
        item = self.enriched("Interpello A041 Istituto Superiore")
        self.assertEqual(item.regione, "")
        self.assertIn("Regione da verificare", format_message(item))

    def test_scadenza(self):
        item = enrich(Item(key="k", title="Interpello A041", link="https://e.it/x", source="AT", date="2026-10-10T09:00:00"),
                      "domande entro le ore 12 del 20/10/2026")
        self.assertEqual(item.scadenza_dt, dt.date(2026, 10, 20))
        self.assertTrue(is_expired(item, dt.date(2026, 11, 4)))
        self.assertFalse(is_expired(item, dt.date(2026, 10, 19)))

    def test_stesso_avviso_da_due_uffici(self):
        a = self.enriched("Interpello A041 18h fino al 07/12/2026 presso ISS Fermi di Empoli")
        b = enrich(Item(key="z", title="Interpello nazionale cdc A041 18 ore sino al 07/12/2026 Empoli (FI)",
                        link="https://usr.it/y", source="USR"))
        self.assertEqual(a.fp, b.fp)

    def test_formati_reali_di_scadenza(self):
        casi = [("entro e non oltre le ore 12.00 del giorno martedì 27/10/2026 con oggetto", dt.date(2026, 10, 27), "12:00"),
                ("entro le ore 11,00 del giorno 06/11/2026.", dt.date(2026, 11, 6), "11:00"),
                ("entro e non oltre le ore 08: 00 del 02/11/ 2026 la propria", dt.date(2026, 11, 2), "08:00"),
                ("ENTRO E NON OLTRE LE ORE 7.30 del 30/10/2026.", dt.date(2026, 10, 30), "07:30"),
                ("candidatura entro le ore 08.00 di giovedì 22 ottobre 202 6 mediante", dt.date(2026, 10, 22), "08:00"),
                ("Termine per l'invio delle candidature: entro le ore 13.00 del giorno 21/10/2026.", dt.date(2026, 10, 21), "13:00")]
        for testo, data, ora in casi:
            item = enrich(Item(key="k", title="Interpello A041", link="https://e.it/x", source="AT", date="2026-10-20T09:00:00"), testo)
            self.assertEqual((item.scadenza_dt, item.scadenza_ora), (data, ora), testo)

    def test_date_del_contratto_non_sono_la_scadenza(self):
        for testo in ("La presa di servizio dovrà avvenire entro il 10/11/2026", "rettifica della data di scadenza del contratto 30 giugno 2027",
                      "accettata entro 24 ore. Gli eventuali contratti al 31/08/2027"):
            item = enrich(Item(key="k", title="Interpello A041", link="https://e.it/x", source="AT", date="2026-10-20T09:00:00"), testo)
            self.assertIsNone(item.scadenza_dt, testo)

    def test_scadenza_mancante_viene_dichiarata(self):
        self.assertIn("Scadenza: non trovata", format_message(self.enriched("Interpello A041")))
        relativa = self.enriched("Interpello A041", "domande entro 24 ore dalla pubblicazione")
        self.assertIn("entro 24 ore dalla pubblicazione", format_message(relativa))

    def test_avviso_ripubblicato_dopo_la_scadenza_e_scaduto(self):
        item = enrich(Item(key="k", title="Interpello A041", link="https://e.it/x", source="AT", date="2026-11-04T09:00:00"),
                      "entro le ore 12:00 del giorno 02/11/2026")
        self.assertTrue(is_expired(item, dt.date(2026, 11, 4)))

    def test_citazione_normativa_non_scarta_l_avviso(self):
        item = enrich(Item(key="k", title="Interpello A041", link="https://e.it/x", source="AT", date="2026-11-04T10:00:00"),
                      "ai sensi della nota, domande entro il 31/08/2025")
        self.assertIsNone(item.scadenza_dt)
        self.assertFalse(is_expired(item, dt.date(2026, 11, 4)))

    def test_stessa_scuola_con_meno_dettagli_e_duplicato(self):
        now = dt.datetime(2026, 11, 4, 10)
        state = {"fps": {}, "places": {}}
        full = self.enriched("Interpello c.d.c. A041 10h fino al 30/06/2027 presso I.I.S. Einaudi di Muravera.")
        remember(full, state, now.isoformat())
        sparse = self.enriched("Interpello Nazionale A041 IIS Einaudi Muravera")
        self.assertTrue(is_duplicate(sparse, state, now))
        other = self.enriched("Interpello c.d.c. A041 18h fino al 30/04/2027 presso I.I.S. Einaudi di Muravera.")
        self.assertFalse(is_duplicate(other, state, now))

    def test_titolo_con_caratteri_html(self):
        self.assertIn("&lt;", format_message(self.enriched("Interpello A041 <urgente>")))


if __name__ == "__main__":
    unittest.main()
