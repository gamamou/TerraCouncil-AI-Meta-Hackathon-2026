# TerraCouncil — Technical architecture

This document describes the implementation protocol that was exercised in the locally tested prototype. Source-level references and exact module paths will be added after the final RC1 archive is imported and reviewed.

```text
Question (FR or EN)
       |
       v
Evidence/context admission gate
  - source and provenance
  - completeness / missing-domain flags
  - candidate vs admitted evidence
       |
       v
Meta: Spark initial analysis
       |
       v
Meta: Wonder critique
       |
       v
Meta: Spark revised analysis
       |
       v
Preserved trace + review metadata
       |
       +--> Scientific/report presentation --> PDF
       |
       +--> Faithful editorial dialogue
                |
                v
         Moderator-quality gates
                |
                v
           ElevenLabs TTS
                |
                v
            Audio segments
```

## Deliberation mechanics

The third call must receive preceding arguments and criticism; the workflow is not three independently scripted speakers. Recorded traces support inspection and recovery of completed phases after partial API failure. Call failures are not automatically retried because previously completed calls may incur cost.

## Demo and Live separation

- **Live:** accepts questions and uses runtime API calls.
- **Demo:** presents preserved, genuinely generated deliberations, not fabricated claims of live inference.
- Each language and pilot is associated with its own corresponding trace, output and media.
- Editorial narration may improve clarity but should not manufacture scientific facts or alter the agents' findings.

## Technical safeguards

- Explicit distinction between candidate material and scientifically admitted evidence.
- No automatic retries of failed paid model operations.
- Review/approval state must not be inferred from file existence.
- Audio publication checks and fingerprinting to prevent associating a stale audio file with a changed dialogue.
- Credentials provided through environment configuration, never committed.

## Known limits

The three showcased examples do not constitute a field-validation program. Scientific completeness, source licensing, reproducibility of a specific result, and deployment readiness each require separate verification. Exact implementation paths, tests and dependency lock files will be documented from the imported RC1 source.
