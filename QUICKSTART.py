#!/usr/bin/env python3
"""
Vera Bot — Quick Start Guide

This script shows how to deploy and test the bot locally.
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   VERA BOT - MAGICPIN AI CHALLENGE                         ║
║                                                                            ║
║  A minimal, deterministic merchant engagement bot that composes            ║
║  WhatsApp messages from 4 context layers.                                  ║
╚════════════════════════════════════════════════════════════════════════════╝

## FILE STRUCTURE

bot.py                  — Main FastAPI server (5 endpoints, ~300 lines)
                        - GET /v1/healthz
                        - GET /v1/metadata
                        - POST /v1/context (push contexts)
                        - POST /v1/tick (compose & send)
                        - POST /v1/reply (handle merchant replies)

submission.jsonl        — 30 test pairs pre-composed (ready to submit)

generate_submission.py  — Script to regenerate submission.jsonl if needed

expanded/               — Full dataset (5 categories, 50 merchants, 200 customers, 100 triggers)
  ├── categories/      — Category contexts (voice, offers, digests, etc.)
  ├── merchants/       — Merchant contexts (performance, offers, etc.)
  ├── customers/       — Customer contexts (relationship state, preferences)
  ├── triggers/        — Trigger contexts (events that prompt messages)
  └── test_pairs.json  — 30 canonical test pairs

README.md               — Detailed approach documentation

requirements.txt        — Python dependencies (fastapi, pydantic, uvicorn)

test_bot.py             — Unit test for composition logic


## QUICK START

1. Install dependencies:
   pip install -r requirements.txt

2. Start the bot server:
   python bot.py
   → Listens on http://localhost:8080

3. In another terminal, test it:
   curl http://localhost:8080/v1/healthz
   → {"status":"ok","uptime_seconds":2,"contexts_loaded":{...}}

4. (Optional) Run the test:
   python test_bot.py
   → Verifies composition logic works


## DEPLOYMENT

For the challenge:
- Deploy bot.py to a public URL (AWS, GCP, Render, Railway, etc.)
- Submit the URL via the challenge portal
- The judge will:
  1. Push all dataset contexts to /v1/context
  2. Call /v1/tick periodically to get messages
  3. Simulate merchant replies via /v1/reply
  4. Score the bot's composition + conversation handling

Estimated runtime: 60 simulated minutes


## COMPOSITION STRATEGY

The bot routes messages by trigger.kind:

  research_digest → (dentists) Extract digest item, offer to pull abstract
  perf_dip        → Acknowledge drop, offer diagnostic help
  perf_spike      → Spotlight merchant's active offer
  curious_ask     → Ask merchant "what's most-asked this week?"
  recall_due      → (customer-facing) Send recall reminder with language preference
  (default)       → Generic friendly checkin

All messages:
  ✓ Respect category voice (clinical for dentists, operator-speak for restaurants)
  ✓ Use merchant's real name + offers
  ✓ Stay ≤ 320 characters
  ✓ Include single primary CTA (binary or open-ended)
  ✓ Anchor on real data, never fabricate


## EXPECTED PERFORMANCE

Based on the 5-dimension rubric (50 total):
  - Specificity       : 7-8/10  (real data, some citations)
  - Category fit      : 8-9/10  (voice adapted per vertical)
  - Merchant fit      : 8-9/10  (real names, offers, language)
  - Trigger relevance : 7-8/10  (clear reason for message)
  - Engagement        : 6-7/10  (predictable phrasing, limited LLM)

Estimated total: 36-41 / 50

Wins on fit + specificity. Loses on unpredictability (rule-based, not learned).


## KEY DESIGN DECISIONS

1. NO LLM CALLS (Free tier)
   - Rule-based composition instead
   - Deterministic, reproducible
   - Zero API cost during development + testing

2. RULE-BASED ROUTING
   - Dispatch by trigger.kind
   - Category-specific templates
   - Fallback to generic checkin

3. IN-MEMORY STATE
   - Sufficient for 60-min test
   - Fast (no DB latency)
   - Simple debugging

4. MINIMAL MULTI-TURN
   - Auto-reply detection
   - Intent recognition (yes/no/unclear)
   - Simple state machine (not full dialogue)


## IF UPGRADING TO LLM

To improve score by 10+ points:

1. Use free tier Claude Instant or GPT-4o-mini
2. Retrieve top 3 digest items; let LLM pick best match
3. Add function calling to look up peer-comparable merchants
4. Track conversation sentiment; adjust tone per turn
5. Use examples (few-shot) from case studies

Cost: ~$0.01-0.05 per composition (still minimal)


## TESTING CHECKLIST

Before submitting:
  [ ] python test_bot.py                    (tests composition logic)
  [ ] python bot.py                         (starts server on :8080)
  [ ] curl http://localhost:8080/v1/healthz (healthz passes)
  [ ] cat submission.jsonl | wc -l          (30 lines?)
  [ ] Each line is valid JSON?              (python -m json.tool)
  [ ] All bodies ≤ 320 chars?               (check samples)
  [ ] No URLs in bodies?                    (grep http submission.jsonl)
  [ ] No repeated bodies in same conversation?
  [ ] Rationales match actual outputs?


## SUPPORT

If the bot times out or fails:
1. Check /v1/healthz (3 consecutive failures = disqualified)
2. Ensure all 5 endpoints return valid JSON within 10s
3. Verify contexts are stored after /v1/context calls
4. Check bot.py logs for errors

For local iteration:
  python test_bot.py       (fast unit test)
  python judge_simulator.py --scenario warmup  (mini judge)

---

Built: April 29, 2026
Challenge: magicpin AI — Vera merchant engagement
Status: Ready for submission
""")

