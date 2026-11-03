"""TERRA-META-DEMO-001: read-only FAITH snapshot gateway.
No scientific matching, scoring, or intervention selection is performed in Python.
Local snapshots are never uploaded by this module.
"""
import json
from pathlib import Path

TABLES={"PilotCandidate","MiningPermit","PermitSpatialContext",
        "SiteRehabilitationRecommendation","RehabilitationSolution"}
FIELDS={
 "PilotCandidate":("shape_uid","permit_record_key","score_0_100","priority_class_v2",
                   "selection_reason","pilot_category","status","snapshot_id"),
 "MiningPermit":("shape_uid","permit_record_key","score_0_100","national_rank",
                 "has_observed_footprint","footprint_pct_of_permit","confidence_level",
                 "evidence_level","field_validation_priority","cadastral_area_km2","substance","region",
                 "prefecture","administrative_status","evidence_weight","snapshot_id"),
 "PermitSpatialContext":("shape_uid","permit_record_key","rivers_within_radius_count",
       "river_intersection_count","nearest_distance_m","nearest_mapped_school_distance_m",
       "mapped_school_count_5km","estimated_population_5km_people","evidence_decision",
       "interpretation_boundary","snapshot_id"),
 "SiteRehabilitationRecommendation":("shape_uid","permit_record_key","diagnostic_summary",
       "identified_degradations","data_gaps","field_validation_required",
       "recommendation_status","snapshot_id"),
 "RehabilitationSolution":("solution_id","solution_name","degradation_types",
       "mining_contexts","technical_description","limitations","prerequisites",
       "required_field_validation","source_references","solution_status")
}
def load(path):
 raw=json.loads(Path(path).read_text(encoding="utf-8-sig"))
 if not isinstance(raw,dict):raise ValueError("Expected an object keyed by FAITH entity name")
 for name,rows in raw.items():
  if name not in TABLES or not isinstance(rows,list):raise ValueError("Unsupported entity: "+str(name))
  if len(rows)>25000 or any(not isinstance(row,dict) for row in rows):
   raise ValueError("Invalid records in "+name)
 return raw

class Gateway:
 def __init__(self,data):
  self.data=data
 def discover_faith_data(self):
  return [{"entity":name,"available_records":len(self.data.get(name,[])),
           "available_fields":list(FIELDS[name])} for name in sorted(TABLES)]
 def query_faith_data(self,entity,limit=50):
  if entity not in TABLES:raise ValueError("Entity not permitted")
  if not isinstance(limit,int) or not 1<=limit<=100:raise ValueError("Invalid limit")
  return [self._clean(entity,row) for row in self.data.get(entity,[])[:limit]]
 def get_faith_record(self,entity,identifier):
  if entity not in TABLES:raise ValueError("Entity not permitted")
  if not isinstance(identifier,str) or not identifier:raise ValueError("Invalid identifier")
  keys=("shape_uid","permit_record_key") if entity!="RehabilitationSolution" else ("solution_id",)
  return [self._clean(entity,row) for row in self.data.get(entity,[])
          if any(row.get(key)==identifier for key in keys)][:20]
 @staticmethod
 def _clean(entity,row):
  return {key:row.get(key) for key in FIELDS[entity] if key in row}

def invoke(gateway,action):
 tool=action.get("tool")
 if tool=="discover_faith_data":return gateway.discover_faith_data()
 if tool=="query_faith_data":return gateway.query_faith_data(action["entity"],action.get("limit",50))
 if tool=="get_faith_record":return gateway.get_faith_record(action["entity"],action["identifier"])
 raise ValueError("Unknown FAITH tool")
