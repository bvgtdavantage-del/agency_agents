# Benable AI Academy

An interactive, self-contained training application by **benable ai** for knowledge workers at large Gulf (GCC) enterprises — UAE, Saudi Arabia, Qatar, Bahrain, Kuwait, Oman — covering prompt engineering and AI adoption in daily corporate work.

The curriculum is adapted from the *AI-Native Workforce* enterprise briefing (the source PDF) and its Four-Signal capability framework: **Recognition, Direction, Judgement, Refinement**.

## Contents

Six modules, each with lesson cards and a 4-question quiz (pass mark 3/4):

1. **The AI-Native Mandate** — why output stopped being proof; the 3–5× productivity spread; Gulf national AI strategies
2. **The Four Signals** — the anatomy of AI capability, with an animated compass diagram
3. **Prompt Engineering I — Direction** — the five-part prompt (role, context, task, constraints, format) with Gulf business examples
4. **Prompt Engineering II — Refinement** — critique–re-direct–verify loop, hallucination defense, confidentiality (UAE/Saudi PDPL)
5. **AI in the Daily Workflow** — five daily arenas, a before/after workday, the mis-hire ROI arithmetic
6. **The AI-Native Organization** — assessment / embedded training / continuous evaluation; build-vs-buy standards argument; a 90-day mandate

## Features

- Animated stat counters, module transitions, quiz feedback micro-animations (respects `prefers-reduced-motion`)
- Instant answer feedback with an explanation for every question
- Progress saved in `localStorage`; per-module scores and a header progress ring
- Printable completion certificate with the learner's name, benable ai branded
- English content with Arabic module accents; light product theme with a full dark-mode variant (system preference and explicit `data-theme` both supported)

## Running

No build, no dependencies — open the file in a browser:

```bash
open gulf_ai_academy/index.html
```

Fonts (Bricolage Grotesque, Schibsted Grotesk, Spline Sans Mono) load from Google Fonts; without network access the declared fallback stacks are used.
