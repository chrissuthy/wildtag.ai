# Setting up wildtag.ai on Git

A one-time setup guide for getting the wildtag.ai working folder under proper
version control, using Git through RStudio.

## Why this matters

This project has hit the same problem three times in one session: not being
sure which copy of `wildtag.py` was actually the current one, and losing
finished work by overwriting it with a stale copy. Git solves this
permanently: every change is recorded, nothing is ever silently lost, and
"what's the current version" always has a definite answer.

## Part 1 — Clean up the working folder first

Before anything goes into Git, get the folder itself into one unambiguous
state.

1. **Pick one canonical folder.** Archive any backup snapshots
   (e.g. `wildtag.ai_260707`) somewhere outside your active dev folder,
   an external drive or a separate archive location, not sitting alongside
   the live folder.
2. **Clear out build debris**: old `wildtag_dist\`, superseded
   `wildtag_beta*.zip` files (keep the most recent one or two, archive the
   rest), stray `__pycache__\` folders, leftover `tcltk_extract\` or
   `python_embed.zip` if any cleanup step ever left them behind.
3. **Check for duplicate or ambiguously-named source files.** There should
   be exactly one `wildtag.py` in the folder, delete any
   `wildtag_v2.py`-style backups once you've confirmed the real one is
   correct and working.

## Part 2 — Install Git

If not already installed: download and install **Git for Windows** from
[git-scm.com](https://git-scm.com/download/win). Accept the defaults during
install.

## Part 3 — Turn the folder into a Git project in RStudio

1. In RStudio: **File → New Project → Existing Directory**, then browse to
   your `wildtag.ai\` working folder.
2. This drops a small `.Rproj` file in the folder and, once Git is
   installed, RStudio will show a **Git** tab in the top-right pane.
3. If the Git tab doesn't appear, check **Tools → Global Options → Git/SVN**
   and confirm the Git executable path is set correctly, then reopen the
   project.

## Part 4 — Create `.gitignore`

Before the first commit, create a plain text file named `.gitignore` in the
project root (RStudio's file pane, or Terminal tab, works fine) containing:

```
wildtag_env/
validate_env/
models/
wt_models/*.pt
wt_models/*.onnx
wt_models/*.pth
wildtag_dist/
*.zip
__pycache__/
*.pyc
wildtag_settings.json
.Rproj.user/
```

Adjust the model-weight extensions to whatever your actual weight files use.
This keeps multi-gigabyte binaries (the Python environments, model weights,
build output) out of Git entirely, they don't diff meaningfully and would
make every clone of the repo drag that weight around forever.

**What does get tracked**: `wildtag.py`, `engine.py`, `registry.py`,
`wildtag_project_brief.md`, every `.bat` script, `fix_shebangs.py`,
`deployment_template.csv`, `README.txt`, `wildtag.ico`, and the `.py` source
files under `wt_models\` (just not the weight files themselves).

## Part 5 — First commit

1. In the RStudio Git pane, you'll see every tracked-worthy file listed as
   untracked (a yellow `?`).
2. **Before checking anything, look at the full file list carefully.** This
   is the moment to catch anything that shouldn't be there, a stray large
   folder, an accidentally-included folder of real camera trap images with
   site location data, etc. Much easier to fix now than after it's
   permanently in history.
3. Tick the checkboxes to stage everything that should be tracked, or use
   "Stage All" if the `.gitignore` above is already excluding the right
   things.
4. Click **Commit**, write a message like `Initial commit: wildtag.ai
   baseline`, and commit.

## Part 6 — Push to a private remote

1. Create a **private** repository on GitHub or GitLab (private matters
   here, deployment metadata and similar may be sensitive).
2. Follow GitHub's instructions for "push an existing repository", something
   like:
   ```
   git remote add origin <your-repo-url>
   git branch -M main
   git push -u origin main
   ```
   Run these in the RStudio **Terminal** tab (bottom pane), not the R
   Console, they're shell commands, not R code.

## Ongoing habits

- **Commit before starting a Claude session**, so there's always a known-good
  rollback point if something goes sideways.
- **Commit again once a fix is confirmed working** (not just written, tested
  and confirmed), with a message describing what changed.
- **Tag every distribution build**: the moment you run `build_dist.bat` and
  it produces e.g. `wildtag_beta3.zip`, tag the matching commit in the
  Terminal tab:
  ```
  git tag beta3
  git push --tags
  ```
  This gives you a permanent, exact answer to "what code made this zip",
  the exact problem that caused most of the confusion this session.
- **Treat the Git repo as the source of truth**, not whatever's sitting in
  a chat's project knowledge. Pull from Git at the start of a new
  development session rather than relying on an uploaded file that might be
  stale.
- Don't overthink branching for a solo project, committing directly to
  `main` frequently is fine, tags handle your release history.
