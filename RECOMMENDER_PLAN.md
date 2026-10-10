# LeetCode Recommender MVP — Phase-by-Phase Implementation Plan

## Goal

Build a 5-day adaptive LeetCode learning recommender that selects problems based on:

- concept competence
- recency of concept exposure
- problem difficulty fit
- redundancy with recently completed problems
- day-dependent curriculum weights

The recommender should use hard constraints for candidate generation, then rank eligible candidates with a weighted scoring function.

Core scoring model:

```text
score(problem, user, day) =
    w_recency(day)    * recency(problem)
  + w_competence(day) * competenceGap(problem)
  + w_difficulty(day) * difficultyFit(problem)
  - w_redundancy(day) * redundancy(problem)
```

All derived scoring values should be normalized to `[0,1]`.

Recommendation logging / explainability is P1 and should not block MVP.

---

# Phase 1 — Domain Model: Concepts

## Objective

Make concepts first-class objects so learning state can be represented at the concept level rather than only at the problem level.

## Add Concept model

Minimum fields:

```text
Concept {
    id
    name
    competence
    exposureCount
    lastPracticedAt
}
```

`competence`:

- range `[0,1]`
- initialize to `0`
- represents demonstrated competence
- `0 + exposureCount=0` means unknown/unseen
- `0 + exposureCount>0` means demonstrated weakness

Do not persist a derived `recency` score. Persist the underlying timestamp.

## Update Problem model

Problems should reference one or more concepts:

```text
Problem {
    ...
    difficulty
    concepts[]
}
```

Difficulty remains discrete:

```text
EASY
MEDIUM
HARD
```

## Multi-concept behavior

For MVP, all concepts attached to a problem are equally weighted.

Examples:

```text
1 concept  -> weight 1.0
2 concepts -> weight 0.5 each
3 concepts -> weight 0.333 each
```

Do not introduce primary/secondary concept weighting in MVP.

## Deliverable

The application can represent problems with concept associations and maintain per-concept user learning state.

---

# Phase 2 — Submission Enrichment + Learning-State Updates

## Objective

Use existing submission events to update concept competence and exposure state.

Do not create a separate Attempt model.

## Extend Submission

Preserve existing deterministic submission fields.

Add optional metadata needed by the learning system. Qualitative/LLM-generated values must be nullable.

Potential fields:

```text
hintLevel?
outcomeScore?
approachQuality?
analysisMetadata?
```

Exact naming should follow existing project conventions.

Do not make the recommender dependent on LLM metadata being present.

## Outcome score

Normalize attempt quality onto `[0,1]`.

Initial heuristic:

```text
1.0 = solved independently
0.7 = solved independently with significant struggle / slow solve
0.4 = solved with a meaningful hint
0.2 = substantial assistance required
0.0 = failed / gave up
```

If qualitative metadata is unavailable, derive the best available outcome score from deterministic submission information.

## Competence update

Use an incremental update:

```text
newCompetence =
    oldCompetence
    + learningRate * (outcomeScore - oldCompetence)
```

Use an exposure-dependent learning rate so early evidence changes competence more strongly than later evidence.

Example:

```text
learningRate =
    baseLearningRate / sqrt(exposureCount + 1)
```

Exact constants should live in configuration.

For every concept associated with the submitted problem:

1. calculate concept attribution weight
2. update competence
3. increment exposureCount
4. set lastPracticedAt
5. persist state

Because concepts are equally weighted:

```text
conceptWeight = 1 / problem.concepts.length
```

The competence update should account for this weight.

## Deliverable

Completing problems causes concept competence, exposure count, and practice timestamps to evolve automatically.

---

# Phase 3 — Derived Learning Features

## Objective

Implement deterministic functions that convert persisted state into normalized recommendation-time features.

These functions should not mutate state.

---

## 3A. Recency

Recency is calculated at recommendation time from `lastPracticedAt`.

`1.0` is reserved as the sentinel for an unseen concept.

Example initial schema:

```text
never practiced -> 1.0
< 6 hours       -> 0.0
6–24 hours      -> 0.1
1–2 days        -> 0.3
2–3 days        -> 0.5
3–5 days        -> 0.7
5+ days         -> 0.9
```

Exact boundaries should be constants/configuration rather than embedded throughout business logic.

For a multi-concept problem, aggregate the recency values of its concepts using equal weighting.

---

## 3B. Competence Gap

For a concept:

```text
competenceGap = 1 - competence
```

For a multi-concept problem, aggregate concept competence gaps equally.

Start with the arithmetic mean.

Keep aggregation isolated behind a function so a low-order interaction function can be introduced later without rewriting the ranking pipeline.

Example API:

```text
calculateProblemCompetenceGap(problemConcepts)
```

---

## 3C. Difficulty Fit

Difficulty fit is not persisted.

Calculate it from:

```text
problem difficulty
+
aggregate competence over problem concepts
```

