#!/usr/bin/env python3
"""Bot Telegram: avvisa quando un ufficio scolastico pubblica un interpello A041.

Uso:
  python bot.py --test           invia un messaggio di prova su Telegram
  python bot.py --chat-id        mostra il chat id (dopo aver scritto al bot)
  python bot.py                  esegue una scansione e termina
  python bot.py --loop           scansiona di continuo (default ogni 10 minuti)
  python bot.py --report         mostra lo stato delle fonti, per regione
  python bot.py --dry-run --backfill 14
                                 mostra gli avvisi degli ultimi 14 giorni senza inviare nulla
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html as htmllib
import io
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
SOURCES_FILE = ROOT / "sources.json"
COMUNI_FILE = ROOT / "comuni.json"
UA = "InterpelliA041Bot/1.0 (avvisi personali per docente; polling lento)"
WINDOW_DAYS = 30
RETENTION_DAYS = 150
MAX_PDF_BYTES = 8_000_000
SOURCE_ALERT_AFTER_HOURS = 24
DUPLICATE_DAYS = 7

PROVINCE = {
    "AG": ("Agrigento", "Sicilia"), "AL": ("Alessandria", "Piemonte"), "AN": ("Ancona", "Marche"),
    "AO": ("Aosta", "Valle d'Aosta"), "AP": ("Ascoli Piceno", "Marche"), "AQ": ("L'Aquila", "Abruzzo"),
    "AR": ("Arezzo", "Toscana"), "AT": ("Asti", "Piemonte"), "AV": ("Avellino", "Campania"),
    "BA": ("Bari", "Puglia"), "BG": ("Bergamo", "Lombardia"), "BI": ("Biella", "Piemonte"),
    "BL": ("Belluno", "Veneto"), "BN": ("Benevento", "Campania"), "BO": ("Bologna", "Emilia-Romagna"),
    "BR": ("Brindisi", "Puglia"), "BS": ("Brescia", "Lombardia"), "BT": ("Barletta-Andria-Trani", "Puglia"),
    "BZ": ("Bolzano", "Trentino-Alto Adige"), "CA": ("Cagliari", "Sardegna"), "CB": ("Campobasso", "Molise"),
    "CE": ("Caserta", "Campania"), "CH": ("Chieti", "Abruzzo"), "CL": ("Caltanissetta", "Sicilia"),
    "CN": ("Cuneo", "Piemonte"), "CO": ("Como", "Lombardia"), "CR": ("Cremona", "Lombardia"),
    "CS": ("Cosenza", "Calabria"), "CT": ("Catania", "Sicilia"), "CZ": ("Catanzaro", "Calabria"),
    "EN": ("Enna", "Sicilia"), "FC": ("Forlì-Cesena", "Emilia-Romagna"), "FE": ("Ferrara", "Emilia-Romagna"),
    "FG": ("Foggia", "Puglia"), "FI": ("Firenze", "Toscana"), "FM": ("Fermo", "Marche"),
    "FR": ("Frosinone", "Lazio"), "GE": ("Genova", "Liguria"), "GO": ("Gorizia", "Friuli-Venezia Giulia"),
    "GR": ("Grosseto", "Toscana"), "IM": ("Imperia", "Liguria"), "IS": ("Isernia", "Molise"),
    "KR": ("Crotone", "Calabria"), "LC": ("Lecco", "Lombardia"), "LE": ("Lecce", "Puglia"),
    "LI": ("Livorno", "Toscana"), "LO": ("Lodi", "Lombardia"), "LT": ("Latina", "Lazio"),
    "LU": ("Lucca", "Toscana"), "MB": ("Monza e Brianza", "Lombardia"), "MC": ("Macerata", "Marche"),
    "ME": ("Messina", "Sicilia"), "MI": ("Milano", "Lombardia"), "MN": ("Mantova", "Lombardia"),
    "MO": ("Modena", "Emilia-Romagna"), "MS": ("Massa-Carrara", "Toscana"), "MT": ("Matera", "Basilicata"),
    "NA": ("Napoli", "Campania"), "NO": ("Novara", "Piemonte"), "NU": ("Nuoro", "Sardegna"),
    "OR": ("Oristano", "Sardegna"), "PA": ("Palermo", "Sicilia"), "PC": ("Piacenza", "Emilia-Romagna"),
    "PD": ("Padova", "Veneto"), "PE": ("Pescara", "Abruzzo"), "PG": ("Perugia", "Umbria"),
    "PI": ("Pisa", "Toscana"), "PN": ("Pordenone", "Friuli-Venezia Giulia"), "PO": ("Prato", "Toscana"),
    "PR": ("Parma", "Emilia-Romagna"), "PT": ("Pistoia", "Toscana"), "PU": ("Pesaro e Urbino", "Marche"),
    "PV": ("Pavia", "Lombardia"), "PZ": ("Potenza", "Basilicata"), "RA": ("Ravenna", "Emilia-Romagna"),
    "RC": ("Reggio Calabria", "Calabria"), "RE": ("Reggio Emilia", "Emilia-Romagna"), "RG": ("Ragusa", "Sicilia"),
    "RI": ("Rieti", "Lazio"), "RM": ("Roma", "Lazio"), "RN": ("Rimini", "Emilia-Romagna"),
    "RO": ("Rovigo", "Veneto"), "SA": ("Salerno", "Campania"), "SI": ("Siena", "Toscana"),
    "SO": ("Sondrio", "Lombardia"), "SP": ("La Spezia", "Liguria"), "SR": ("Siracusa", "Sicilia"),
    "SS": ("Sassari", "Sardegna"), "SU": ("Sud Sardegna", "Sardegna"), "SV": ("Savona", "Liguria"),
    "TA": ("Taranto", "Puglia"), "TE": ("Teramo", "Abruzzo"), "TN": ("Trento", "Trentino-Alto Adige"),
    "TO": ("Torino", "Piemonte"), "TP": ("Trapani", "Sicilia"), "TR": ("Terni", "Umbria"),
    "TS": ("Trieste", "Friuli-Venezia Giulia"), "TV": ("Treviso", "Veneto"), "UD": ("Udine", "Friuli-Venezia Giulia"),
    "VA": ("Varese", "Lombardia"), "VB": ("Verbano-Cusio-Ossola", "Piemonte"), "VC": ("Vercelli", "Piemonte"),
    "VE": ("Venezia", "Veneto"), "VI": ("Vicenza", "Veneto"), "VR": ("Verona", "Veneto"),
    "VT": ("Viterbo", "Lazio"), "VV": ("Vibo Valentia", "Calabria"),
}
# Comuni omonimi di istituti ("Da Vinci", "Cavour", "Bramante-Genga") o di parole comuni: mai usati da soli.
COMUNI_AMBIGUI = {"vinci", "cavour", "genga", "marconi", "volta", "ali", "ne", "re", "lei", "sale", "ora", "ore", "mori", "scuola"}
PREPOSIZIONI = {"di", "a", "presso", "sede"}

# --- Riconoscimento dell'A041 -------------------------------------------------
CDC_RE = re.compile(r"(?<![A-Za-z0-9])(?:[Aa]0?41|A[\s\-_+./]{1,2}0?41|a[\-_+.]0?41)(?!\d)")
LABEL_RE = re.compile(r"scienze\s+e\s+tecnologie\s+informatiche", re.I)
# B016 "Laboratori di scienze e tecnologie informatiche" è un'altra classe di concorso.
LAB_RE = re.compile(r"laborator\w*\s+(?:di\s+)?(?:scienze\s+e\s+tecnologie\s+)?informatic\w*", re.I)
INFORMATICA_RE = re.compile(r"\binformatica\b", re.I)
OTHER_CDC_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:A[\s\-]?0?(?!41(?!\d))\d{2}|A[BCDIJLM]\d{2}|AS\d[A-Z]?|AM\d[A-Z]?|B[\s\-]?0?\d{2}|"
    r"AAAA|EEEE|ADAA|ADEE|ADMM|ADSS|EEIL|PPPP|AR\d{2}|DSGA)(?![A-Za-z0-9])"
)
INTERPELLO_RE = re.compile(r"interr?pell|supplenz|ricerca\s+(?:di\s+)?(?:un\s+)?(?:docent|supplent)|reclutamento", re.I)
EXCLUDE_RE = re.compile(
    r"\besit[oi]\b|\bgraduatori[ae]\b|\bdecreto\b|\bannullat|\brevoc|\bconcorso\s+(?:docenti|per\s+titoli)\b|"
    r"\bD\.?\s?D\.?\s?G\b|\bD\.?S\.?G\.?A\b|\bconciliazion|\bmobilit[aà]\b|\bdirigent|\bpersonale\s+ata\b|"
    r"\bassistente\s+tecnico\b|\bcollaboratore\s+scolastico\b",
    re.I,
)
NO_PDF_NEEDED_RE = re.compile(r"primaria|infanzia|sostegno|\bATA\b|assistente|collaborator|\bdsga\b|d\.s\.g\.a|preventiv", re.I)
MECC_RE = re.compile(r"\b([A-Z]{2})[A-Z]{2}\d{5}[0-9A-Z]\b")
SIGLA_RE = re.compile(r"\(([A-Z]{2})\)")
MESI = {m: i + 1 for i, m in enumerate(
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
DATE_PAT = r"(?:(\d{1,2})[/.\-_](\d{1,2})[/.\-_](\d{2,4})|(\d{1,2})\s+(" + "|".join(MESI) + r")\s+(\d{4}))"
DEADLINE_RE = re.compile(r"(?:scadenza|entro|non\s+oltre|termine\s+(?:di\s+)?(?:presentazione|invio))[^.;\n]{0,70}?" + DATE_PAT, re.I)
UNTIL_TITLE_RE = re.compile(r"(?:fino\s+al|sino\s+al|\bal)\s+" + DATE_PAT, re.I)
UNTIL_TEXT_RE = re.compile(r"(?:fino\s+al|sino\s+al)\s+" + DATE_PAT, re.I)
HOURS_RE = re.compile(r"\b(\d{1,2})\s*(?:h\b|ore\b(?!\s*\d{1,2}[:.]\d))|\bh\.?\s*(\d{1,2})\b|\bn\.?\s*ore\s*(\d{1,2})\b", re.I)
SKIP_LINK_RE = re.compile(r"facebook\.com|twitter\.com|linkedin\.com|whatsapp|mailto:|t(?:elegram)?\.me/share|sharer", re.I)
MODEL_RE = re.compile(r"modell|allegato|domanda|informativa|privacy|fac.?simile", re.I)


@dataclass
class Post:
    source: str
    title: str
    html: str
    link: str
    date: str = ""
    listing: bool = False
    on_interpelli_page: bool = False  # sezione dedicata: il testo può dire solo "Posto A041 18 ore"


@dataclass
class Item:
    key: str
    title: str
    link: str
    source: str
    date: str = ""
    pdf: str = ""
    text: str = ""
    mecc: str = ""
    sigla: str = ""
    comune: str = ""
    regione: str = ""
    provincia: str = ""
    stimata: bool = False
    ore: str = ""
    fino_dt: dt.date | None = None
    scadenza_dt: dt.date | None = None
    fp: str = ""


def clean(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\bDownload\b", " ", htmllib.unescape(s))
    return re.sub(r"\s+", " ", s).strip()


def is_a041(text, title=False):
    if CDC_RE.search(text):
        return True
    without_lab = LAB_RE.sub(" ", text)
    if LABEL_RE.search(without_lab):
        return True
    return bool(title and INFORMATICA_RE.search(without_lab) and not OTHER_CDC_RE.search(text))


def links_in(fragment, base):
    out = []
    for href, label in re.findall(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', fragment, re.S | re.I):
        href = htmllib.unescape(href).strip()
        if SKIP_LINK_RE.search(href) or href.startswith("#") or href.lower().startswith("javascript"):
            continue
        out.append((urllib.parse.urljoin(base, href), clean(label)))
    return out


def is_pdf(url):
    return ".pdf" in urllib.parse.urlparse(url).path.lower()


def real_pdfs(html, base):
    return [u for u, label in links_in(html, base) if is_pdf(u) and not MODEL_RE.search(u + label)]


def blocks_of(html):
    if html.count('class="results-row"') >= 1:  # tabella interpelli della Liguria
        return re.split(r'(?=<div class="results-row")', html)[1:]
    blocks = re.split(r"(?i)</(?:p|li|tr|div|h[1-6]|article|section)\s*>", html)
    return [b for b in blocks if (clean(b) or "href" in b.lower()) and not re.search(r"<(?:select|option|form)\b", b, re.I)]


def extract_items(post):
    """Trasforma un post (o una pagina-elenco) negli avvisi A041 che contiene."""
    title, body = clean(post.title), clean(post.html)
    if not post.listing:
        if EXCLUDE_RE.search(title) and not re.search(r"errata", title, re.I):
            return []
        if not post.on_interpelli_page and not INTERPELLO_RE.search(title + " " + body[:1500]):
            return []

    matched, others = [], 0
    for block in blocks_of(post.html):
        text, links = clean(block), links_in(block, post.link)
        haystack = text + " " + " ".join(urllib.parse.unquote(u) for u, _ in links)
        if is_a041(haystack):
            if not (post.listing and EXCLUDE_RE.search(text)):
                matched.append((text, links))
        elif links and OTHER_CDC_RE.search(haystack):
            others += 1

    hrefs = {links[0][0] for _, links in matched if links}
    if matched and (post.listing or others > 0 or len(hrefs) > 1):
        items, seen = [], set()
        for text, links in matched:
            link = links[0][0] if links else post.link
            if link in seen or (post.listing and not links):
                continue
            seen.add(link)
            label = re.sub(r"Vai all.interpello\W*", "", text).strip() or links[0][1]
            items.append(Item(key=link, title=label[:220], link=link, source=post.source, date=post.date,
                              pdf=link if is_pdf(link) else "", text=text[:1500]))
        return items
    if matched or is_a041(title, title=True):
        pdfs = real_pdfs(post.html, post.link)
        return [Item(key=post.link, title=title[:220], link=post.link, source=post.source, date=post.date,
                     pdf=pdfs[0] if pdfs else "", text=body[:3000])]
    return []


def needs_pdf_check(post):
    """Avviso senza classe di concorso nel testo: l'unico modo per capirlo è leggere il PDF."""
    title, body = clean(post.title), clean(post.html)
    text = title + " " + body
    if not re.search(r"interr?pell", title, re.I) or EXCLUDE_RE.search(title):
        return False
    return not OTHER_CDC_RE.search(text) and not NO_PDF_NEEDED_RE.search(text) and not is_a041(text)


