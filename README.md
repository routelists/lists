# routelists

Per-country lists of domains that are blocked there, rebuilt every day from
[OONI](https://ooni.org)'s open network measurements, for rule-based routing apps.

- `countries/<cc>.txt` — one domain per line (ISO 3166 alpha-2, lower case), e.g. `countries/tr.txt`.
- `index.json` — the build date and how many domains each country has.

Blocking is judged network by network (ASN), so one filtered school or office network can't
put a domain on a whole country's list. Over the last 30 days, a network blocks a domain when
OONI confirmed a block page there, or at least 3 tests ran and 60% or more were anomalous.
A domain is listed when at least 2 networks block it and they are at least a quarter of the
networks that measured it. A domain listed in 80% or more of the 20+ countries that measured it
is left out, since that usually means the site itself is broken. If a country's data can't be
fetched on a given day, its previous list is kept.

The data comes from OONI and is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
these lists are shared under the same licence. Thank you to OONI and its volunteers.