Use a discrete heuristic matrix for MVP.

Initial example:

```text
competence 0.0–0.3
Easy   -> 1.0
Medium -> 0.4
Hard   -> 0.0

competence 0.3–0.7
Easy   -> 0.6
Medium -> 1.0
Hard   -> 0.3

competence 0.7–1.0
Easy   -> 0.2
Medium -> 0.9
Hard   -> 1.0
```

Treat these as tunable constants, not universal truths.

---

## Deliverable

Given a user and problem, the system can independently derive:

```text
recency
competenceGap
difficultyFit
```

without performing recommendation ranking yet.

---

# Phase 4 — Recent-History + Redundancy

## Objective

Prevent recommendations from repeatedly serving nearly identical concepts simply because those concepts have high learning value.

Redundancy is calculated at recommendation time and is not persisted on Problem.

## Fetch recent completions

Retrieve a bounded recent-completion window:

```text
completionStack.head(N)
```

`N` should be configurable.

Do one history query, not separate queries per candidate/problem concept.

## Concept-overlap redundancy

For each candidate problem:

1. compare its concepts to concepts in recent completions
2. assign greater penalty to more recent overlap
3. normalize result to `[0,1]`

Conceptual form:

```text
redundancy(candidate) =
    max(
        conceptOverlap(candidate, recentProblem)
        * historyDecay(position)
    )
```

For MVP, concept overlap can be deterministic:

```text
no shared concepts          -> 0
partial concept overlap     -> intermediate
identical concept set       -> 1
```

Recent entries should contribute more than older entries.

Keep `conceptOverlap()` and `historyDecay()` as separate functions.

## Exact problem repetition

Do not permanently exclude solved problems.

Allow exact problems to re-enter the pool after sufficient time.

A short repeat cooldown may be implemented as a hard constraint, while long-term reappearance is governed by recency.

## Deliverable

The system can calculate a context-sensitive redundancy value for every candidate using one bounded history fetch.

---

# Phase 5 — Five-Day Curriculum State

## Objective

Represent where the learner is in the 5-stage learning program.

Program progression should be based on completed work, not wall-clock days.

## Program state

Add or extend user learning-program state:

```text
ProgramState {
    currentDay       // 1..5
    completedInDay
}
```

Persist whatever identifiers/timestamps are required by the existing architecture.

## Advancement

Minimum requirement:

```text
completedInDay >= 2
```

A user must complete at least 2 problems before advancing.

Do not automatically advance simply because a calendar day has passed.

Do not require a competence threshold for advancement; weak users should not become permanently trapped on one stage.

When a program day advances:

```text
currentDay += 1
completedInDay = 0
```

Define expected behavior after Day 5 explicitly.

For MVP, choose one simple behavior:

- remain in Day-5/interleaved mode, or
- reset/start another cycle

Prefer remaining in Day-5 mode unless the product already has a concept of repeated programs.

## Curriculum semantics

The five stages should roughly represent:

```text
Day 1: acquisition-heavy
Day 2: acquisition + spaced retrieval
Day 3: mixed retrieval / increasing interleaving
Day 4: weakness-focused + highly interleaved
Day 5: mostly mixed/interview-style practice
```

This should be expressed through configuration and ranking behavior rather than separate recommendation implementations for every day.

## Deliverable

The recommender can determine the current curriculum stage and progress users through all five stages based on completed work.

---

# Phase 6 — Candidate Generation

## Objective

Separate hard eligibility constraints from soft ranking.

Do not encode absolute exclusions as giant negative score weights.

## Candidate generation

Create a function/service such as:

```text
generateCandidates(user, programState)
```

It should apply inexpensive hard constraints before scoring.

Potential MVP constraints:

- valid/active problems only
- problem has concept metadata
- supported difficulty
- exact-problem cooldown
- curriculum-specific restrictions, if required
- any existing user/problem exclusions

Do not permanently remove solved problems.

## Candidate-pool sizing

Use a bounded candidate pool.

The exact size depends on the existing dataset. Start with a configurable value rather than optimizing prematurely.

For a small LeetCode corpus, fetching a broad eligible set may be acceptable for MVP.

Keep the retrieval layer separate anyway so candidate generation can later become more sophisticated.

## Deliverable

The ranking layer receives only a bounded pool of eligible problems.

---

# Phase 7 — Ranking Engine

## Objective

Implement the core weighted ranking function.

For every candidate, derive:

```text
recency
competenceGap
difficultyFit
redundancy
```

Then calculate:

```text
score =
    w_recency(day)    * recency
  + w_competence(day) * competenceGap
  + w_difficulty(day) * difficultyFit
  - w_redundancy(day) * redundancy
```

## Day-dependent weights

Store weight tables in centralized configuration.

Example shape:

```text
DAY_WEIGHTS = {
    1: {...},
    2: {...},
    3: {...},
    4: {...},
    5: {...}
}
```

The exact values are tuning parameters.