# --- Dati dell'avviso ---------------------------------------------------------
def parse_date(groups):
    try:
        if groups[0]:
            d, m, y = int(groups[0]), int(groups[1]), int(groups[2])
            y = y + 2000 if y < 100 else y
        else:
            d, m, y = int(groups[3]), MESI[groups[4].lower()], int(groups[5])
        return dt.date(y, m, d)
    except (ValueError, TypeError):
        return None


def load_comuni():
    if COMUNI_FILE.exists():
        return json.loads(COMUNI_FILE.read_text(encoding="utf8"))
    return {}


COMUNI = load_comuni()


def find_comune(text):
    """Cerca un comune: preferisce quelli dopo 'di/a/presso'. A parità vince l'ultimo trovato."""
    words = re.findall(r"[A-Za-zÀ-ÿ'’]+", text)
    found = []
    for i in range(len(words)):
        for size in (4, 3, 2, 1):
            chunk = words[i:i + size]
            cand = " ".join(chunk).lower().replace("’", "'")
            if len(chunk) != size or cand not in COMUNI:
                continue
            prep = i > 0 and words[i - 1].lower() in PREPOSIZIONI
            if cand in COMUNI_AMBIGUI or (len(cand) < 5 and not prep):
                continue
            found.append((prep, cand))
            break
    with_prep = [c for prep, c in found if prep]
    return (with_prep or [c for _, c in found] or [None])[-1]


