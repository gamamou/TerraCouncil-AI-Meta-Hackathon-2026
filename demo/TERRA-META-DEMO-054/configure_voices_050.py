"""Safe voice configuration check. Does not print keys or call APIs."""
import os
keys=["ELEVENLABS_API_KEY","ELEVENLABS_SPARK_VOICE_ID","ELEVENLABS_WONDER_VOICE_ID","ELEVENLABS_MODERATOR_VOICE_ID"]
for k in keys:print(k, "CONFIGURED" if os.environ.get(k) else "MISSING")
a,b=os.getenv("ELEVENLABS_MODERATOR_VOICE_ID"),os.getenv("ELEVENLABS_WONDER_VOICE_ID")
if a and b and a==b:print("WARNING: Moderator and Wonder share a voice. To obtain three vocal identities, choose a distinct moderator voice and regenerate the two sessions.")
else:print("No moderator/Wonder voice-ID duplication detected.")
