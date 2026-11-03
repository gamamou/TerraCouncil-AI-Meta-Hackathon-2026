"""Pronounce only simple underscore-separated alphabetical identifiers.

Keep original scientific text unchanged outside the oral render.
Reject identifiers containing numbers, repeated underscores or risky symbols.
"""
import re
from datetime import datetime
TOKEN=re.compile(r"(?<![\w])([A-Za-zÀ-ÿ]+(?:_[A-Za-zÀ-ÿ]+)+)(?![\w])")
ANY_UNDERSCORE=re.compile(r"\S*_\S*")
def normalize_identifiers(text):
    if not isinstance(text,str):raise ValueError("Invalid text")
    audit=[]
    def replace(m):
        original=m.group(1)
        parts=original.split("_")
        if not all(2<=len(p)<=40 for p in parts):
            raise ValueError("Ambiguous underscore identifier")
        spoken=" ".join(parts)
        audit.append({"original_sha_only":True,"spoken":"UNDERSCORE_AS_PAUSE","occurrences":1})
        return spoken
    from terra_french_numbers_001 import integer_words
    def timestamp(m):
        source=m.group(0)
        datepart,timepart=source.split("_")[:2]
        try: dt=datetime.strptime(datepart+timepart,"%Y%m%d%H%M%S")
        except ValueError: raise ValueError("Invalid UTC timestamp")
        months=("","janvier","février","mars","avril","mai","juin","juillet","août",
                "septembre","octobre","novembre","décembre")
        audit.append({"original_sha_only":True,"spoken":"UTC_TIMESTAMP","occurrences":1})
        return (integer_words(dt.day)+" "+months[dt.month]+" "+integer_words(dt.year)+
                ", "+integer_words(dt.hour)+" heures "+integer_words(dt.minute)+
                " minutes "+integer_words(dt.second)+" secondes, U T C")
    rendered=re.sub(r"(?<![\w])\d{8}_\d{6}_UTC(?![\w])",timestamp,text)
    rendered=TOKEN.sub(replace,rendered)
    if ANY_UNDERSCORE.search(rendered):
        raise ValueError("Unsafe technical identifier requires review")
    return rendered,audit