def enrich(item, extra_text=""):
    """Ricava scuola, luogo, ore e date. Non usa mai la sede di chi pubblica: gli uffici si ripubblicano a vicenda."""
    text = f"{item.title} {item.text} {extra_text}"
    named = f"{item.title} {urllib.parse.unquote(item.link)}".upper()

    candidates = list(MECC_RE.finditer(named)) + list(MECC_RE.finditer(text[:6000]))
    for m in candidates:
        if m.group(1) in PROVINCE:
            item.mecc, item.sigla = m.group(0), m.group(1)
            break
    if not item.sigla:
        for m in SIGLA_RE.finditer(item.title + " " + text[:1500]):
            if m.group(1) in PROVINCE:
                item.sigla = m.group(1)
                break
    comune = find_comune(item.title) or (find_comune(text[:800]) if not item.sigla else None)
    if comune:
        item.comune = comune.title()
        if not item.sigla and COMUNI.get(comune) in PROVINCE:
            item.sigla = COMUNI[comune]
            item.stimata = True
    if item.sigla:
        item.provincia, item.regione = PROVINCE[item.sigla]

    hours = HOURS_RE.search(item.title)
    if hours:
        value = next(v for v in hours.groups() if v)
        if 1 <= int(value) <= 24:
            item.ore = value

    deadline = DEADLINE_RE.search(text)
    if deadline:
        item.scadenza_dt = parse_date(deadline.groups())
    until = UNTIL_TITLE_RE.search(item.title) or UNTIL_TEXT_RE.search(text[:3000])
    if until:
        item.fino_dt = parse_date(until.groups())
    # Una data anteriore alla pubblicazione è una citazione normativa letta male, non la scadenza dell'avviso.
    published = dt.date.fromisoformat(item.date[:10]) if item.date else dt.date.today() - dt.timedelta(days=3)
    if item.scadenza_dt and item.scadenza_dt < published:
        item.scadenza_dt = None
    if item.fino_dt and item.fino_dt < published:
        item.fino_dt = None

    item.fp = fingerprint(item)
    return item


