"""Prepare audio review materials for the latest completed local session.
No external API calls.
"""
import argparse
import json
from pathlib import Path
from natural_french_dialogue import oral_storyboard, write_review_files
from chamber_visuals import visual_cues

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True)
    p.add_argument("--session",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
    session=json.loads(Path(a.session).read_text(encoding="utf-8"))
    visuals=visual_cues(session,evidence)
    oral=oral_storyboard(session,evidence)
    folder=Path(a.out)
    folder.mkdir(parents=True,exist_ok=True)
    visual_path=folder/("HACK013-"+oral["session_id"]+"-visual.json")
    if visual_path.exists():
        raise ValueError("Visual file already exists")
    visual_path.write_text(json.dumps(visuals,ensure_ascii=False,indent=2),encoding="utf-8")
    draft,text=write_review_files(oral,folder)
    print("STATUS: REVIEW_READY")
    print("META_CALLS: 0")
    print("TTS_CALLS: 0")
    print("VISUAL:",visual_path)
    print("DRAFT:",draft)
    print("TEXT:",text)
if __name__=="__main__":
    main()
