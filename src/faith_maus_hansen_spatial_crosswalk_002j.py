"""TERRA-DATA-002J — Geospatial identity crosswalk for existing MAUS/Hansen science.

Uses ORIGINAL MAUS v2 GeoPackage polygon geometry to locate the 128 existing
FSMI source FIDs relative to TerraCouncil's exploratory rectangle. Existing
Hansen/Dynamic World/JRC metrics are never recalculated or reattributed.
Requires local shapely; Python sqlite3 and csv are standard library.

This creates a *candidate screening report*, NOT a Council AOI observation.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
import struct
from pathlib import Path

BBOX=(-14.5,10.5,-14.0,11.0)
EXPECTED_CSV_ROWS=640
EXPECTED_FIDS=128
ZONES={"inside","0_1km","1_5km","5_10km","10_20km"}
MAX_GPKG=2_000_000_000

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def read_metrics(csv_path):
    with Path(csv_path).open("r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=EXPECTED_CSV_ROWS:
        raise ValueError("Unexpected source Hansen screening population")
    required={"maus_fid","zone","hansen_source","hansen_qa",
              "maus_to_permit","maus_to_company","causal_attribution"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Unexpected Hansen screening schema")
    indexed={}
    for row in rows:
        fid=row["maus_fid"]
        if not fid.isdecimal() or row["zone"] not in ZONES:
            raise ValueError("Invalid source FID or zone")
        pair=(fid,row["zone"])
        if pair in indexed:
            raise ValueError("Duplicate source FID-zone")
        if row["maus_to_permit"]!="UNVERIFIED" or row["maus_to_company"]!="UNVERIFIED":
            raise ValueError("Unsupported permit/company attribution in screening")
        if row["causal_attribution"]!="NOT_ESTABLISHED":
            raise ValueError("Unsupported causal attribution")
        indexed[pair]=row
    fids={fid for fid,zone in indexed}
    if len(fids)!=EXPECTED_FIDS or any({zone for f,zone in indexed if f==fid}!=ZONES for fid in fids):
        raise ValueError("Expected 128 source FIDs with five screening zones")
    return indexed,fids

def gpkg_wkb(blob):
    if not isinstance(blob,bytes) or len(blob)<9 or blob[:2]!=b"GP":
        raise ValueError("Invalid GeoPackage geometry header")
    flags=blob[3]
    envelope_code=(flags>>1)&7
    envelope_bytes={0:0,1:32,2:48,3:48,4:64}.get(envelope_code)
    if envelope_bytes is None:
        raise ValueError("Unsupported GeoPackage envelope code")
    offset=8+envelope_bytes
    if len(blob)<=offset:
        raise ValueError("Truncated GeoPackage geometry")
    return blob[offset:]

def crosswalk(gpkg_path, csv_path, expected_gpkg_sha=None):
    try:
        from shapely.geometry import box
        from shapely.wkb import loads
    except ImportError as e:
        raise RuntimeError("shapely is required for an exact polygon intersection") from e
    g=Path(gpkg_path)
    c=Path(csv_path)
    if not g.is_file() or g.is_symlink() or not c.is_file() or c.is_symlink():
        raise ValueError("Source file not found or symlink")
    if g.stat().st_size>MAX_GPKG:
        raise ValueError("Source GeoPackage unexpectedly large")
    metrics,fids=read_metrics(c)
    gdigest=file_sha(g)
    if expected_gpkg_sha and gdigest.lower()!=expected_gpkg_sha.lower():
        raise ValueError("Original GeoPackage SHA256 differs from declared reference")
    with sqlite3.connect("file:"+str(g.resolve())+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        result=db.execute("PRAGMA quick_check").fetchone()[0]
        if result!="ok":
            raise ValueError("GeoPackage SQLite integrity failed")
        source=db.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns").fetchall()
        if len(source)!=1 or int(source[0]["srs_id"])!=4326:
            raise ValueError("Expected one MAUS polygon feature table in EPSG:4326")
        table=source[0]["table_name"]
        geom=source[0]["column_name"]
        if not (table.replace("_","").isalnum() and geom.replace("_","").isalnum()):
            raise ValueError("Unexpected GeoPackage SQL identifiers")
        columns=db.execute('PRAGMA table_info("'+table+'")').fetchall()
        pks=[x["name"] for x in columns if x["pk"]==1]
        if len(pks)!=1 or not pks[0].replace("_","").isalnum():
            raise ValueError("No unique integer primary key")
        pk=pks[0]
        area=box(*BBOX)
        matches=[]
        found=set()
        by_fid={}
        source_ids=sorted(int(x) for x in fids)
        for start in range(0,len(source_ids),80):
            group=source_ids[start:start+80]
            clause=",".join("?" for _ in group)
            query=f'SELECT "{pk}" AS source_fid, "{geom}" AS shape FROM "{table}" WHERE "{pk}" IN ({clause})'
            for r in db.execute(query,group):
                fid=str(r["source_fid"])
                found.add(fid)
                shape=loads(gpkg_wkb(r["shape"]))
                if shape.is_empty or not shape.is_valid:
                    raise ValueError("Invalid original MAUS polygon geometry")
                intersects=shape.intersects(area)
                by_fid[fid]=intersects
                if intersects:
                    matches.append({"maus_fid":fid,
                        "zones_available":sorted(zone for x,zone in metrics if x==fid),
                        "relationship":"ORIGINAL_MAUS_POLYGON_INTERSECTS_EXPLORATORY_RECTANGLE",
                        "site_permit_attribution":"UNVERIFIED",
                        "hansen_values_interpretable_as_clipped_aoi":False})
    missing=sorted(fids-found,key=int)
    if missing:
        raise ValueError("MAUS fid missing from original global geometry source: "+",".join(missing[:6]))
    return {
      "schema_version":"TERRA_DATA_002J_SPATIAL_CROSSWALK",
      "source_geo_package_sha256":gdigest,
      "source_hansen_csv_sha256":file_sha(c),
      "source_crs":"EPSG:4326",
      "exploratory_rectangle_bbox":list(BBOX),
      "total_national_maus_screening_fids":len(fids),
      "full_source_fids_intersecting_rectangle":len(matches),
      "matching_source_fids":matches,
      "scientific_status":"GEOMETRY_SCREENED_NOT_HANSEN_AOI_CLIPPED",
      "council_evidence":[],
      "council_admission":"NONE",
      "not_established":[
        "Source-wide Hansen values do not become AOI-clipped values",
        "No validated MAUS to CPDM/Cheng/company identity",
        "No attribution of observed forest loss to mining",
        "A rectangle is not Boké administrative boundary",
        "Geospatial overlap does not establish source license or scientific authorization",
      ],
      "new_scientific_raster_calculations":0,"model_calls":0,"network_calls":0
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gpkg",required=True)
    p.add_argument("--hansen",required=True)
    p.add_argument("--expected-gpkg-sha")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    dest=Path(a.out)
    if dest.exists():
        raise ValueError("Existing screening report will not be overwritten")
    result=crosswalk(a.gpkg,a.hansen,a.expected_gpkg_sha)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k] for k in (
        "scientific_status","total_national_maus_screening_fids",
        "full_source_fids_intersecting_rectangle","council_admission",
        "model_calls","network_calls")},ensure_ascii=False,indent=2))
    print("PRIVATE_REPORT="+str(dest))

if __name__=="__main__":
    main()