def fingerprint(item):
    """Lo stesso avviso ripubblicato da più uffici deve produrre una sola notifica."""
    period = (item.fino_dt or item.scadenza_dt or "")
    if item.mecc:
        return f"{item.mecc}|{item.ore}|{period}"
    if item.comune and (item.ore or period):
        return f"{item.comune.lower()}|{item.ore}|{period}"
    norm = re.sub(r"[^a-z0-9]+", " ", item.title.lower())
    return hashlib.sha1(" ".join(norm.split()).encode()).hexdigest()[:16]


def places_of(item):
    return [p for p in (item.mecc, item.comune.lower()) if p]


def is_duplicate(item, state, now):
    """Vero se già inviato. Con pochi dettagli basta la stessa scuola o lo stesso comune nell'ultima settimana."""
    if item.fp in state["fps"]:
        return True
    limit = (now - dt.timedelta(days=DUPLICATE_DAYS)).isoformat()
    complete = bool(item.ore and (item.fino_dt or item.scadenza_dt))
    for place in places_of(item):
        known = state["places"].get(place)
        if known and known["at"] >= limit and not (complete and known["complete"]):
            return True
    return False


def remember(item, state, stamp):
    state["fps"][item.fp] = stamp
    complete = bool(item.ore and (item.fino_dt or item.scadenza_dt))
    for place in places_of(item):
        state["places"][place] = {"at": stamp, "complete": complete}


