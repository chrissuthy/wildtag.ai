# Developing wildtag.ai — Git workflow

A guide for anyone working on wildtag.ai's codebase alongside the project
lead. The goal is simple: never be unsure which version of a file is
current, and never lose working code.

## What's in the repo

Tracked (source code and small config/reference files):

- `wildtag.py`, `engine.py`, `registry.py` — the application
- `wt_models/*.py` — model runner source (not the weight files themselves)
- `wildtag_project_brief.md` — project overview and architecture notes
- All `.bat` scripts (`wildtag.bat`, `setup_gpu.bat`, `setup_validate_env.bat`,
  `build_dist.bat`, `fix_shebangs.bat`) and `fix_shebangs.py`
- `deployment_template.csv`, `README.txt`, `wildtag.ico`

**Not tracked** (see `.gitignore`): `wildtag_env/`, `validate_env/`,
`models/`, model weight files, build output (`wildtag_dist/`, `*.zip`),
`__pycache__/`, and `wildtag_settings.json` (this is machine-specific runtime
state, not part of the app).

If a task genuinely requires adding something to `.gitignore` or removing
something from it, raise it with the project lead first rather than editing
it unilaterally, it's easy to accidentally start tracking something huge.

## Before you start any change

1. **Pull latest**: `git pull` (or RStudio's Git pane → Pull), always work
   from the current state of `main`, not a copy you had lying around from
   last week.
2. If you're picking up a task that touches GPU install logic, the
   distribution/packaging code, or anything in `setup_*.bat`, skim
   `wildtag_project_brief.md` first, several of these areas have had subtle,
   non-obvious bugs (baked absolute paths, missing Tcl/Tk, mismatched
   launcher paths) that are easy to reintroduce if you're not aware of them.

## Making a change

1. Create a branch for anything non-trivial:
   ```
   git checkout -b fix/short-description
   ```
   For small, obviously-safe changes on a small team, committing directly to
   `main` is fine too, use judgement.
2. Make your change. Keep commits reasonably small and focused, one logical
   change per commit rather than one giant commit at the end of a session.
3. **Test before committing.** For anything touching `wildtag.py`, at
   minimum run it and exercise the tab(s) you changed. For anything touching
   the `.bat` scripts, actually run them, batch script bugs are easy to
   write and easy to miss just from reading.
4. Write a commit message that says *what* changed and, briefly, *why*:
   ```
   git commit -m "Fix GPU install loop: verify CUDA after install instead of trusting pip's exit code"
   ```
   not just `"fix bug"` or `"updates"`.

## Merging back

- If you used a branch: open a pull request against `main`, even a
  self-reviewed one is useful, it gives a clear record of what changed and
  why, and a natural point to double check `.gitignore` hasn't picked up
  anything it shouldn't.
- Resolve conflicts locally before merging, don't force-push over someone
  else's work.

## Release tagging

Every time `build_dist.bat` is run to produce a real distribution zip
(`wildtag_beta*.zip`), the commit used to build it gets tagged to match:

```
git tag beta4
git push --tags
```

This means "what code produced this zip" always has an exact, permanent
answer, check this before assuming a bug report is about the current code.

## A note on stale copies

Several bugs this project has hit came from editing an out-of-date copy of
`wildtag.py` (from a chat's project knowledge, an old backup, a zip someone
had sitting around) and it getting mistaken for the current version. Rules
of thumb to avoid repeating this:

- Always `git pull` before starting work, and check `git log` if anything
  about the current state seems surprising.
- Never hand-merge two versions of a file from memory, if two people (or
  two sessions) touched the same file, use Git's actual diff/merge tooling
  to reconcile them properly.
- If you're ever handed a file outside of Git (e.g. in a chat), diff it
  against what's currently in the repo before assuming it's the same or
  newer.
