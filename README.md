# routelists

Per-country lists of domains that are blocked there, rebuilt every day from
[OONI](https://ooni.org)'s open network measurements, for rule-based routing apps.

- `countries/<cc>.txt` — one domain per line (ISO 3166 alpha-2, lower case), e.g. `countries/tr.txt`.
- `index.json` — the build date and how many domains each country has.

A domain is listed for a country when, in the last 30 days, OONI confirmed a block page
for it there, or at least 5 tests ran and 60% or more of them were anomalous. A domain that
is anomalous in 80% or more of the 20+ countries that measured it is left out, since that
usually means the site itself is broken.

The data comes from OONI and is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
these lists are shared under the same licence. Thank you to OONI and its volunteers.