def is_expired(item, today=None):
    today = today or dt.date.today()
    return bool((item.scadenza_dt and item.scadenza_dt < today) or (item.fino_dt and item.fino_dt < today))


def format_message(item):
    e = htmllib.escape
    if item.regione:
        place = f"<b>{e(item.regione)}</b> · {e(item.provincia)} ({item.sigla})"
        if item.comune:
            place += f" · {e(item.comune)}"
        if item.stimata:
            place += " <i>(località stimata)</i>"
        tag = "#" + re.sub(r"[^A-Za-z]", "", item.regione)
    else:
        place = "<b>Regione da verificare</b> (leggi l'avviso)"
        tag = "#DaVerificare"
    lines = ["🔔 <b>Interpello A041</b>", f"📍 {place}", f"🏫 {e(item.title)}"]
    details = []
    if item.ore:
        details.append(f"{item.ore} ore")
    if item.fino_dt:
        details.append(f"fino al {item.fino_dt:%d/%m/%Y}")
    if details:
        lines.append("🕐 " + " · ".join(details))
    if item.scadenza_dt:
        lines.append(f"⏳ Scadenza: <b>{item.scadenza_dt:%d/%m/%Y}</b>")
    links = [f'<a href="{e(item.link, quote=True)}">Apri l\'avviso</a>']
    if item.pdf and item.pdf != item.link:
        links.append(f'<a href="{e(item.pdf, quote=True)}">PDF</a>')
    lines.append("🔗 " + " · ".join(links))
    when = f" · {item.date[:10]}" if item.date else ""
    lines.append(f"🏛 Pubblicato da {e(item.source)}{when}")
    lines.append(f"{tag} #A041")
    return "\n".join(lines)[:4000]


