"""Rigenera sources.json: python tools/build_sources.py. Per aggiungere un ufficio basta una riga qui."""
import json
from pathlib import Path

WP = [
    ("Abruzzo", "AT Chieti-Pescara", "https://www.istruzionechietipescara.it"),
    ("Abruzzo", "AT L'Aquila", "https://lnx.csalaquila.it/wp"),
    ("Basilicata", "AT Matera", "https://www.istruzionematera.it"),
    ("Basilicata", "AT Potenza", "https://www.istruzionepotenza.it"),
    ("Calabria", "AT Catanzaro", "https://www.istruzione.calabria.it/catanzaro"),
    ("Calabria", "AT Cosenza", "https://www.istruzione.calabria.it/cosenza"),
    ("Calabria", "AT Crotone", "https://www.istruzione.calabria.it/crotone"),
    ("Calabria", "AT Reggio Calabria", "https://www.istruzioneatprc.it"),
    ("Calabria", "AT Vibo Valentia", "https://www.istruzione.calabria.it/vibovalentia"),
    ("Campania", "AT Avellino", "https://www.atavellino.it"),
    ("Campania", "AT Caserta", "https://www.uat-caserta.it"),
    ("Campania", "AT Napoli", "https://www.uat-napoli.it"),
    ("Emilia-Romagna", "AT Bologna", "https://bo.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Ferrara", "https://fe.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Forlì-Cesena", "https://fc.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Modena", "https://mo.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Parma", "https://pr.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Piacenza", "https://pc.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Ravenna", "https://ra.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Reggio Emilia", "https://re.istruzioneer.gov.it"),
    ("Emilia-Romagna", "AT Rimini", "https://rn.istruzioneer.gov.it"),
    ("Lazio", "AT Frosinone", "https://www.uspistruzione.fr.it/wp2"),
    ("Lazio", "AT Rieti", "https://www.usp-rieti.it"),
    ("Lazio", "AT Roma", "https://www.atpromaistruzione.it/atp"),
    ("Marche", "AT Ascoli Piceno", "https://www.uspascolipiceno.it"),
    ("Marche", "AT Pesaro Urbino", "https://www.usppesarourbino.it"),
    ("Piemonte", "AT Alessandria-Asti", "https://www.istruzionepiemonte.it/alessandria-asti"),
    ("Piemonte", "AT Biella", "https://www.istruzionepiemonte.it/biella"),
    ("Piemonte", "AT Cuneo", "https://www.istruzionepiemonte.it/cuneo"),
    ("Piemonte", "AT Novara", "https://www.istruzionepiemonte.it/novara"),
    ("Piemonte", "AT Torino", "https://www.istruzionepiemonte.it/torino"),
    ("Piemonte", "AT Verbania", "https://www.istruzionepiemonte.it/verbania"),
    ("Piemonte", "AT Vercelli", "https://www.istruzionepiemonte.it/vercelli"),
    ("Puglia", "AT Bari", "https://www.uspbari.it/usp"),
    ("Puglia", "AT BAT", "https://www.istruzionebat.it"),
    ("Puglia", "AT Brindisi", "https://www.istruzionebrindisi.it"),
    ("Puglia", "AT Foggia", "https://www.ustfoggia.it"),
    ("Sicilia", "USR Sicilia", "https://www.usr.sicilia.it"),
    ("Sicilia", "AT Agrigento", "https://ag.usr.sicilia.it"),
    ("Sicilia", "AT Caltanissetta-Enna", "https://cl-en.usr.sicilia.it"),
    ("Sicilia", "AT Catania", "https://ct.usr.sicilia.it"),
    ("Sicilia", "AT Messina", "https://me.usr.sicilia.it"),
    ("Sicilia", "AT Palermo", "https://pa.usr.sicilia.it"),
    ("Sicilia", "AT Ragusa", "https://rg.usr.sicilia.it"),
    ("Sicilia", "AT Siracusa", "https://sr.usr.sicilia.it"),
    ("Sicilia", "AT Trapani", "https://tp.usr.sicilia.it"),
    ("Toscana", "AT Firenze", "https://www.ust.fi.it"),
    ("Toscana", "AT Lucca", "https://www.ustlucca.it"),
    ("Toscana", "AT Massa-Carrara", "https://www.ustms.it"),
    ("Toscana", "AT Pistoia", "https://www.ufficioscolasticoprovinciale.pistoia.it"),
    ("Toscana", "AT Prato", "https://www.ufficioscolasticoprovinciale.prato.it"),
    ("Toscana", "AT Siena", "https://www.uspsi.it"),
    ("Umbria", "USR Umbria", "https://istruzione.umbria.it"),
    ("Veneto", "AT Belluno", "https://belluno.istruzioneveneto.gov.it"),
    ("Veneto", "AT Padova", "https://padova.istruzioneveneto.gov.it"),
    ("Veneto", "AT Rovigo", "https://rovigo.istruzioneveneto.gov.it"),
    ("Veneto", "AT Treviso", "https://treviso.istruzioneveneto.gov.it"),
    ("Veneto", "AT Venezia", "https://venezia.istruzioneveneto.gov.it"),
    ("Veneto", "AT Vicenza", "https://vicenza.istruzioneveneto.gov.it"),
]
RSS = [
    ("Toscana", "AT Arezzo", "https://www.arezzoistruzione.it/usparezzo/index.php/interpelli?format=feed&type=rss"),
    ("Veneto", "AT Verona", "https://www.istruzioneverona.it/?s=interpell&feed=rss2"),
]
MIM = "https://www.mim.gov.it/web/{}/interpelli-ricerca-supplenti"
HTML = [("Lombardia", f"AT {n}", MIM.format(p)) for n, p in [
    ("Bergamo", "bergamo"), ("Brescia", "brescia"), ("Como", "como"), ("Cremona", "cremona"), ("Lecco", "lecco"),
    ("Lodi", "lodi"), ("Mantova", "mantova"), ("Milano", "milano"), ("Monza Brianza", "monza-brianza"),
    ("Pavia", "pavia"), ("Sondrio", "sondrio"), ("Varese", "varese")]]
