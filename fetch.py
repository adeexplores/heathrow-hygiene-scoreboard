#!/usr/bin/env python3
# ============================================================================
#  fetch.py  -  REFRESH THE LIVE RATINGS FOR YOUR VENUES (run on a schedule)
# ----------------------------------------------------------------------------
#  WHAT THIS DOES
#    Reads venues.json (made by resolve.py), calls the FSA API once per FHRSID,
#    and writes a clean data.json the scoreboard widget reads. Only the fields
#    the page needs are kept, plus a generatedAt timestamp.
#
#  ROBUSTNESS
#    - Small delay + retries between calls.
#    - If one venue fails, its LAST GOOD value is reused (flagged stale) and the
#      run continues - one failure never blanks the board.
#    - If everything fails, the existing data.json is left untouched.
#
#  WHEN TO RUN
#    On a schedule (see .github/workflows/refresh.yml) or by hand: python3 fetch.py
#
#  Settings live in config.py - you should not need to edit this file.
# ============================================================================

import json, re, time, datetime, os, urllib.parse, urllib.request
import config


def api_get(path, params=None):
    url = config.API_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    last_err = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=config.API_HEADER)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                       # noqa: BLE001
            last_err = e
            time.sleep(config.REQUEST_DELAY_SECONDS * attempt * 2)
    raise last_err


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "business"


def clean_record(e, group="", display_name=None):
    geo = e.get("geocode") or {}
    scores = e.get("scores") or {}
    rating = e.get("RatingValue")
    is_numeric = str(rating).isdigit()
    address = ", ".join(
        str(e.get(k)).strip() for k in
        ("AddressLine1", "AddressLine2", "AddressLine3", "AddressLine4")
        if e.get(k) and str(e.get(k)).strip())
    return {
        "fhrsid": e["FHRSID"],
        "name": display_name or e.get("BusinessName"),   # your HTT name for display
        "fsaName": e.get("BusinessName"),                 # the FSA's own listed name
        "businessType": e.get("BusinessType"),
        "rating": str(rating) if rating is not None else "",
        "ratingNumeric": int(rating) if is_numeric else None,
        "ratingKey": e.get("RatingKey"),
        "ratingDate": (e.get("RatingDate") or "")[:10],
        "hygiene": scores.get("Hygiene"),
        "structural": scores.get("Structural"),
        "confidence": scores.get("ConfidenceInManagement"),
        "localAuthority": e.get("LocalAuthorityName"),
        "postcode": e.get("PostCode"),
        "address": address,
        "lat": geo.get("latitude"),
        "lon": geo.get("longitude"),
        "fsaUrl": f"https://ratings.food.gov.uk/business/{slugify(e.get('BusinessName'))}/{e['FHRSID']}",
        "group": group,
        "stale": False,
    }


def load_previous():
    if not os.path.exists(config.DATA_JSON):
        return {}
    try:
        with open(config.DATA_JSON, encoding="utf-8") as f:
            return {r["fhrsid"]: r for r in json.load(f).get("establishments", [])}
    except Exception:                                # noqa: BLE001
        return {}


def main():
    started = datetime.datetime.now(datetime.timezone.utc)
    if not os.path.exists(config.VENUES_JSON):
        print(f"Missing {config.VENUES_JSON}. Run  python3 resolve.py  first.")
        return

    with open(config.VENUES_JSON, encoding="utf-8") as f:
        venues = [v for v in json.load(f).get("venues", []) if v.get("fhrsid")]
    if not venues:
        print("No resolved venues with an FHRSID. Edit venues.csv and re-run resolve.py.")
        return

    previous = load_previous()
    records, failed = [], []
    print(f"Refreshing {len(venues)} venue(s) from the FSA API...\n")
    for i, v in enumerate(venues, 1):
        fid = v["fhrsid"]
        try:
            e = api_get(f"/Establishments/{fid}")
            rec = clean_record(e, group=v.get("group", ""), display_name=v.get("name"))
            records.append(rec)
            print(f"  [{i:>2}/{len(venues)}] OK   {rec['name']} -> {rec['rating'] or 'n/a'}")
        except Exception as ex:                       # noqa: BLE001
            if fid in previous:
                stale = dict(previous[fid]); stale["stale"] = True
                records.append(stale)
                failed.append((v.get("name"), f"{ex} (kept last good value)"))
                print(f"  [{i:>2}/{len(venues)}] WARN {v.get('name')} failed - kept last good value")
            else:
                failed.append((v.get("name"), str(ex)))
                print(f"  [{i:>2}/{len(venues)}] FAIL {v.get('name')} - no previous value, left blank")
        time.sleep(config.REQUEST_DELAY_SECONDS)

    if not records:
        print("\n!! Nothing fetched and no previous data. Keeping any existing data.json untouched.")
        return

    records.sort(key=lambda r: (
        0 if r["ratingNumeric"] is not None else 1,
        -(r["ratingNumeric"] if r["ratingNumeric"] is not None else 0),
        (r["name"] or "").lower()))

    out = {
        "generatedAt": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(records),
        "attributionHtml": config.ATTRIBUTION_HTML,
        "establishments": records,
    }
    with open(config.DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\nWrote {config.DATA_JSON}: {len(records)} venue(s).")
    if failed:
        print(f"\n{len(failed)} venue(s) had problems this run:")
        for name, why in failed:
            print(f"  - {name}: {why}")


if __name__ == "__main__":
    main()
