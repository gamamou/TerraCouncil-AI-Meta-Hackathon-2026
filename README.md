# TerraCouncil AI — Meta Hackathon 2026

**SustainAfrica | FAITH — Future Africa Innovation & Transformation Hub**

## Why TerraCouncil?

Decisions about mining, agricultural production and climate hazards require reconciling fragmented scientific evidence, conflicting priorities and uncertainty. TerraCouncil is a bilingual multi-agent decision-support prototype that makes scientific argument and critique inspectable.

## Real three-stage Meta reasoning

1. **FSDC evidence context:** question, inputs, provenance and missing-evidence flags.
2. **Spark initial position:** genuine Meta model call.
3. **Wonder critique:** genuine Meta model call challenges assumptions and analyzes alternatives.
4. **Spark revision:** genuine Meta model call incorporates criticism.
5. **Outputs:** preserved trace, human-readable report and moderated multi-voice presentation.

The locally tested model sequence was `muse-spark-1.3` → `muse-wonder-1.0` → `muse-spark-1.3`. Model access and versions depend on the provider.

**Demo** plays back authentic previously recorded reasoning with its saved outputs. **Live** initiates fresh inference. Demo playback must not be misrepresented as a live API call.

## Three bilingual demonstrations

| Domain | Pilot | FR / EN |
|---|---|---|
| Sustainable mining | Boké, Guinea | Both |
| Flood risk | Guinea | Both |
| Climate-smart agriculture | Guinea | Both |

The November 3 local acceptance test confirmed 6/6 audio variants (two segments each) and 6/6 PDF reports. Recorded media, private scientific traces, local datasets and credentials are not included in the public source snapshot.

## Scientific integrity

This is a scientific *decision-support* prototype, not certified environmental or engineering advice. Candidate data and background sources must not be presented as scientifically admitted or field-validated observations. Model outputs require independent review before consequential use.

## Technical documentation

- [Architecture and deliberation pipeline](docs/ARCHITECTURE.md)
- [Reproducibility and acceptance protocol](docs/REPRODUCIBILITY.md)
- [Security and responsible handling](SECURITY.md)

## Running the source

The **final RC1 source** has now been imported to `src/` and `demo/TERRA-META-DEMO-054/`. The local application was acceptance-tested on Windows using:

```powershell
$repo = "$HOME\\Documents\\TerraCouncil-Workspace\\Application\\TerraCouncil-Meta-Hackathon"
$demo = Join-Path $repo "data\\science_packages\\TERRA-META-DEMO-054"
Set-Location $demo
python -X utf8 server.py
```

This is the **developer's validated local workspace**, not a promise that the public GitHub checkout is self-contained. The GitHub source uses `demo/TERRA-META-DEMO-054/` and `src/`; the private scientific inputs, recorded media, provider API keys and data paths are not included. A first-time clone may need environment setup and source-path configuration before it can run.

The `requirements.txt` file records third-party Python imports detected in the foundational source; it is not an exhaustive, pinned dependency lockfile. The CI workflow performs offline syntax checks rather than external-service integration tests.

See [Implementation map](docs/IMPLEMENTATION_MAP.md) and [Source review](docs/SOURCE_REVIEW.md).

## Attribution

An original SustainAfrica/FAITH prototype developed for the Meta Hackathon Startup Track. Meta provides the reasoning models; ElevenLabs provides voice synthesis. Their APIs and services are not part of the source release.

**Release label:** `TERRA-META-SUBMISSION-2026-11-03-RC1` (local build validated; GitHub source imported, private runtime assets excluded).
