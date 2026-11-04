"""Rigenera comuni.json dall'elenco ISTAT: python tools/build_comuni.py"""
import csv
import io
import json
import urllib.request
from pathlib import Path

URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
rows = list(csv.reader(io.StringIO(raw.decode("latin1")), delimiter=";"))
header = [c.replace("\n", " ") for c in rows[0]]
name = next(i for i, c in enumerate(header) if c.startswith("Denominazione in italiano"))
sigla = next(i for i, c in enumerate(header) if c.startswith("Sigla automobilistica"))
out = {r[name].strip().lower().replace("’", "'"): r[sigla].strip() for r in rows[1:] if len(r) > sigla}
Path(__file__).resolve().parent.parent.joinpath("comuni.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
print(len(out), "comuni")
