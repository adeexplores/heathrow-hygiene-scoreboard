#!/usr/bin/env python3
# ============================================================================
#  resolve.py  -  TURN YOUR VENUE LIST INTO STABLE FSA IDs
# ----------------------------------------------------------------------------
#  WHAT THIS DOES
#    Reads venues.csv (your hotels, hotel restaurants and HTT eateries), looks
#    each one up on the FSA API by name + postcode, and saves the official
#    FHRSID (the stable record ID) to venues.json. fetch.py then refreshes the
#    live rating for each of those IDs, and you paste the same IDs into each
#    review page's badge (see badge.html).
#
#    It also lists OTHER food businesses at each venue's postcode, so you can
#    spot a hotel's separately-rated restaurant and add it to venues.csv.
#
#  WHEN TO RUN
#    Once now, and again only when you change venues.csv. The daily refresh is
#    fetch.py, not this.
#
#  RUN IT WITH:   python3 resolve.py
#
#  Anything that does not match cleanly is FLAGGED at the end for you to check.
# ============================================================================

import csv, json, sys, time, urllib.parse, urllib.request
from difflib import SequenceMatcher
import config

EATING_OUT = (1, 7841, 7842, 7843, 7844, 7846)   # restaurant, catering, hotel, pub, takeaway, mobile


def norm_postcode(pc):
    return (pc or "").replace(" ", "").upper().strip()


