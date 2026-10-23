# Highlight Reel (pseudocode)

Spec: [../features/highlight-reel/README.md](../features/highlight-reel/README.md). Reuses [find-highlights.md](find-highlights.md) and beat tracking from [media-montage.md](media-montage.md). All of this is **design**.

```text
function highlight_reel(sources, p) -> Reel:
  M = moments(sources, win=(3, 15))                         # find-highlights stages 0–4, short windows + role labels
  hook = p.intro_hook ? pick_hook(M) : null
  body = M - {hook} if hook else M
  fixed = (hook?.dur or 0) + (p.end_card?.dur_s or 0)
  budget = p.target_s - fixed
  chosen = solve(body, budget, p)
  order = order_moments(chosen, p.ordering)
  T = plan_transitions(order, p.style, beats = p.music ? beat_grid(p.music) : null)
  fine_fit(order, T, target=p.target_s, tol=p.tolerance_s, fixed)
  return assemble(hook, order, T, p)
```

## Hook

```text
function pick_hook(M):
  payoff = argmax(m.score for m in M if m.role == "payoff")
  for m in sort_desc(M, by=m.sub.hook):
    if 2 <= m.dur <= 5 and not reveals(m, payoff):        # LLM yes/no, temperature 0
      return m
  return null
```

## Solver

```text
function solve(M, budget, p):
  U = 0.1                                                   # seconds per bucket
  cap = round((budget + p.tolerance_s) / U)
  tr = transition_overlap(p.style)                          # seconds lost per join (crossfade)
  items = [(m, round((m.dur - tr) / U), m.score) for m in M]
  locked = [m for m in M if m.locked]
  cap -= sum(w for (m, w, _) in items if m in locked)
  # DP: best[c] = (value, set) using unlocked items
  best = array(cap+1, (−INF, {})); best[0] = (0, {})
  for (m, w, v) in items if m not in locked:
    for c in cap..w step -1:
      if best[c-w].value + v > best[c].value: best[c] = (best[c-w].value + v, best[c-w].set ∪ {m})
  lo = round((budget - p.tolerance_s) / U) - locked_weight
  pick = argmax over c in [max(lo,0), cap] of best[c].value
  S = best[pick].set ∪ locked
  S = local_search(S, M, budget, p, iters=200)              # swap-in/out to cut redundancy, add coverage, enforce constraints
  return S

function objective(S):
  return Σ m.score − 40 * Σ_{a<b} max(0, cos(a.emb, b.emb) − 0.8) + 5 * |segments(S)|
         − 1000 * violates(S)       # story_arc: needs setup & payoff; speaker share ≤ 0.6; locked present; duration in range
```

## Ordering

```text
function order_moments(S, mode):
  if mode == "chronological": return sort(S, by=(source_clock_time))
  if mode == "best_first":   return sort_desc(S, by=score)
  roles = ["setup", "build", "payoff", "outro"]
  seq = concat(sort(S where role==r or (r=="build" and role=="none"), by=time) for r in roles)
  for k in 1..3:
    swap = llm_json("reel_coherence.v1", {seq: [text(m) for m in seq]}, schema={swap: [i, i+1] | null})
    if not swap: break
    cand = swap_adjacent(seq, swap)
    if coherence_judge(cand) > coherence_judge(seq): seq = cand
  return seq
```

## Transitions and fine fit

```text
function plan_transitions(seq, style, beats):
  for a, b in pairs(seq):
    kind = style == "clean" ? "cut" : style == "crossfade" ? "xfade" : "whip"
    if a.speaker == b.speaker and same_shot(a, b) and kind == "cut": kind = "punch_in"
    frames = {cut: 0, punch_in: 0, xfade: 10, whip: 6}[kind]
    yield {after: a.id, kind, frames, audio_xfade_frames: 2}
  if beats: snap each join to nearest beat within ±0.15 s by adjusting a.tail / b.head silence only

function fine_fit(seq, T, target, tol, fixed):
  err = total(seq, T) + fixed - target
  if abs(err) <= tol: return
  # use tails (0–0.4 s each) and xfade lengths (6–14 frames) as slack, never words
  distribute(-err, slack=[m.tail_slack for m in seq] + [t.frames_slack for t in T])
```

## Assemble

```text
function assemble(hook, seq, T, p):
  commit("Create highlight reel"):
    comp = create_composition(name=p.title or "Highlight reel", aspect=p.aspect)
    if hook: add_range(comp, hook); add_transition(comp, "flash", frames=6)
    for m, t in zip(seq, T + [null]): add_range(comp, m); if t: add_transition(comp, t)
    if p.end_card: add_card(comp, p.end_card)
    if p.aspect == "9:16": apply_reframe(comp)                # find-highlights plan_reframe per range
    add_captions(comp); loudnorm_each_range(comp, -16)
    if p.music: add_music(comp, p.music, duck={depth_db: -12, attack_ms: 300, release_ms: 300}, end_on_downbeat=true)
  reel.packaging = {pl: publish_package_for(comp, pl) for pl in p.platforms}
```
