# wildtag: fixing the validation write/read bottleneck (design sketch)

## The root problem (named precisely)

`results_with_ids.csv` mixes two kinds of data with opposite access patterns:

- **Detection record** (immutable after a run): image_id, detection_id, paths,
  datetime, bbox, `label`, `confidence`, locationName. ~480k rows, 197 MB.
  Changes only when you re-run the pipeline.
- **Validation state** (frequently updated, tiny): per detection_id,
  `validated` + `correct_label`. Hundreds to a few thousand rows.

Because they share one file, changing a few validation cells forces a rewrite of
all 480k rows. That is the entire cause of: the slow saves, the unreliable
background merge, the slow summary, and the truncation class of bug.

## The fix (one sentence)

Keep `results_with_ids.csv` as the immutable **detection record**, move
**validation state** into a tiny SQLite database that both local validation and
collect write to, and **derive** the combined `results_with_ids.csv` on demand.
Validation becomes instant; the big file is only written when you export.

## New data model

- `results_with_ids.csv` - unchanged in content and location. Still produced by
  `enrich_csv` from `results.csv`. **Never rewritten by validation.** All
  existing readers of detection columns keep working as-is.
- `validation.db` (SQLite, in the project folder) - the live source of truth for
  validation:

```sql
CREATE TABLE validations (
    detection_id  TEXT PRIMARY KEY,
    label         TEXT,     -- predicted label (denormalised, for the matrix)
    correct_label TEXT,     -- correction; '' if confirmed as predicted
    validated     INTEGER DEFAULT 1,
    source        TEXT,     -- 'local' or 'volunteer'
    updated_at    TEXT
);
CREATE INDEX idx_val ON validations(validated);
```

`sqlite3` is in the Python standard library - no new dependency.

## Every current dependency, and how it's respected + sped up

| Current use of results_with_ids.csv | Reads/Writes | New design | Speed |
|---|---|---|---|
| `enrich_csv` creates it from results.csv | Write (create) | Unchanged - it's the detection record | same |
| `_val_merge_to_master` (validate → master) | Read+Write 197 MB | Replaced by `INSERT OR REPLACE` of the changed rows into `validation.db` | ms |
| Collect merges returns | Read+Write 197 MB | Same `INSERT OR REPLACE` into `validation.db` (source='volunteer') | ms |
| Summary counts (n_validated, n_corrected) | Read 197 MB | `SELECT COUNT(*)` queries on the db | ms |
| Confusion matrix (cm_all, cm_errors) | Read 197 MB | `GROUP BY label, correct_label` on the db | ms |
| Map + species totals (site_species, n_rows) | Read 197 MB | From the detection record, **cached once per run** (mtime key); corrections overlaid from the db (small set) | one-time, then instant |
| Sibling bbox drawing | Read (detection cols) | Unchanged - reads detection record | same |
| Volunteer package bake (subset into zip) | Read (detection cols) | Unchanged - reads detection record | same |
| Downstream/external tools reading the CSV | Read | Still get a real `results_with_ids.csv` via **on-demand export** (below) | explicit |

Key point: **nothing rewrites 197 MB on a validation click, ever.** The only
480k-row write is the explicit export.

## Read paths (summary / matrix / map)

- **Validation aggregates** (validated count, corrections, confusion matrix):
  pure SQL on `validation.db`. Instant, always current, independent of project
  size. Because `label` is stored in the db, the matrix is a single GROUP BY
  with no join to the big file.
- **Detection aggregates** (total detections, species totals, per-site counts):
  computed once from the detection record and cached on its mtime. The detection
  record only changes on a new run, so this cache effectively never rebuilds
  during validation.
- **Map corrected labels**: start from the cached detection site-species counts,
  then apply the db's corrections as a small overlay (decrement predicted,
  increment corrected). Cheap because corrections are few.

## Write paths (local validation / collect)

- "Mark batch complete" → `INSERT OR REPLACE` the batch's detection_ids into
  `validation.db`. Instant, synchronous, reliable. No background thread, no hack,
  no truncation risk. The stall and the unreliability both disappear because the
  write is tiny.
- Collect → same, tagged `source='volunteer'`. Local + volunteer validation
  accumulate in one durable store, exactly the single accumulation point you
  described.

## results_with_ids.csv regeneration (the derived export)

- An explicit **"Export results (CSV)"** action (and/or on project close):
  stream the detection record, look up each detection_id in the db (loaded once
  into a dict), fill `validated`/`correct_label`, write the combined CSV
  atomically (temp + os.replace). This is the same join as today's merge, but it
  runs only when you ask, not on every edit.
- If you want the CSV kept continuously current for an external watcher, the
  export can also run in the background after a sync - but it is never on the
  critical path of validating.

## Backwards compatibility (your big project)

On first open of an existing project with the new build, a one-time automatic
migration (non-destructive, `results_with_ids.csv` untouched):

1. If `validation.db` doesn't exist, create it.
2. Import existing validation state into it, keyed by detection_id, from BOTH:
   - the `validated`/`correct_label` columns already in `results_with_ids.csv`
     (your collected volunteer returns), and
   - every `validation.csv` in the `validation\` folders (your local work).
   `INSERT OR REPLACE` means duplicates collapse to one row; the folder copy
   (freshest) wins ties.
3. From then on, the db is the live store; the CSV is the detection record +
   on-demand export.

This captures everything you have already done - collected returns and the local
sheep validations - into the fast store, with nothing lost and the big CSV left
exactly as it is.

## What changes in code (scope)

- New small module/helpers: open db, `upsert_validations(rows)`,
  `validation_stats()` (counts + matrix), `corrections_overlay()` (for the map),
  `export_combined_csv()`, `migrate_if_needed()`.
- `_val_complete_batch`: replace the master merge with a db upsert of the batch.
- `_dist_collect`: replace the master merge with a db upsert of the returns.
- `_get_aggregates`: split into cached detection aggregates + live db validation
  aggregates.
- `_val_merge_to_master` / `_val_sync_to_master`: become `export_combined_csv`
  (explicit), not per-edit.
- Add "Export results (CSV)" button; keep migration automatic on open.

## Safety / rollout

- Migration is additive; the existing CSV is never modified by it.
- The export write is atomic (temp + os.replace) - the truncation bug cannot
  recur even on the one big write that remains.
- Because the db is separate, even a crash mid-export leaves validation state
  intact in the db.

## Decisions (as built)

1. `results_with_ids.csv` is regenerated **on demand** via an "Export results"
   button at the top of the Summary pane, and **automatically on a clean close**
   (with a "Saving results" message). Nothing watches the file live, so it is
   not continuously regenerated.
2. On project open, wildtag runs a one-time migration (first open) and then a
   **staleness check**: if the store has validations newer than the last export,
   it offers to export. This covers hard-close/crash cases.
3. One `validation.db` (SQLite) per project folder, alongside
   `results_with_ids.csv`.
4. All writes to the results file are atomic (temp + os.replace), and the export
   surfaces a clear message if the file is locked (e.g. open in Excel).
