# Reproducibility and evaluation protocol

## Current status

The finalized **59-file source snapshot** was built on Windows as `TERRA-META-GITHUB-SOURCE-RC1.zip` and reported zero issues in its packaging scan. That scan is **not** a complete security audit. The ZIP has not yet been imported into this GitHub repository.

Until the archive is inspected and committed, runnable steps and exact dependency versions cannot responsibly be claimed here.

## Evaluation workflow for reviewers

Once the final source is included:

1. Inspect the source inventory and dependency documentation.
2. Configure API credentials locally using `.env.example` (never commit real keys).
3. Launch the application following the source-verified instructions.
4. Navigate to Demo and Live modes, checking both French and English.
5. Review the three-stage Meta protocol: initial Spark, Wonder critique, revised Spark.
6. Verify that the source separates evidence provenance, model text, editorial dialogue and audio generation.
7. Evaluate abstention/unvalidated-evidence behaviors, trace preservation and no-blind-retry handling.
8. Compare generated outputs with their trace and integrity metadata where authorized.

## Reported local acceptance results — November 3, 2026

| Pilot | FR audio | EN audio | FR PDF | EN PDF |
|---|---|---|---|---|
| Boké mining | Ready | Ready | Present | Present |
| Flood risk | Ready | Ready | Present | Present |
| Agriculture | Ready | Ready | Present | Present |

All audio variants and PDF reports were manually checked by the developer in the local runtime. These results are historical test reports, not evidence that the public GitHub checkout contains media or API credentials.

## Reproducibility boundaries

- A recorded Demo is reproducible for playback **only if corresponding authorized media assets are provisioned**.
- Live inference is subject to model/API access, cost, stochasticity and provider availability.
- Scientific input datasets, local provenance logs and private model traces are withheld from the source distribution.
- Evidence admission is not equivalent to field validation.

## Before submission

The final RC1 ZIP must be reviewed against `SOURCE_INVENTORY.json`, dependencies and potential leakage of absolute paths, tokens and sensitive input data.