# --- Rete --------------------------------------------------------------------
def http_get(url, timeout=30, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(limit + 1) if limit else resp.read()
    if limit and len(data) > limit:
        raise ValueError("file troppo grande")
    return data


def pdf_text(url):
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)
    try:
        reader = PdfReader(io.BytesIO(http_get(url, limit=MAX_PDF_BYTES)))
        return " ".join((page.extract_text() or "") for page in reader.pages[:3])
    except Exception:
        return ""  # PDF scansionato o danneggiato: l'avviso resta valido, solo con meno dettagli


def fetch_wp(source, now):
    since = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    posts, errors = {}, []
    for term in ("interpell", "A041"):
        query = urllib.parse.urlencode({"search": term, "per_page": 50, "modified_after": since,
                                        "_fields": "date,modified,link,title,content"})
        try:
            for p in json.loads(http_get(f"{source['url']}/wp-json/wp/v2/posts?{query}").decode("utf8", "ignore")):
                if max(p["date"], p["modified"]) >= since:
                    posts[p["link"]] = Post(source["name"], p["title"]["rendered"], p["content"]["rendered"], p["link"], p["date"])
        except Exception as exc:
            errors.append(str(exc))
    if len(errors) == 2:
        raise RuntimeError(errors[0])
    return list(posts.values())


def fetch_rss(source, now):
    root = ET.fromstring(http_get(source["url"]))
    encoded = "{http://purl.org/rss/1.0/modules/content/}encoded"
    out = []
    for it in root.iter("item"):
        date = ""
        try:
            date = dt.datetime.strptime((it.findtext("pubDate") or "")[:25], "%a, %d %b %Y %H:%M:%S").isoformat()
        except ValueError:
            pass
        body = it.findtext(encoded) or it.findtext("description") or ""
        out.append(Post(source["name"], it.findtext("title") or "", body, it.findtext("link") or "", date))
    return out


