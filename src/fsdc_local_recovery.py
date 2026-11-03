"""FSDC-RECOVERY-001 — local-only inventory of pre-existing FAITH science.

Scans explicitly selected local roots for plausible OSM, dust/AERMOD,
TerraCouncil 010HI/J and FEI/CHIRPS artifacts. Never reads values,
imports measurements, calls providers, or uploads data.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re

PATTERNS={
 "TERRA_SCIENTIFIC_QA":re.compile(r"010h[i-j]|spatial.qa|evidence.json|screened.evidence",re.I),
 "OSM_GEOMETRY":re.compile(r"osm|overpass|buildings|road|rail|waterway|boke.*(agric|mine)|mining.tiles",re.I),
 "DUST_AERMOD":re.compile(r"aermod|pm10|pm2[._-]?5|dust|poussi|dispersion|receptor|emission",re.I),
 "CLIMATE_WATER":re.compile(r"chirps|era5|hydrolog|flood|water.climate|rainfall",re.I),
 "FSDC_MANIFEST":re.compile(r"scientific.integration.manifest|fsdc.*manifest|dataset.registry|data.readiness",re.I)
}
EXTENSIONS={".json",".geojson",".gpkg",".shp",".dbf",".shx",".prj",".tif",".tiff",
 ".csv",".parquet",".feather",".nc",".grib",".zip",".yaml",".yml",".txt",".md"}
OMIT={"node_modules",".git",".venv","venv","site-packages","__pycache__",".next",
      "AppData","Microsoft","Windows","Temp","Cache"}
MAX_FILES=60000
SMALL_HASH=25*1024*1024

def role(name):
    return [category for category,pattern in PATTERNS.items() if pattern.search(name)]

def inventory(roots,limit=MAX_FILES,with_paths=True):
    found=[];visited=0;errors=[]
    for root in roots:
        base=Path(root).expanduser()
        if not base.is_dir():
            errors.append({"root":str(base),"error":"ROOT_NOT_FOUND"})
            continue
        for dirpath,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=[d for d in dirs if d not in OMIT and not (Path(dirpath)/d).is_symlink()]
            for name in files:
                visited+=1
                if visited>limit:
                    errors.append({"root":str(base),"error":"MAX_FILES_REACHED"})
                    break
                categories=role(name)
                if not categories:continue
                f=Path(dirpath)/name
                if f.suffix.lower() not in EXTENSIONS or f.is_symlink():continue
                try:
                    stat=f.stat()
                    entry={"filename":name,"categories":categories,
                           "extension":f.suffix.lower(),"size_bytes":stat.st_size,
                           "modified_utc":dt.datetime.fromtimestamp(stat.st_mtime,dt.timezone.utc).isoformat(),
                           "sha256":None,"hash_status":"DEFERRED_LARGE_FILE"}
                    if with_paths:entry["path"]=str(f.resolve())
                    if stat.st_size<=SMALL_HASH:
                        hasher=hashlib.sha256()
                        with f.open("rb") as stream:
                            for chunk in iter(lambda:stream.read(1024*1024),b""):
                                hasher.update(chunk)
                        entry["sha256"]=hasher.hexdigest()
                        entry["hash_status"]="HASHED"
                    found.append(entry)
                except (OSError,PermissionError) as error:
                    errors.append({"filename":name,"error":type(error).__name__})
            if visited>limit:break
    by_category={c:sum(c in item["categories"] for item in found) for c in PATTERNS}
    return {"schema_version":"FSDC_RECOVERY_001",
            "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "local_only":True,"no_upload":True,"no_data_values_read":True,
            "files_inspected":visited,"matched_count":len(found),
            "categories":by_category,"matches":found,"errors":errors,
            "scientific_readiness":"NOT_ASSESSED_METADATA_ONLY",
            "warning":"Matching filenames are candidates, NOT verified scientific evidence. Review licenses, structure, CRS, AOI, units, provenance and QA before integration."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",action="append",required=True,help="Explicit local folder (repeatable)")
    parser.add_argument("--out",required=True,help="Private output JSON location, outside public repository")
    parser.add_argument("--max-files",type=int,default=MAX_FILES)
    args=parser.parse_args()
    if not 1<=args.max_files<=MAX_FILES:parser.error("Invalid max-files")
    target=Path(args.out).expanduser()
    target.parent.mkdir(parents=True,exist_ok=True)
    payload=inventory(args.root,args.max_files)
    if target.exists():
        parser.error("Output exists; choose a new filename to preserve prior inventories")
    with target.open("x",encoding="utf-8") as handle:
        json.dump(payload,handle,ensure_ascii=False,indent=2)
    print("FSDC_SCAN_FILES="+str(payload["files_inspected"]))
    print("MATCHES="+str(payload["matched_count"]))
    for category,count in payload["categories"].items():print(category+"="+str(count))
    print("SCIENTIFIC_READY=NOT_ASSESSED")
    print("NO_EXTERNAL_CALLS; NO_SOURCE_MODIFICATIONS; PRIVATE_OUT="+str(target))

if __name__=="__main__":
    main()