def similar(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def api_get(path, params):
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


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("name,postcode"):
                continue
            parts = [p.strip() for p in line.split(",")]
            name = parts[0] if parts else ""
            postcode = parts[1] if len(parts) > 1 else ""
            group = parts[2] if len(parts) > 2 else ""
            fhrsid = parts[3] if len(parts) > 3 else ""    # optional: lock to a known FSA ID
            if name:
                rows.append({"name": name, "postcode": postcode, "group": group,
                             "fhrsid": fhrsid.strip()})
    return rows


def resolve_fixed(entry):
    """A known FHRSID was supplied - just confirm it exists and capture its name."""
    fid = int(entry["fhrsid"])
    e = api_get(f"/Establishments/{fid}", None)
    return {"name": entry["name"], "postcode": entry["postcode"], "group": entry["group"],
            "fhrsid": fid, "matchedName": e.get("BusinessName"),
            "matchedPostcode": e.get("PostCode"), "status": "ok",
            "note": "locked to supplied FHRSID", "candidates": []}


def siblings_at_postcode(postcode, exclude_fhrsid):
    """Other eating-out venues at the same postcode (e.g. a hotel's restaurant)."""
    if not postcode:
        return []
    try:
        data = api_get("/Establishments", {"address": postcode, "pageSize": 50})
    except Exception:                                # noqa: BLE001
        return []
    pc = norm_postcode(postcode)
    out = []
    for e in data.get("establishments", []) or []:
        if norm_postcode(e.get("PostCode")) != pc:
            continue
        if e.get("FHRSID") == exclude_fhrsid:
            continue
        if e.get("BusinessTypeID") in EATING_OUT or e.get("BusinessType"):
            out.append({"FHRSID": e["FHRSID"], "BusinessName": e.get("BusinessName"),
                        "BusinessType": e.get("BusinessType"), "RatingValue": e.get("RatingValue")})
    return out


def resolve_one(entry):
    name, postcode = entry["name"], entry["postcode"]
    data = api_get("/Establishments", {"name": name, "pageSize": 50})
    results = data.get("establishments", []) or []
    pc = norm_postcode(postcode)
    pc_matches = [e for e in results if norm_postcode(e.get("PostCode")) == pc] if pc else []

    def pack(e, status, note=""):
        return {
            "name": name, "postcode": postcode, "group": entry["group"],
            "fhrsid": e["FHRSID"] if e else None,
            "matchedName": e.get("BusinessName") if e else None,
            "matchedPostcode": e.get("PostCode") if e else None,
            "status": status, "note": note,
            "candidates": [] if status == "ok" else [
                {"FHRSID": c["FHRSID"], "BusinessName": c.get("BusinessName"),
                 "PostCode": c.get("PostCode"), "RatingValue": c.get("RatingValue")}
                for c in results[:5]
            ],
        }

    if pc and len(pc_matches) == 1:
        return pack(pc_matches[0], "ok")
    if pc and len(pc_matches) > 1:
        ranked = sorted(pc_matches, key=lambda e: similar(name, e.get("BusinessName")), reverse=True)
        if similar(name, ranked[0].get("BusinessName")) - similar(name, ranked[1].get("BusinessName")) > 0.15:
            return pack(ranked[0], "ok", "auto-picked closest name among several at this postcode")
        out = pack(None, "multi", f"{len(pc_matches)} records share this postcode - confirm by hand")
        out["candidates"] = [
            {"FHRSID": c["FHRSID"], "BusinessName": c.get("BusinessName"),
             "PostCode": c.get("PostCode"), "RatingValue": c.get("RatingValue")} for c in ranked[:6]]
        return out
    if results:
        ranked = sorted(results, key=lambda e: similar(name, e.get("BusinessName")), reverse=True)
        if not pc and similar(name, ranked[0].get("BusinessName")) > 0.85:
            return pack(ranked[0], "ok", "matched by name (no postcode supplied - add one to be safe)")
        return pack(None, "nomatch", "no postcode match - check the candidates listed")
    return pack(None, "nomatch", "the API returned nothing for this name")


def main():
    entries = read_csv(config.VENUES_CSV)
    if not entries:
        print(f"No venues found in {config.VENUES_CSV}. Add some and re-run.")
        sys.exit(1)

    print(f"Resolving {len(entries)} venue(s) against the FSA API...\n")
    resolved, flags = [], []
    for i, entry in enumerate(entries, 1):
        try:
            r = resolve_fixed(entry) if entry.get("fhrsid") else resolve_one(entry)
        except Exception as e:                       # noqa: BLE001
            r = {"name": entry["name"], "postcode": entry["postcode"], "group": entry["group"],
                 "fhrsid": None, "status": "error", "note": str(e), "candidates": []}
        # Helpful extra: what else is at this postcode?
        sibs = []
        if config.SHOW_POSTCODE_SIBLINGS and r.get("fhrsid"):
            sibs = siblings_at_postcode(r.get("matchedPostcode") or entry["postcode"], r["fhrsid"])
            time.sleep(config.REQUEST_DELAY_SECONDS)
        resolved.append(r)

        mark = {"ok": "OK  ", "multi": "MULTI", "nomatch": "NONE", "error": "ERR "}.get(r["status"], "??")
        extra = f" -> FHRSID {r['fhrsid']} ({r.get('matchedName')})" if r["fhrsid"] else ""
        print(f"  [{i:>2}/{len(entries)}] {mark}  {entry['name']}{extra}")
        if sibs:
            print(f"        also at {r.get('matchedPostcode')}: " +
                  "; ".join(f"{s['BusinessName']} [FHRSID {s['FHRSID']}, {s['BusinessType']}]" for s in sibs))
        if r["status"] != "ok":
            flags.append(r)
        time.sleep(config.REQUEST_DELAY_SECONDS)

    with open(config.VENUES_JSON, "w", encoding="utf-8") as f:
        json.dump({"venues": resolved}, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(resolved)} record(s) to {config.VENUES_JSON}.")
    print("Tip: the FHRSID shown for each venue is what you paste into a review "
          "page badge (data-fhrsid). See badge.html.")
    if flags:
        print(f"\n!!  {len(flags)} venue(s) need YOUR attention (no clean match):\n")
        for r in flags:
            print(f"  - {r['name']} ({r['postcode']}): {r['status']} - {r.get('note','')}")
            for c in r.get("candidates", []):
                print(f"        candidate: FHRSID {c['FHRSID']}  {c['BusinessName']}  "
                      f"{c['PostCode']}  (rating {c['RatingValue']})")
    else:
        print("\nAll venues matched cleanly. Run fetch.py next.")


if __name__ == "__main__":
    main()
