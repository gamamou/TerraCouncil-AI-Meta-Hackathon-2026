"""TERRA-DATA-001: read-only retrieval of known FAITH scientific assets.

Unlike broad keyword discovery, matches precise file/folder patterns.
ZIP members are catalogued without extraction. No DB/API/model calls.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

MAX_FILES=150000
MAX_HASH_BYTES=128*1024*1024
SKIP={"node_modules",".git",".venv","venv","__pycache__","site-packages","AppData"}
RULES={
    "MAUS_V2_SOURCE": re.compile(r"^global_mining_polygons_v2\.(gpkg|zip)$",re.I),
    "GUINEA_CADASTRE": re.compile(r"^official_guinea_cadastre_(all_layers_raw|final_clean)\.geojson$|^official_guinea_cadastre_for_gee\.(shp|shx|dbf|prj)$",re.I),
    "CHENG_FUNCTIONAL_CLASS": re.compile(r"(cheng|functional.mine|functional.land.use|mine.land.use|open.pit|waste.dump)",re.I),
    "TERRA_BOKE_010HI_HJ": re.compile(r"^010H[I-J]_(evidence|spatial_qa)\.json$|^boke_screened_evidence\.json$",re.I),
    "FSDC_AIR_DUST": re.compile(r"(aermod|aermet|pm10|pm2[._-]?5|dust|dispersion|receptor)",re.I),
    "FSDC_FOREST_CLIMATE_WATER": re.compile(r"(hansen|dynamicworld|jrc_tmf|wapor|chirps|era5)",re.I),
}
SUPPORTED={".gpkg",".geojson",".shp",".shx",".dbf",".prj",".zip",".json",".csv",
           ".tif",".tiff",".nc",".grib",".grb",".parquet",".dat",".inp",".out",".txt"}
KNOWN_MAUS_SHA256="6936e2743a21ba952b4de3e4b6f77099a0aa4479f7e2639d9d1b0787876a3ea1"
def classify(name):
    """Only filename/basename; directory names do not imply scientific identity."""
    base=Path(name).name
    extension=Path(base).suffix.lower()
    if extension not in SUPPORTED:
        return []
    return [key for key,pattern in RULES.items() if pattern.search(base)]
def checksum(path):
    h=hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda:inp.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()
def scan(roots,max_files=MAX_FILES,inspect_zip=True):
    matches=[];errors=[];seen=0
    for root in roots:
        base=Path(root).expanduser()
        if not base.is_dir():
            errors.append({"root":str(base),"type":"MISSING_ROOT"})
            continue
        for folder,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=[d for d in dirs if d not in SKIP and not (Path(folder)/d).is_symlink()]
            for name in files:
                seen+=1
                if seen>max_files:
                    errors.append({"root":str(base),"type":"MAX_FILES_REACHED"})
                    break
                p=Path(folder)/name
                if p.is_symlink():
                    continue
                classes=classify(name)
                if classes:
                    try:
                        size=p.stat().st_size
                        sha=checksum(p) if size<=MAX_HASH_BYTES else None
                        matches.append({
                            "filename":name,"path":str(p),"source_kind":"LOCAL_FILE",
                            "classes":classes,"size_bytes":size,"sha256":sha,
                            "hash_status":"HASHED" if sha else "DEFERRED_LARGE_FILE",
                            "source_integrity":("MATCHES_FAITH_REFERENCE" if sha==KNOWN_MAUS_SHA256
                                                else "NOT_REFERENCE_VERIFIED" if "MAUS_V2_SOURCE" in classes
                                                else "UNASSESSED")})
                    except OSError as exc:
                        errors.append({"filename":name,"type":type(exc).__name__})
                if inspect_zip and p.suffix.lower()==".zip":
                    try:
                        with zipfile.ZipFile(p) as z:
                            for info in z.infolist():
                                if info.is_dir():
                                    continue
                                tags=classify(info.filename)
                                if tags:
                                    matches.append({"filename":Path(info.filename).name,
                                      "path":str(p),"archive_member":info.filename,
                                      "source_kind":"ZIP_ENTRY_NOT_EXTRACTED",
                                      "classes":tags,"size_bytes":info.file_size,
                                      "sha256":None,"hash_status":"NOT_HASHED_INSIDE_ZIP",
                                      "source_integrity":"UNASSESSED"})
                    except (OSError,zipfile.BadZipFile,RuntimeError) as exc:
                        errors.append({"filename":name,"type":type(exc).__name__})
            if seen>max_files:
                break
    distinct={}
    for row in matches:
        key=(row["source_kind"],row.get("sha256") or row["path"]+":"+row.get("archive_member",""))
        distinct.setdefault(key,[]).append(row)
    return {"schema_version":"TERRA_DATA_RECOVERY_001",
        "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "files_seen":seen,"matches_count":len(matches),
        "unique_content_groups":len(distinct),
        "duplicates_possible":len(matches)-len(distinct),
        "read_only":True,"scientific_status":"INVENTORY_NOT_VALIDATED",
        "matches":matches,"errors":errors,
        "warning":"A filename or ZIP member is not a validated scientific dataset. Compare CRS, source hash, rights, AOI and contents before debate. No automatic import."}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",action="append",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--max-files",type=int,default=MAX_FILES)
    p.add_argument("--no-zip",action="store_true")
    args=p.parse_args()
    if not 0<args.max_files<=MAX_FILES:
        p.error("Invalid max-files")
    dest=Path(args.out).expanduser()
    if dest.exists():
        p.error("Destination exists; do not overwrite")
    report=scan(args.root,args.max_files,not args.no_zip)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("FILES_SEEN="+str(report["files_seen"]))
    print("CANDIDATE_MATCHES="+str(report["matches_count"]))
    print("UNIQUE_CONTENT_GROUPS="+str(report["unique_content_groups"]))
    for group in RULES:
        count=sum(group in r["classes"] for r in report["matches"])
        print(group+"="+str(count))
    print("SCIENTIFIC_STATUS=INVENTORY_NOT_VALIDATED")
    print("PRIVATE_REPORT="+str(dest))
if __name__=="__main__":
    main()
