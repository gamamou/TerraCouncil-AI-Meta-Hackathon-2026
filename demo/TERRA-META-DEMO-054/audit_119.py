"""Offline jury-demo audit; no API calls and no changes to stored evidence/audio."""
from pathlib import Path
import json,sys

def main(root):
    root=Path(root).resolve()
    sys.path.insert(0,str(root))
    import pilot_115
    print('PILOT  LANG  PUBLIC AUDIO  SEGMENTS  MANIFEST')
    for pilot in ('BOKE','FLOOD','AGRO'):
        for lang in ('fr','en'):
            manifest=root/'pilot_audio_116b'/f'{pilot}-{lang}.json'
            try:segments=pilot_115.audio_segments(pilot,lang,root)
            except Exception as exc:
                print(f'{pilot:<6} {lang:<4} ERROR: {type(exc).__name__}');continue
            public='READY' if segments else 'NOT READY'
            saved='yes' if manifest.is_file() else 'no'
            print(f'{pilot:<6} {lang:<4} {public:<13} {len(segments):<8} {saved}')
    print('NOT READY can mean missing recording, obsolete moderator script or failed checksum.')
    print('No API calls or file changes made.')

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python audit_119.py <DEMO_ROOT>')
    main(sys.argv[1])
