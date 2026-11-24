#!/usr/bin/env python3
"""Per-country lists of blocked domains, built from OONI's open measurements.

For every country OONI measured in the last 30 days, a domain is listed when
  - OONI confirmed a block page for it there, or
  - at least 5 successful-or-anomalous tests ran and 60%+ of them were anomalous,
and it is not anomalous in 80%+ of the 20+ countries that measured it (a broken site, not a block).

Output: countries/<cc>.txt (one domain per line, a leading "www." removed) and index.json.
Data: OONI (https://ooni.org), CC BY 4.0. Standard library only.
"""
import datetime, ipaddress, json, os, sys, time, urllib.parse, urllib.request

API = "https://api.ooni.io/api/v1/aggregation"
DAYS = 30
MIN_TESTS = 5
ANOMALY_SHARE = 0.6
EVERYWHERE_SHARE = 0.8        # flagged in 80%+ of the countries that measured it -> a broken site
EVERYWHERE_MIN = 20           # ...judged only when at least this many countries measured it
UA = "routelists-builder (+https://github.com/routelists/lists)"


def get(params, tries=4):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def is_ip(host):
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def main(only=None):
    until = datetime.date.today()
    since = until - datetime.timedelta(days=DAYS)
    window = {"test_name": "web_connectivity", "since": since.isoformat(), "until": until.isoformat()}
    countries = only or sorted(r["probe_cc"] for r in get({**window, "axis_x": "probe_cc"})["result"]
                               if r.get("probe_cc") and r["probe_cc"] != "ZZ" and r.get("measurement_count", 0) >= 50)
    flagged = {}           # cc -> {domain: confirmed?}
    measured_in = {}       # domain -> countries with enough tests
    for cc in countries:
        try:
            rows = get({**window, "probe_cc": cc, "axis_x": "domain"})["result"]
        except Exception as e:  # noqa: BLE001
            print(f"{cc}: skipped ({e})", file=sys.stderr)
            continue
        out = {}
        for r in rows:
            d = (r.get("domain") or "").strip().lower().rstrip(".")
            if not d or is_ip(d) or "." not in d:
                continue
            tested = r.get("measurement_count", 0) - r.get("failure_count", 0)
            if tested >= MIN_TESTS:
                measured_in[d] = measured_in.get(d, 0) + 1
            confirmed = r.get("confirmed_count", 0) > 0
            anomalous = tested >= MIN_TESTS and r.get("anomaly_count", 0) / tested >= ANOMALY_SHARE
            if confirmed or anomalous:
                out[d] = confirmed
        flagged[cc] = out
        print(f"{cc}: {len(rows)} measured, {len(out)} flagged", file=sys.stderr)
        time.sleep(1)
    flagged_in = {}
    for out in flagged.values():
        for d in out:
            flagged_in[d] = flagged_in.get(d, 0) + 1
    os.makedirs("countries", exist_ok=True)
    index = {"generated": until.isoformat(), "window_days": DAYS, "source": "OONI web_connectivity (CC BY 4.0)", "countries": {}}
    for cc, out in flagged.items():
        def broken(d):
            n = measured_in.get(d, 0)
            return n >= EVERYWHERE_MIN and flagged_in[d] > EVERYWHERE_SHARE * n
        keep = sorted({(d[4:] if d.startswith("www.") else d) for d, confirmed in out.items()
                       if confirmed or not broken(d)})
        if not keep:
            continue
        with open(f"countries/{cc.lower()}.txt", "w") as f:
            f.write(f"# Domains blocked in {cc} per OONI measurements {since}..{until} (https://ooni.org, CC BY 4.0)\n")
            f.write("\n".join(keep) + "\n")
        index["countries"][cc] = len(keep)
    with open("index.json", "w") as f:
        json.dump(index, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main([c.upper() for c in sys.argv[1:]] or None)