The intended progression is:

```text
early days:
    greater emphasis on exposure/acquisition

later days:
    greater emphasis on retrieval, weak concepts,
    appropriate challenge, and reduced repetition
```

Do not introduce `transferValue` in MVP.

## Tie-breaking

When candidates have effectively equal scores, randomize their ordering.

Define a small score tolerance rather than requiring bit-for-bit equality.

Example:

```text
abs(scoreA - scoreB) < epsilon
```

then randomized tie break.

This prevents deterministic repetition among equivalent candidates.

## Deliverable

Given an eligible candidate pool, user state, recent history, and program day, the system returns a ranked list of recommended problems.

---

# Phase 8 — Batch Selection + Diversity Guardrails

## Objective

Prevent pathological batches after ranking.

Ranking should not have to encode every batch-level constraint.

After sorting candidates, construct the final batch while applying simple diversity rules.

Potential MVP guardrail:

```text
max N problems sharing the same concept in a recommendation batch
```

Keep this conservative. Redundancy already handles much of the repetition problem.

Do not build sophisticated optimization here in MVP.

The sequence should be:

```text
candidate generation
        ↓
feature calculation
        ↓
ranking
        ↓
batch diversity constraints
        ↓
final recommendations
```

## Deliverable

The API returns a usable batch rather than simply the top K raw scores.

---

# Phase 9 — Recommendation API / Product Integration

## Objective

Expose the recommender through the existing application workflow.

The recommendation request should:

1. load program state
2. load relevant concept state
3. fetch recent completions once
4. generate candidates
5. derive features
6. rank candidates
7. apply diversity/tie-breaking
8. return final recommendations

The response should contain enough information for the UI to render each problem.

For MVP, do not require persistent recommendation logs.

If useful for local development, component scores may be exposed behind debug/development configuration without persisting them.

## Deliverable

A user can request recommendations and receive an adaptive batch based on their actual learning state.

---

# Phase 10 — Testing + Calibration

## Objective

Verify that the recommender behaves sensibly before attempting data-driven optimization.

## Unit tests

Cover each deterministic component independently:

- competence update
- exposure-dependent learning rate
- concept weighting
- recency buckets
- unseen recency sentinel
- competence-gap aggregation
- difficulty-fit matrix
- concept overlap
- history decay
- redundancy calculation
- program-day advancement
- candidate constraints
- score calculation
- tie-breaking boundaries

## Scenario tests

Create synthetic users representing:

### New learner

```text
no concept exposure
competence = 0
```

Expected:

- canonical/easier problems should dominate
- unseen concepts should be eligible

### Weak learner on a known concept

```text
high exposure
low competence
```

Expected:

- concept gets learning priority
- but recent redundancy prevents endless repetition

### Strong learner

```text
high competence
```

Expected:

- Medium/Hard difficulty fit increases
- trivial Easy problems lose ranking value

### Recently drilled concept

Expected:

- redundancy suppresses immediate repetition
- concept can return later through recency

### Returning learner

Expected:

- old practiced concepts gain recency priority again

### Multi-concept problem

Expected:

- all relevant concept states contribute equally

## Calibration

All initial constants should live centrally:

- competence base learning rate
- recency buckets
- recent-history window `N`
- history-decay values
- exact-repeat cooldown
- difficulty-fit matrix
- day weights
- tie epsilon
- batch diversity limits

Do not prematurely optimize these constants.

The purpose of MVP calibration is to avoid obviously bad behavior, not prove optimality.

---

# P1 — Explicitly Deferred

Do not block MVP on:

- LeetCode acceptance-rate ingestion: add a nullable problem field, populate it through
the existing importer, and use it only as an optional calibration/tie-break signal.
It must not replace concept state or become a hard eligibility constraint.
- persistent recommendation logging
- score-component audit history
- prompt/model version logging
- LLM-based transfer-value scoring
- primary vs secondary concept attribution
- learned ranking
- embeddings/problem similarity
- collaborative filtering
- contextual bandits
- Bayesian knowledge tracing / IRT
- automatic weight optimization
- A/B testing infrastructure
- sophisticated long-term learning evaluation

These should be layered on after deterministic MVP behavior is stable.

---

# Recommended Implementation Order

Implement in this dependency order:

```text
1. Concept model + problem associations
2. Submission enrichment
3. Competence/exposure write-time updates
4. Recency derivation
5. Competence-gap aggregation
6. Difficulty-fit heuristic
7. Recent-history retrieval + redundancy
8. Program state + 5-day advancement
9. Candidate generation
10. Ranking engine
11. Batch diversity/tie-breaking
12. API/product integration
13. Tests + calibration
```

Each phase should leave the codebase in a working/testable state before moving to the next phase.

The MVP is complete when a submission changes concept learning state and subsequent recommendation requests demonstrably adapt based on competence, elapsed practice time, problem difficulty, recent concept repetition, and the user's current stage in the 5-day program.