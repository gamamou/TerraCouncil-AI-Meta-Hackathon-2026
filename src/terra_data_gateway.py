"""TERRA-DATA-GATEWAY-001: explicit, read-only API discovery and provenance capture.

Standard library only. Dry-run by default. No model calls, no automatic
promotion to admissible scientific evidence. Private outputs outside repo.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "terra_data_gateway_001.json"
API_HOSTS = {
    "nasa-power": "power.larc.nasa.gov",
    "openaq-stations": "api.openaq.org",
    "earth-search": "earth-search.aws.element84.com",
}
MAX_BYTES = 5 * 1024 * 1024

def read_manifest(path=MANIFEST):
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    if result.get("schema_version") != "TERRA_DATA_GATEWAY_001":
        raise ValueError("Unsupported gateway manifest")
    return result

def validate_point(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid WGS84 coordinates")
    return round(lat, 4), round(lon, 4)

def request_plan(provider, lat, lon, start="20250101", end="20250107"):
    lat, lon = validate_point(lat, lon)
    if provider == "nasa-power":
        for date in (start, end):
            if len(date) != 8 or not date.isdigit():
                raise ValueError("Dates must be YYYYMMDD")
        if start > end:
            raise ValueError("Start date after end date")
        params = urllib.parse.urlencode({
            "parameters": "T2M,WS10M,RH2M,PRECTOTCORR",
            "community": "AG",
            "longitude": lon, "latitude": lat,
            "start": start, "end": end, "format": "JSON"
        })
        return {"provider": provider,
                "url": "https://power.larc.nasa.gov/api/temporal/daily/point?" + params,
                "requires_key": False, "spatial_unit": "GRID_POINT_NOT_AOI",
                "scientific_status": "RAW_DISCOVERY_ONLY"}
    if provider == "openaq-stations":
        params = urllib.parse.urlencode({
            "coordinates": f"{lat:.4f},{lon:.4f}", "radius": 25000,
            "limit": 100, "page": 1
        })
        return {"provider": provider,
                "url": "https://api.openaq.org/v3/locations?" + params,
                "requires_key": True, "spatial_unit": "STATIONS_WITHIN_25KM",
                "scientific_status": "STATION_DISCOVERY_NOT_MEASUREMENTS"}
    if provider == "earth-search":
        # Collection metadata only. No AOI assertion or product download.
        return {"provider": provider,
                "url": "https://earth-search.aws.element84.com/v1/collections",
                "requires_key": False, "spatial_unit": "CATALOGUE_ONLY",
                "scientific_status": "CATALOG_DISCOVERY_ONLY"}
    raise ValueError("Unknown provider")

def fetch(plan, api_key=None, opener=None):
    parsed = urllib.parse.urlparse(plan["url"])
    if (parsed.scheme != "https" or parsed.hostname != API_HOSTS.get(plan["provider"])
            or parsed.username or parsed.password or parsed.port):
        raise ValueError("Unapproved API host or URL")
    if plan["requires_key"] and not api_key:
        raise ValueError("Missing OPENAQ_API_KEY environment setting")
    headers = {"User-Agent": "TerraCouncil-FSDC-Evidence-Gateway/0.1",
               "Accept": "application/json"}
    if plan["requires_key"]:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(plan["url"], headers=headers)
    open_url = opener or urllib.request.urlopen
    with open_url(req, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > MAX_BYTES:
            raise ValueError("API response exceeds size limit")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("API response exceeds size limit")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object from provider")
    return payload, data

def save_capture(plan, raw, out):
    dest = Path(out).expanduser()
    if dest.exists():
        raise ValueError("Output exists: no overwrites")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # No secrets in source URL or report.
    envelope = {"schema_version": "TERRA_API_RAW_CAPTURE_001",
       "provider": plan["provider"],
       "source_url": plan["url"],
       "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "raw_sha256": hashlib.sha256(raw).hexdigest(),
       "payload": json.loads(raw),
       "validation_status": "DOWNLOADED_UNVALIDATED",
       "field_validated": False,
       "notes": ["Provider JSON is not an admitted scientific observation.",
                 "Validate variable units, nodata, date availability, coverage and license.",
                 "Do not send to models before independent AOI-specific FSDC QA."]}
    with dest.open("x", encoding="utf-8") as target:
        json.dump(envelope, target, ensure_ascii=False, indent=2)
    return envelope

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=sorted(API_HOSTS))
    p.add_argument("--latitude", type=float, default=10.75)
    p.add_argument("--longitude", type=float, default=-14.25)
    p.add_argument("--start", default="20250101")
    p.add_argument("--end", default="20250107")
    p.add_argument("--execute", action="store_true", help="Perform one real HTTP request. No automatic retries.")
    p.add_argument("--out", help="Private JSON output when --execute")
    p.add_argument("--list", action="store_true", help="Show existing FAITH recovery and API sources")
    args = p.parse_args()
    if args.list:
        catalog = read_manifest()
        for row in catalog["recovered_works"] + catalog["api_sources"]:
            print(row["id"] + ": " + row["state"])
        return
    if not args.provider:
        p.error("--provider or --list required")
    plan = request_plan(args.provider, args.latitude, args.longitude, args.start, args.end)
    # The URL never contains a secret. NASA coordinates are public AOI reference.
    print(json.dumps({**plan, "execute": args.execute}, indent=2))
    if not args.execute:
        print("DRY_RUN: zero network calls, zero model calls")
        return
    if not args.out:
        p.error("--out required when --execute")
    key = os.environ.get("OPENAQ_API_KEY") if plan["requires_key"] else None
    raw, data = fetch(plan, api_key=key)
    envelope = save_capture(plan, raw, args.out)
    print("RAW_CAPTURE_SAVED: " + args.out)
    print("SHA256: " + envelope["raw_sha256"])
    print("SCIENTIFIC_STATUS: DOWNLOADED_UNVALIDATED")
    if args.provider == "openaq-stations":
        print("STATIONS_RETURNED: " + str(len(data.get("results", []))))
        print("NO_STATION_MEASUREMENTS_FETCHED")
    print("NO_META_CALLS")

if __name__ == "__main__":
    main()
