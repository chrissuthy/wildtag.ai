# Training a solid UK classifier from DeepFaune-Europe

A strategy for extending DeepFaune-Europe into a UK model, keeping the classes it
already handles well and adding the UK-specific ones. Written to be shared with
collaborators; nothing here is committed until we agree the class design.

## 1. The core idea

Do not train from scratch, and do not repeat what DeepFaune-UK v1.1 did. Start
from the DeepFaune-Europe ViT-L DINOv2 backbone, which already produces
excellent features for most UK fauna, and retrain a UK classification head on top
of it. This is transfer learning, the same route Fergus took, but with three
deliberate differences that matter for wildtag:

1. **Keep the input at 224, not 518.** DeepFaune-UK's 518-pixel ViT is why it was
   unusably slow on a CPU. Staying at DeepFaune-Europe's 224 keeps wildtag fast on
   field laptops. This single choice is the main reason to build our own rather
   than adopt theirs.
2. **Design the output classes around what is distinguishable on camera**, with an
   honest fallback to coarser labels when the animal cannot be told apart at
   species level (Section 3).
3. **Train on wildtag's own validated data** (Section 4), closing a loop the rest
   of the project already built.

## 2. What DeepFaune-Europe already gives us

DeepFaune-Europe's real classes (from wildtag's own label list) are 27 species,
6 groups, and 5 special categories. Mapping your UK target list against them:

**Already covered directly (keep as-is, no new training needed to recognise them):**
beaver, hedgehog, fox, otter, badger, wild boar, roe deer, red deer, fallow deer,
bison, cow, sheep, goat, horse (as the `equid` group), dog, domestic cat, bird,
and small mammal (as `micromammal`).

That is roughly two-thirds of your list. The real work is only in three lumped
groups that UK monitoring needs split to species, plus a handful of introduced
species DeepFaune has never seen.

**Groups DeepFaune lumps that UK work needs split:**

| DeepFaune class | UK species we need from it | Difficulty |
|---|---|---|
| `squirrel` (one class) | red squirrel, grey squirrel | Easy, data-rich, high conservation value |
| `lagomorph` (one class) | rabbit, brown hare, mountain hare | Rabbit easy; the two hares hard, esp. on IR |
| `mustelid` (one class) | pine marten, polecat, American mink, stoat, weasel | Marten/polecat/mink feasible; stoat vs weasel very hard |
| `cat` (domestic) | domestic cat vs European/Scottish wildcat | Very hard, conservation-sensitive |

**Species not in DeepFaune-Europe at all (genuinely new heads):**
sika deer, water deer, Reeves's muntjac (all introduced, and muntjac/sika are
data-rich in UK camera sets), and domestic pig (minor).

**Subspecies:** merge Scottish wildcat into a single wildcat class. Camera imagery
cannot resolve *F. s. silvestris* from the European wildcat, and the wildcat vs
feral/hybrid cat problem is already the hard part.

## 3. Output-class design (the part you flagged)

The central design decision is a **taxonomy with abstention**: train species-level
heads, but let the model roll up to a coarser class when it is not confident,
rather than emit a confident wrong species. This mirrors DeepFaune's own group
classes and is honest ecology. Concretely:

- **Confident, distinguishable species** get their own class: fox, badger, the
  three common deer, wild boar, hedgehog, otter, beaver, red squirrel, grey
  squirrel, rabbit, pine marten, polecat, American mink, muntjac, sika, and the
  domestics. These are where DeepFaune already excels or where UK data is plentiful.

- **Hard pairs get a species head plus a group fallback.** When the top-1 species
  confidence is below a tuned threshold, output the group instead of guessing:
  - stoat / weasel -> fall back to **"small mustelid"**
  - brown hare / mountain hare -> fall back to **"hare"**
  - domestic cat / wildcat -> fall back to **"cat (species uncertain)"**
  - roe / red / fallow / sika / water deer at distance -> fall back to **"deer"**

  This gives a usable label on every image and prevents the confident-error
  failure mode we just saw with DeepFaune-UK's ViT.

