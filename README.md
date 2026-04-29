# Vera Bot — Minimal Merchant Engagement Assistant

**Status**: Working submission for magicpin AI Challenge  
**Approach**: Rule-based trigger dispatch with category-specific voice  
**Cost**: Free (no API calls required; all logic deterministic)

---

## What's Built

A FastAPI server implementing the 5 required endpoints:
- `GET /v1/healthz` — liveness probe
- `GET /v1/metadata` — bot identity
- `POST /v1/context` — receive category/merchant/trigger/customer contexts
- `POST /v1/tick` — decide which messages to send this cycle
- `POST /v1/reply` — handle merchant/customer replies in multi-turn conversations

**Total runtime**: ~80 lines of core composition logic + ~200 lines of FastAPI scaffolding.

---

## Composition Strategy

### Trigger-Based Routing

The bot routes based on `trigger.kind`:

| Trigger Kind | What It Does |
|---|---|
| `research_digest` | Extract top item from category digest; offer merchant to pull abstract + draft patient note |
| `perf_dip` | Acknowledge performance drop; offer diagnostic help |
| `perf_spike` / `milestone_reached` | Spotlight a merchant's active offer |
| `curious_ask_due` | Ask merchant what's most-asked this week; offer Google post + reply draft |
| `recall_due` | Customer-facing: send on-behalf recall reminder with language preference |
| *others* | Generic friendly checkin (fallback) |

### Category Voice Adaptation

Each composition respects **category tone** from `CategoryContext.voice`:

- **Dentists**: clinical, technical vocabulary (e.g., "fluoride varnish", "IOPA"), source citations
- **Restaurants**: operator-to-operator tone (e.g., "covers", "AOV", "delivery radius")
- **Salons**: warm, practical (e.g., "skin prep", "bridal trial window")
- **Gyms**: coach voice (e.g., "retention", "lured-back offer")
- **Pharmacies**: trustworthy, precise ("molecule names", "dosage", "senior norms")

### Merchant Personalization

Every message:
- Uses merchant's **owner first name** (from `MerchantContext.identity.owner_first_name`)
- References **real offers** from `MerchantContext.offers`
- Honors **language preference** (Hindi-English mix for customer-facing)
- Anchors on **their actual data** (CTR vs peer median, specific customer cohorts)

### Message Constraints

All messages respect:
- ✅ **≤ 320 characters** (hard limit for WhatsApp)
- ✅ **No URLs** (Meta rejects)
- ✅ **Single primary CTA** (binary YES/NO or open-ended, never multi-choice except booking)
- ✅ **Specificity wins** — factual numbers/dates, not generic "10% off"
- ✅ **No fabrication** — only data from provided contexts

---

## Multi-Turn Conversation Handling

The `/v1/reply` endpoint implements a simple state machine:

1. **Auto-reply detection** — identifies "Thank you for contacting..." canned messages
   - 1st auto-reply → wait 4 hours
   - 2nd auto-reply → wait 24 hours
   - 3+ auto-replies → close conversation

2. **Intent recognition** — detects positive/negative/clarifying signals
   - Positive ("yes", "sure") → offer next step
   - Negative ("stop", "not interested") → close gracefully
   - Unclear → ask for clarification

3. **Conversation tracking** — stores turns per `conversation_id` for state

---

## What's NOT Built (By Design)

**Single-prompt LLM**: To keep it free and deterministic, the bot uses **no LLM calls**. Instead:
- All composition is rule-based, templated logic
- Merchants see predictable, brand-consistent messages
- No hallucination risk (no invented offers/data)
- Zero API cost

**If upgrading**: Would add:
- Free tier Claude/GPT calls for richer context understanding
- Retrieval over category digest items
- Smarter reply classification

---

## Testing Locally

### 1. Start the bot:
```bash
python bot.py
```
Server runs on `http://localhost:8080`

### 2. Run the judge simulator:
```bash
export BOT_URL=http://localhost:8080
python judge_simulator.py --scenario warmup
python judge_simulator.py --scenario phase2_short --duration 10
```

### 3. Test a single composition:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_001"]}' \
  http://localhost:8080/v1/tick
```

---

## Dataset & Submissions

- **Dataset**: 50 merchants (10 per category) + 200 customers + 100 triggers
- **Test pairs**: 30 canonical (merchant, trigger) pairs in `submission.jsonl`
- **Submission format**: 30 JSONL lines, one per test pair
- **All paired**: Each submission references actual data from `expanded/` directory

---

## Key Tradeoffs

### What we prioritized:
1. **Determinism**: Reproducible output, no LLM variance
2. **Specificity**: Every message anchored on real data points
3. **Cost**: Free (no API calls, can run locally forever)
4. **Simplicity**: 80-line composer, easy to debug + iterate

### What we deprioritized:
1. **Sophistication**: No semantic understanding, just rules
2. **Conversation depth**: Multi-turn is simple state machine, not full dialogue
3. **Generalization**: Never seen merchant names pre-hardcoded; would fail new data
4. **Variety**: Tends toward templates; low variance in phrasing

---

## Results Expected

Based on the 5-dimension rubric:

| Dimension | Expected Score | Why |
|---|---|---|
| **Specificity** | 7-8/10 | Real data, some citations; could be sharper |
| **Category fit** | 8-9/10 | Voice adapted per category; vocabulary correct |
| **Merchant fit** | 8-9/10 | Uses real names, offers, language; strong personalization |
| **Trigger relevance** | 7-8/10 | Clear reason for messaging; fallback is generic |
| **Engagement compulsion** | 6-7/10 | Binary CTAs, effort externalization; but predictable phrasing |

**Estimated total**: **36-41 / 50**

The bot wins on **fit + specificity** but loses on **compulsion** (limited by rule-based phrasing).

---

## Lessons for Next Iteration

If rebuilding with LLM:
1. Add free tier Claude to generate richer bodies while respecting constraints
2. Retrieve top 3 digest items per category, let LLM pick the most relevant
3. Use function calling to look up peer-comparable merchants (adds social proof)
4. Track conversation sentiment; adjust tone based on engagement signals

---

## Files Included

- `bot.py` — FastAPI server (all 5 endpoints + composer logic)
- `submission.jsonl` — 30 test pairs with composed messages
- `generate_submission.py` — script to generate submission from dataset
- `expanded/` — full dataset (5 categories, 50 merchants, 200 customers, 100 triggers)
- `README.md` (this file)

