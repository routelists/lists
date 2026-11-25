#!/usr/bin/env python3
"""Per-country lists of blocked domains, built from OONI's open measurements.

Blocking is judged per network (ASN), so one filtered school or office network can't list a
domain for a whole country. Over the last 30 days, a network blocks a domain when OONI
confirmed a block page there, or at least 3 tests ran and 60%+ of them were anomalous.
A domain is listed for a country when
  - at least 2 networks block it, and
  - they are at least 25% of the networks that measured it,
and it isn't listed in 80%+ of the 20+ countries that measured it (a broken site, not a block).

A country whose data can't be fetched keeps its previous list.
Output: countries/<cc>.txt (one domain per line, a leading "www." removed) and index.json.
Data: OONI (https://ooni.org), CC BY 4.0. Standard library only.
"""
import datetime, ipaddress, json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://api.ooni.io/api/v1/aggregation"
DAYS = 30
MIN_TESTS = 3                 # tests on one network before its anomalies count
ANOMALY_SHARE = 0.6           # ...and the share of them that must be anomalous
MIN_NETWORKS = 2              # networks that must block a domain
NETWORK_SHARE = 0.25          # ...and their share of the networks that measured it
EVERYWHERE_SHARE = 0.8        # listed in 80%+ of the countries that measured it -> a broken site
EVERYWHERE_MIN = 20           # ...judged only when at least this many countries measured it
PAUSE = 4                     # seconds between countries (OONI rate-limits bursts)
UA = "routelists-builder (+https://github.com/routelists/lists)"


def get(params, tries=6):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            wait = 30 * (attempt + 1)
            if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                try:
                    wait = max(wait, int(e.headers.get("Retry-After", "0")))
                except ValueError:
                    pass
            time.sleep(min(wait, 600))


def host(d):
    """Lower-case host name, or None for IP addresses and junk."""
    d = (d or "").strip().lower().rstrip(".")
    if d.startswith("[") or d.count(":") > 1:
        return None                                   # IPv6
    d = d.split(":")[0]                               # drop a port
    if not d or "." not in d or "/" in d:
        return None
    try:
        ipaddress.ip_address(d)
        return None
    except ValueError:
        return d


def previous():
    try:
        with open("index.json") as f:
            return json.load(f).get("countries", {})
    except (OSError, ValueError):
        return {}


def main(only=None):
    until = datetime.date.today()
    since = until - datetime.timedelta(days=DAYS)
    window = {"test_name": "web_connectivity", "since": since.isoformat(), "until": until.isoformat()}
    countries = only or sorted(r["probe_cc"] for r in get({**window, "axis_x": "probe_cc"})["result"]
                               if r.get("probe_cc") and r["probe_cc"] != "ZZ" and r.get("measurement_count", 0) >= 50)
    listed = {}            # cc -> set of domains
    measured_in = {}       # domain -> countries where some network measured it
    failed = []
    for i, cc in enumerate(countries):
        if i:
            time.sleep(PAUSE)
        try:
            rows = get({**window, "probe_cc": cc, "axis_x": "domain", "axis_y": "probe_asn"})["result"]
        except Exception as e:  # noqa: BLE001
            print(f"{cc}: skipped ({e})", file=sys.stderr)
            failed.append(cc)
            continue
        blocking, measuring = {}, {}
        for r in rows:
            d = host(r.get("domain"))
            if not d:
                continue
            tested = r.get("measurement_count", 0) - r.get("failure_count", 0)
            confirmed = r.get("confirmed_count", 0) > 0
            anomalous = tested >= MIN_TESTS and r.get("anomaly_count", 0) / tested >= ANOMALY_SHARE
            if confirmed or tested >= MIN_TESTS:
                measuring[d] = measuring.get(d, 0) + 1
            if confirmed or anomalous:
                blocking[d] = blocking.get(d, 0) + 1
        for d in measuring:
            measured_in[d] = measured_in.get(d, 0) + 1
        listed[cc] = {d for d, n in blocking.items() if n >= MIN_NETWORKS and n >= NETWORK_SHARE * measuring[d]}
        print(f"{cc}: {len(rows)} rows, {len(listed[cc])} listed", file=sys.stderr)
    if only is None and len(failed) > len(countries) // 2:
        sys.exit(f"{len(failed)} of {len(countries)} countries failed; keeping yesterday's lists")
    listed_in = {}
    for out in listed.values():
        for d in out:
            listed_in[d] = listed_in.get(d, 0) + 1

    def broken(d):
        n = measured_in.get(d, 0)
        return n >= EVERYWHERE_MIN and listed_in[d] > EVERYWHERE_SHARE * n

    os.makedirs("countries", exist_ok=True)
    old = previous()
    index = {"generated": until.isoformat(), "window_days": DAYS, "source": "OONI web_connectivity (CC BY 4.0)",
             "countries": {cc: n for cc, n in old.items() if cc in failed}}
    for cc, out in listed.items():
        keep = sorted({(d[4:] if d.startswith("www.") else d) for d in out if not broken(d)})
        path = f"countries/{cc.lower()}.txt"
        if not keep:
            if os.path.exists(path):
                os.remove(path)
            continue
        with open(path, "w") as f:
            f.write(f"# Domains blocked in {cc} per OONI measurements {since}..{until} (https://ooni.org, CC BY 4.0)\n")
            f.write("\n".join(keep) + "\n")
        index["countries"][cc] = len(keep)
    if only is not None:
        index["countries"] = {**old, **index["countries"]}
    with open("index.json", "w") as f:
        json.dump(index, f, indent=1, sort_keys=True)
    if failed:
        print(f"kept previous lists for: {' '.join(failed)}", file=sys.stderr)


if __name__ == "__main__":
    main([c.upper() for c in sys.argv[1:]] or None)