HTML += [("Sardegna", f"AT {n}", f"https://www.mim.gov.it/web/{n.lower()}") for n in ("Cagliari", "Nuoro", "Oristano", "Sassari")]
HTML += [("Molise", f"AT {n}", f"https://www.mim.gov.it/web/{n.lower()}") for n in ("Campobasso", "Isernia")]
HTML += [("Liguria", f"AT {n}", f"https://servizi.istruzioneliguria.gov.it/provincia.php?p={p}") for n, p in
         [("Genova", "GE"), ("Imperia", "IM"), ("La Spezia", "SP"), ("Savona", "SV")]]
HTML += [("Friuli-Venezia Giulia", f"AT {n}", f"https://usrfvg.gov.it/it/home/menu/uffici/ufficio-territoriale-di-{n.lower()}/Interpelli/")
         for n in ("Gorizia", "Pordenone", "Trieste", "Udine")]
HTML += [("Umbria", "Interpelli aperti Umbria", "https://istruzione.umbria.it/interpelli/interpelli-aperti/"),
         ("Veneto", "Tabella Treviso", "https://treviso.istruzioneveneto.gov.it/tabella-avvisi-finalizzati-al-reclutamento-docenti-om-88-2024-art-13-comma-23/"),
         ("Veneto", "Tabella Vicenza", "https://vicenza.istruzioneveneto.gov.it/avvisi-interpelli-docenti-vicenza/")]

sources = ([dict(region=r, name=n, type="wp", url=u) for r, n, u in WP]
           + [dict(region=r, name=n, type="rss", url=u) for r, n, u in RSS]
           + [dict(region=r, name=n, type="html", url=u) for r, n, u in HTML])
Path(__file__).resolve().parent.parent.joinpath("sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf8")
print(len(sources), "fonti")