def mim_cards(source, page):
    """Portale del Ministero: ogni avviso è un <article> con data, titolo e descrizione."""
    posts = []
    for card in re.findall(r"<article\b.*?</article>", page, re.S | re.I):
        heading = re.search(r'<h3\b[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S | re.I)
        if not heading:
            continue
        link = urllib.parse.urljoin(source["url"], htmllib.unescape(heading.group(1)))
        after = card[heading.end():]
        description = clean(after)
        title = clean(heading.group(2))
        if description:
            title = f"{title} – {description}"
        date = ""
        when = re.search(r'article_data">\s*' + DATE_PAT, card, re.I)
        if when and parse_date(when.groups()):
            date = parse_date(when.groups()).isoformat()
        posts.append(Post(source["name"], title, heading.group(0) + after, link, date,
                          on_interpelli_page="interpelli" in source["url"]))
    return posts


def fetch_html(source, now):
    page = http_get(source["url"], timeout=45, limit=6_000_000).decode("utf8", "ignore")
    return mim_cards(source, page) or [Post(source["name"], source["name"], page, source["url"], listing=True)]


FETCHERS = {"wp": fetch_wp, "rss": fetch_rss, "html": fetch_html}


def scan_all(sources, now, workers=12):
    """Interroga le fonti: stesso host in sequenza, per non sovraccaricare i server degli uffici."""
    by_host = {}
    for s in sources:
        by_host.setdefault(urllib.parse.urlparse(s["url"]).netloc, []).append(s)

    def run_host(group):
        results = []
        for s in group:
            try:
                results.append((s, FETCHERS[s["type"]](s, now), None))
            except Exception as exc:
                results.append((s, [], f"{type(exc).__name__}: {exc}"[:150]))
            time.sleep(0.5)
        return results

    with cf.ThreadPoolExecutor(workers) as pool:
        return [r for group in pool.map(run_host, by_host.values()) for r in group]


def details_for(item):
    """Legge il PDF (o la pagina di dettaglio) per ricavare scuola, scadenza e località."""
    if item.pdf:
        return pdf_text(item.pdf)
    if is_pdf(item.link):
        return pdf_text(item.link)
    try:
        page = http_get(item.link, limit=2_000_000).decode("utf8", "ignore")
    except Exception:
        return ""
    pdfs = real_pdfs(page, item.link)
    if pdfs:
        item.pdf = pdfs[0]
        text = pdf_text(item.pdf)
        if text:
            return text
    return clean(page)[:3000]


# --- Telegram ----------------------------------------------------------------
def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def telegram(method, payload):
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        sys.exit("Manca TELEGRAM_TOKEN: copia .env.example in .env e inserisci il token di BotFather.")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",
                                 data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read()
            if exc.code == 429 and attempt < 3:
                time.sleep(json.loads(body or b"{}").get("parameters", {}).get("retry_after", 5) + 1)
                continue
            raise RuntimeError(f"Telegram ha risposto {exc.code}: {body[:200]!r}") from None
        except urllib.error.URLError:
            if attempt == 3:
                raise
            time.sleep(5)


def send(text):
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not chat:
        sys.exit("Manca TELEGRAM_CHAT_ID: esegui python bot.py --chat-id dopo aver scritto al bot.")
    telegram("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
    time.sleep(1.1)


# --- Ciclo principale --------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf8"))
    return {"seen": {}, "fps": {}, "places": {}, "pdf": {}, "seeded": [], "health": {}, "heartbeat": ""}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=0), encoding="utf8")
    tmp.replace(STATE_FILE)


def prune(state, now):
    limit = (now - dt.timedelta(days=RETENTION_DAYS)).isoformat()
    for name in ("seen", "fps", "pdf"):
        state[name] = {k: v for k, v in state[name].items() if v >= limit}
    state["places"] = {k: v for k, v in state["places"].items() if v["at"] >= limit}


def allowed_regions():
    return {r.strip().lower() for r in os.environ.get("REGIONI", "").split(",") if r.strip()}


def items_from(post, state, stamp, read_pdfs=True):
    items = extract_items(post)
    if items or post.listing or not needs_pdf_check(post) or post.link in state["pdf"]:
        return items
    state["pdf"][post.link] = stamp
    if not read_pdfs:
        return []
    pdfs = real_pdfs(post.html, post.link)
    if not pdfs and not is_pdf(post.link):  # il Ministero mette i PDF nella pagina di dettaglio
        try:
            pdfs = real_pdfs(http_get(post.link, limit=2_000_000).decode("utf8", "ignore"), post.link)
        except Exception:
            pdfs = []
    for url in pdfs[:2]:
        text = pdf_text(url)
        if text and is_a041(text):
            return [Item(key=post.link, title=clean(post.title)[:220], link=post.link, source=post.source,
                         date=post.date, pdf=url, text=text[:3000])]
    return []


