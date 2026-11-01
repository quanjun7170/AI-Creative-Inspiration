# Multimodal research prototype

This prototype turns a research brief into candidate artifact and comment dimensions,
compiles those dimensions into source-specific coding prompts and runnable scripts,
and links the resulting ratings for exploratory analysis. Video, music, images and
writing are supported by the plan compiler. The same conceptual name across media
does not establish measurement invariance.

## What works now

- AI dimension proposal adapter using Gemini or OpenAI structured JSON output.
- Local plan validation, version hashing, prompt/schema compilation and script generation.
- Independent comment and artifact coding adapters, explicit execution flag, conservative
  media-size limit, stable IDs, cached completed responses and source-content hashes.
- Many-to-one ID linking, explicit failed-record filtering, preservation of missing ratings,
  descriptive distributions and floor frequencies.
- Equal-weight post-level correspondence with artifact bootstrap confidence intervals.
- Exploratory within-artifact fixed effects and between-artifact aggregate regressions.
- A demonstration using only the historical final Study 1 sample and existing ratings.

The adapters have not been tested against live paid API calls in this release. The four
example codebooks were authored by the assistant as candidate examples; they are not
outputs from an executed API proposal request or validated scales. The historical Study 1
ratings were not produced using these new candidate prompts. No video generation,
human validation, automatic literature retrieval, or causal identification is claimed.

## Setup

Use Python 3.10 or later and `pip install -r requirements.txt`. Set API keys in local
environment variables only: `GEMINI_API_KEY` or `OPENAI_API_KEY`. Supply an explicit model
ID available to your account. Gemini handles non-text media in this version; OpenAI
handles dimension proposals and text-only coding. No API request is made by default.

Run these commands from this directory:

```console
python pipeline.py propose --brief examples/music_brief.json --out private_runs/music_design
```

This writes a prompt and schema without making a request. To ask AI to propose a new plan:

```console
python pipeline.py propose --brief examples/music_brief.json --out private_runs/music_design --provider gemini --model YOUR_MODEL_ID --execute
python pipeline.py compile --plan private_runs/music_design/candidate_plan.json --out compiled/music_new
```

Inspect definitions, anchors, construct overlap and source relevance before collecting
confirmatory data. Citations are restricted to evidence supplied in the brief and remain
unverified until checked. Compilation records a plan hash and never executes AI-written
code. Generated scripts are fixed wrappers around the tested engine.

## Input contracts and coding

Comment input CSV: `comment_id,artifact_id,text`.
Artifact input CSV: `artifact_id,path` for local video/audio/image files; or
`artifact_id,text` for writing. Media paths resolve relative to the input CSV.
The inline adapter accepts at most 15 MB per artifact. Large-file upload, URL download,
GIF conversion and agentic temporal exploration are not implemented in this prototype.
Video sampling follows provider defaults; the prototype does not guarantee access to
every frame. Use a model that supports the requested input modality and structured output.

```console
python compiled/music_new/code_artifacts.py --input artifacts.csv --out private_runs/music_artifacts --provider gemini --model YOUR_MODEL_ID --limit 20
python compiled/music_new/code_comments.py --input comments.csv --out private_runs/music_comments --provider openai --model YOUR_MODEL_ID --limit 20
```

Add `--execute` to make calls. Raise `--limit` explicitly for a larger batch. Requests are
sequential and stop on errors. Completed records can be resumed; changed inputs or plan
versions require a new run directory. Errors are retained as errors, never minimum ratings.
API charges and account availability depend on the chosen provider and model.

## Analysis

Analysis inputs are `ratings.csv` exports with an explicit `status` column. Artifact IDs
must be unique in artifact data; comment IDs must be unique in comment data. Unmatched
parents and ambiguous columns raise errors. Non-ok records are excluded with counts.
Missing scores stay missing; -999 is accepted as an import missing code.

```console
python compiled/music_new/analyze.py --comments private_runs/music_comments/ratings.csv --artifacts private_runs/music_artifacts/ratings.csv --out results/music_new --bootstrap 2000
```

Within regressions center variables within artifacts using complete cases for each model.
Between regressions use observed post means and equal artifact weights. All reported
slopes are unstandardized. These are exploratory regressions, not a joint multilevel SEM,
not mediation tests, and not evidence of coding validity. No automatic path selection or
significance search is performed. Cross-modal correlations are computed at artifact level,
with pairwise complete data and no multiplicity adjustment. Aggregation reliability and
cross-domain invariance require separate evaluation.

## Reproduce the existing-data demonstration

```console
python compiled/video/analyze.py --comments examples/study1_final_sample/comments.csv --artifacts examples/study1_final_sample/artifacts.csv --out results/study1_demo --bootstrap 2000
python -m unittest test_pipeline -v
```

The demonstration includes 13,598 comments in 1,191 posts, selected by the historical
Mplus eligibility and exogenous-variable completeness rules. Only final-sample comment
text is included. No authors or excluded comments are included. The sample files retain
different missingness patterns across outcomes. The original Mplus input and output are
in `study1_reference`; its numeric input includes only final-sample rows. The original
input variable list is reduced to the retained analysis columns and the already applied
selection filter is removed. The original output was produced using the full input before filtering, so its exclusion count will
differ if the final-sample-only input is rerun. Candidate definitions are not replacements
for the historical prompts. The technical appendix describes historical coding separately.

## Documentation sources

- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini video input: https://ai.google.dev/gemini-api/docs/video-understanding
- OpenAI structured output: https://developers.openai.com/api/docs/guides/structured-outputs

Structured JSON constrains formatting, not construct validity. No credentials or real
API response logs are included in this release. Keep new raw runs in `private_runs`.