- **Non-target catch-alls:** bird, small mammal (micromammal), plus the pipeline's
  existing person, vehicle, and empty. Keep these; they absorb everything outside
  the target list.

- **Rare species with thin data** (water deer, wildcat, bison, beaver): include
  them as classes but expect wide confidence intervals, and lean on the abstention
  fallback so a low-confidence beaver becomes "small mammal" or "empty" rather than
  a false positive. Do not over-claim rare detections.

The result is a class list of roughly 30 to 35 species plus 4 to 6 group/non-target
fallbacks. The exact cut between "own class" and "fallback only" should be data-
driven: promote a species to its own class only once there is enough validated UK
data to hold a test set for it.

## 4. Data strategy

The training data is the hard part, and this is where wildtag has an unfair
advantage. The validation pipeline built in this project produces validated,
species-labelled crops as a by-product of normal use. UKWO and MammalWeb validated
data is therefore a ready training set, and every future validation round enlarges
it. This is worth stating plainly for the paper: the tool bootstraps its own model.

- **Data-rich classes** (grey squirrel, muntjac, sika, mink, fox, deer, badger):
  abundant in UK camera sets, straightforward to assemble.
- **Data-poor classes** (water deer, wildcat, beaver, bison, mountain hare):
  supplement from partner archives, the DeepFaune-UK training crops if the CC-BY-NC
  licence permits, and targeted collection. Wildlife-park footage can seed the very
  rare ones.
- **Split by site, not by image.** Camera-trap frames from one deployment are
  near-duplicates; a random split leaks the test set. Hold out whole sites.
- Balance day RGB and night IR, and include motion blur, occlusion, juveniles,
  multi-animal frames, and manufacturer overlays.

## 5. Training procedure

1. **Phase 1, linear probe.** Freeze the DeepFaune-Europe backbone, train the new
   UK head. Fast, needs modest data, cannot forget the European features.
2. **Phase 2, partial fine-tune.** Unfreeze the top few transformer blocks at a low
   learning rate, only if the data supports it, to sharpen the hard UK splits
   (red/grey squirrel, the mustelids). Watch for overfitting on rare classes.
3. **Imbalance:** class-balanced or focal loss, oversample rare classes, strong
   augmentation tuned to camera-trap conditions (grayscale/IR, blur, crop jitter).
4. **Inference parity:** train on crops produced the same way wildtag crops at
   inference (same detector, same box handling), so training and deployment match.

## 6. Evaluation

- Site-disjoint held-out UK test set. Report per-class precision, recall, F1, and a
  confusion matrix, with a focused look at the hard pairs.
- Report two accuracies: strict species-level, and effective accuracy allowing the
  abstention fallback. The gap between them is the honest cost of the hard classes.
- Give rare classes explicit confidence intervals; do not headline a single number
  the way the DeepFaune-UK card does.

## 7. Deployment into wildtag

Export in the format wildtag's existing DeepFaune (PyTorch) backend already loads,
so the UK model drops into that backend rather than needing a new ONNX two-stage
path. Add a registry entry with the UK class list, flip its `available` flag on,
and it appears on the Models screen alongside the others. Because it stays at 224
and reuses the European backbone, it will run at DeepFaune-Europe speed, not
DeepFaune-UK speed.

## 8. Phased roadmap

1. Finalise the class taxonomy: the own-class vs fallback cut, and the abstention
   thresholds. This document is the starting point.
2. Assemble the dataset from validated wildtag/UKWO data plus supplements; split by
   site.
3. Phase-1 linear-probe baseline; read the confusion matrix.
4. Iterate: add data for weak classes, phase-2 fine-tune, tune abstention.
5. Site-disjoint evaluation and honest reporting.
6. Export, register, ship.

## Open questions for the group

- Which hard pairs are worth a species head versus fallback-only, given the UK data
  you can actually assemble? (Biggest lever on final quality.)
- Is the DeepFaune-UK CC-BY-NC training set usable as a data source, or do we build
  ours purely from validated UKWO data?
- Do we want the abstention fallback exposed to the user (a confidence slider), or
  fixed thresholds baked in?
