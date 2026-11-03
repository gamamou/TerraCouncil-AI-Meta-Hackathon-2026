# Reviewer guide — mapping technical claims to reviewed source

The following files and responsibilities were verified against the uploaded RC1 ZIP. These source paths are **pending import** at the time this guide was created.

| Capability | Actual source files | What to inspect |
|---|---|---|
| Meta chat-completions integration | `src/council.py` | `meta_call`, provider request structure, HTTP error handling |
| Evidence admissions and fingerprints | `src/council.py`, `src/verification.py`, `src/verified_council.py` | admissible-only selection, gate outcomes, hash logic |
| Interactive local scientific council | `src/local_council_server.py` | localhost server, consent control, durable checkpoints |
| Autonomous action planner | `src/terra_meta_013a_agent_loop.py`, `src/terra_meta_013b_muse_runtime.py`, `src/terra_meta_013c_adaptive_council.py` | constrained tools, source-fidelity safeguards |
| Context and spatial evidence | `src/faith_scientific_evidence_bridge_002.py`, `src/faith_maus_hansen_spatial_crosswalk_002j.py`, `src/faith_chirps_aoi_guard_002i.py` | geospatial/source screening and uncertainty |
| Deliberation, narration and oral QC | `src/dynamic_council.py`, `src/dynamic_narration.py`, `src/dynamic_oral_audit.py`, `src/natural_french_dialogue.py` | debate construction, oral constraints |
| PDF decision products | `src/elegant_decision_pdf.py`, `src/export_decision_pdf.py`, `src/executive_brief_v3.py` | formatting, trace-linked decision communication |
| Audio workflow | `src/dynamic_voice_workflow.py`, `src/voice_workflow.py`, `src/render_session_audio.py` | voice assignment and output verification |

The final application controller, Demo-specific navigation and audio-policy-119 modules reside in the developer's validated `TERRA-META-DEMO-054` directory and must be imported separately. Do not confuse foundational modules with the final deployed user experience.

## Important limitations

The ZIP provides auditable code, not a complete deployed environment or scientific-field-validation certificate. Run-time behavior should be demonstrated in the submission video and tested in the provisioned private environment, with credentials kept out of screen captures.
