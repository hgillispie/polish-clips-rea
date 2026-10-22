# Smooth jump cuts

The AI Tools action that hides cuts in speech by regenerating a short stretch of AI speech, optionally lip-synced video, across each edit boundary. Sources (all **decompiled** from the signed build):

- chunk 9105: the panel definition and the results view
- chunk 5433: the reducer and action types
- the app chunk: the sagas

None of it ran in Hunter's capture. Pseudocode for our version is in [../../pseudocode/smooth-jump-cuts.md](../../pseudocode/smooth-jump-cuts.md).

## Panel

| Field | Value |
| --- | --- |
| Name | "Smooth jump cuts" |
| Gate | flag `ed-regenerate-ai-actions-integration` (true for Hunter) |
| Paywall | `aiSpeechImputation` (usage feature `regenerate_and_overdub`). With lip sync, the feature checked is `imputationLipSync` |
| Usage category | `smooth_jump_cuts` is billed under `ai_editing` |
| Saved params | `SET_AI_ACTIONS_SAVED_PARAMS {presetId: "smooth-jump-cuts", params: {method}}` |

Options:

- **Regenerate**: `audioOnly` or `videoAndAudio`. The second adds lip sync on the regenerated span.
- **Method**:
  - `findFirst`: find all edit boundaries, let the user review them, then smooth the chosen ones.
  - `smoothAll`: smooth every candidate now.

## Flow

1. **findFirst.**
   - Dispatches a project search with `searchType: "jump_cuts"` and a search-result action `SmoothJumpCuts`, then clears the AI-actions prompt.
   - The search results view lists candidate boundaries with a Smooth button.
   - Choosing some boundaries starts a run restricted to their candidate keys.
2. **smoothAll.**
   - Runs a pre-check `checkBeforeStarting {doc, compositionId, lipSyncRequested, candidates}`, where the candidates are the composition's smoothable jump cuts that no earlier run owns.
   - The pre-check can show confirm dialogs: `CONFIRM_SMOOTH_CREATED_BOUNDARIES` and its credit-warning and video-consent variants.
   - It then shows the results view (`SET_SMOOTH_JUMP_CUTS_RESULTS_VISIBLE true`) and starts the run.
3. **Run saga.**
   - **Order and concurrency.** Candidates are filtered to the requested keys and processed **in reverse time order**, so earlier edits do not shift later boundaries. Up to 20 workers run at once; the launch queue is serial.
   - **Pricing.** Candidates are priced in batches of up to 20. Each batch returns a cost per candidate and the remaining credits by category. A local credit ledger reserves credits per launch and skips the rest with `insufficientCredits` when the budget runs out.
   - **Launch spacing.** Launches are spaced at least **3000 ms** apart per project.
   - **Each launch.**
     1. Re-resolve the boundary from the current document. If the cut moved, skip with `cutChanged`; if it is gone, skip with `boundaryUnavailable`.
     2. Build an AI-speech regeneration request: the seed range around the boundary, no new text (regenerate the same words), entrypoint `edit_boundary`.
     3. Insert a new AI-speech clip (tau) tagged with the run id, skipping the per-call credits preflight because the run already priced it.
     4. A failed launch is skipped with `launchFailed`.
   - **Watch.** Each new tau is polled every **1 s** while its speech state or lip-sync state is `running`. There is a **10 s** grace period before the run gives up on one.
   - **Finish.** `FINISH_SMOOTH_JUMP_CUTS_RUN`. The run status becomes `launched`, or `cancelled` if the user stopped it.
4. **Revert.**
   - `REQUEST_REVERT_SMOOTH_JUMP_CUTS_RUN` deletes every tau the run created, with a 5 s timeout each.
   - The status becomes `reverted`. On error: `RESTORE_SMOOTH_JUMP_CUTS_AFTER_REVERT_FAILURE`.

## State

```text
SmoothJumpCutsRun
  id, projectId, compositionId
  candidateCount, launchLimit
  candidateKeys      string[]        # boundary keys in scope
  source             undefined | "editForClarity"
  tauIds             string[]        # AI-speech clips created
  skipReasonByCandidateKey  {key: "cutChanged" | "boundaryUnavailable" | "launchFailed" | "insufficientCredits"}
  status             "launching" | "cancelled" | "launched" | "reverted"

aiActions.pendingEditForClaritySmoothJumpCuts
  candidateKeysBeforeEdits, regenerateMode, runIds
```

Actions (LLM / AITools slice): `SET_SMOOTH_JUMP_CUTS_RESULTS_VISIBLE`, `START_SMOOTH_JUMP_CUTS_RUN`, `ADD_SMOOTH_JUMP_CUTS_RUN_TAU`, `SKIP_SMOOTH_JUMP_CUTS_RUN_CANDIDATE`, `CANCEL_…`, `FINISH_…`, `SET_…_REVERTING`, `REMOVE_…_TAU`, `RESTORE_…_AFTER_REVERT_FAILURE`, `REQUEST_REVERT_SMOOTH_JUMP_CUTS_RUN`, `CONFIRM_SMOOTH_CREATED_BOUNDARIES`.

## Edit for clarity hook

Edit for clarity has the toggle `enableSmoothJumpCuts` ("Regenerate to smooth cuts made"; flags `ed-regenerate-ai-actions-integration` and `ai-actions-new-edit-review-state`).

1. It snapshots the candidate keys **before** its edits.
2. After the edits it starts a run with `source: "editForClarity"`, limited to the boundaries those edits created.

## The agent's jump-cut tools are different

Underlord does not call Smooth jump cuts. Its related tools:

- **`query_jump_cuts`** (in the 72 sent to Hunter).
  - Lists the "beats" between media splices in a composition: `startTime`, `endTime`, `duration`, `text`, `wordCount`, plus `sceneId` when the splice is already a scene boundary.
  - A beat is `eligible: false` when it is shorter than about 0.75 s or has two words or fewer.
- **Zoom at jump cuts** (hidden guidance skill `zoom-at-jump-cuts` plus an internal zoom-cuts action).
  1. Adds inline scene boundaries at eligible beats (commit "Creating scenes for jump cuts").
  2. Punches in on alternating segments, default scale **1.15**.
  3. Cleans up (commit "Zoom cut cleanup").
  - This hides the cut visually instead of regenerating speech.