def scan_once(args, state, sources):
    now = dt.datetime.now()
    stamp = now.isoformat(timespec="seconds")
    regions = allowed_regions()
    backfill_from = (now - dt.timedelta(days=args.backfill)).strftime("%Y-%m-%d") if args.backfill else None
    new, ok, failed = [], 0, []
    for source, posts, err in scan_all(sources, now):
        health = state["health"].setdefault(source["name"], {"ok": "", "error": ""})
        if err:
            health["error"] = err
            failed.append(source["name"])
            continue
        ok += 1
        health.update(ok=stamp, error="")
        # Una fonte vista per la prima volta non deve inondare la chat con il suo arretrato.
        first = source["name"] not in state["seeded"]
        for post in posts:
            # Al primo passaggio l'arretrato non si legge: sarebbero centinaia di PDF scaricati per nulla.
            for item in items_from(post, state, stamp, read_pdfs=not first or bool(backfill_from)):
                if item.key in state["seen"]:
                    continue
                recent = bool(backfill_from and item.date and item.date[:10] >= backfill_from)
                if first and not recent:
                    state["seen"][item.key] = stamp
                else:
                    new.append(item)
        if first:
            state["seeded"].append(source["name"])

    sent = 0
    for item in sorted(new, key=lambda i: i.date):
        enrich(item, details_for(item))
        skip = is_duplicate(item, state, now) or is_expired(item) or (regions and item.regione and item.regione.lower() not in regions)
        if not skip:
            if args.dry_run:
                print("\n" + re.sub(r"</?(?:b|i|a)\b[^>]*>", "", format_message(item)))
            else:
                send(format_message(item))
            remember(item, state, stamp)
            sent += 1
        state["seen"][item.key] = stamp
        if not args.dry_run:
            save_state(state)  # se si interrompe qui, al riavvio non rimanda gli avvisi già inviati

    prune(state, now)
    print(f"[{stamp}] fonti ok {ok}/{len(sources)}, nuovi avvisi {sent}, in errore: {', '.join(failed) or 'nessuna'}")
    if not args.dry_run:
        heartbeat(state, sources, now)
        save_state(state)


def heartbeat(state, sources, now):
    """Una volta al giorno conferma che il bot è vivo e segnala le fonti ferme da oltre 24 ore."""
    today = now.strftime("%Y-%m-%d")
    if state.get("heartbeat") == today or now.hour < 8:
        return
    state["heartbeat"] = today
    limit = (now - dt.timedelta(hours=SOURCE_ALERT_AFTER_HOURS)).isoformat()
    down = [s["name"] for s in sources if state["health"].get(s["name"], {}).get("ok", "") < limit]
    text = f"✅ Bot attivo: {len(sources) - len(down)}/{len(sources)} fonti raggiungibili."
    if down:
        text += "\n⚠️ Ferme da oltre 24 ore, controllale a mano:\n" + htmllib.escape(", ".join(down))
    send(text)


def report(state, sources):
    by_region = {}
    for s in sources:
        by_region.setdefault(s["region"], []).append(s)
    for region in sorted(by_region):
        print(f"\n{region}")
        for s in by_region[region]:
            h = state["health"].get(s["name"], {})
            label = "ERR" if h.get("error") else "OK " if h.get("ok") else "?  "
            print(f"  {label} {s['name']}  {h.get('error', '')}")


def show_chat_id():
    updates = telegram("getUpdates", {}).get("result", [])
    chats = {u[k]["chat"]["id"]: u[k]["chat"].get("first_name") or u[k]["chat"].get("title")
             for u in updates for k in ("message", "channel_post") if k in u}
    if not chats:
        print("Nessun messaggio trovato: scrivi /start al tuo bot su Telegram e riprova.")
    for cid, name in chats.items():
        print(f"TELEGRAM_CHAT_ID={cid}   ({name})")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=10, help="minuti tra una scansione e l'altra")
    parser.add_argument("--dry-run", action="store_true", help="stampa senza inviare e senza salvare")
    parser.add_argument("--backfill", type=int, default=0, help="al primo avvio invia anche gli avvisi degli ultimi N giorni")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--chat-id", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    load_env()
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf8"))
    state = load_state()
    if args.chat_id:
        return show_chat_id()
    if args.test:
        return send("✅ Il bot interpelli A041 è collegato correttamente.")
    if args.report:
        return report(state, sources)
    while True:
        try:
            scan_once(args, state, sources)
        except Exception as exc:
            if not args.loop:
                raise
            print(f"Errore nella scansione, riprovo al prossimo giro: {exc}", file=sys.stderr)
        if not args.loop:
            return
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
