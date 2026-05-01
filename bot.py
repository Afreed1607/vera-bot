"""
Vera AI Bot — Minimal, Deterministic Merchant Engagement Assistant
Built for the magicpin AI Challenge

Approach:
- Rule-based composition with LLM fallback (uses free tier APIs)
- Stores contexts in-memory (sufficient for 60-min test)
- Dispatches by trigger.kind to appropriate composer
- Multi-turn support with simple state tracking
"""

import os
import time
import json
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Try to use free LLM; fallback to rule-based if not available
try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ============================================================================
# Models
# ============================================================================

class CtxBody(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str

class TickBody(BaseModel):
    now: str
    available_triggers: list[str] = []

class ReplyBody(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str
    message: str
    received_at: str
    turn_number: int

class ComposedMessage(BaseModel):
    body: str
    cta: str
    send_as: str
    suppression_key: str
    rationale: str

# ============================================================================
# Composer Logic
# ============================================================================

@dataclass
class ComposedAction:
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str]
    send_as: str
    trigger_id: str
    template_name: str
    template_params: list[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str

def compose_research_digest(category: dict, merchant: dict, trigger: dict) -> ComposedAction:
    """Compose a research digest message for a merchant."""
    merchant_id = merchant["merchant_id"]
    category_slug = category["slug"]
    owner_name = merchant.get("identity", {}).get("owner_first_name", "there")

    # Extract digest item
    payload = trigger.get("payload", {})
    top_item_id = payload.get("top_item_id")
    digest_items = category.get("digest", [])
    digest_item = next((d for d in digest_items if d.get("id") == top_item_id), digest_items[0] if digest_items else None)

    if not digest_item:
        digest_item = digest_items[0] if digest_items else {"title": "industry research", "source": "unknown"}

    # Build message
    title = digest_item.get("title", "industry research")
    source = digest_item.get("source", "recent study")
    trial_n = digest_item.get("trial_n", "N/A")

    if category_slug == "dentists":
        body = (
            f"Hi {owner_name}! {source} (n={trial_n}): {title}. "
            f"Relevant to your practice—want me to draft a patient note?"
        )
    elif category_slug == "salons":
        body = (
            f"Hi {owner_name}! New: {title} (via {source}). "
            f"Worth sharing with clients—turn into a post?"
        )
    elif category_slug == "restaurants":
        body = (
            f"Hey {owner_name}, {source}: {title}. "
            f"Could affect your menu strategy—want talking points for your team?"
        )
    elif category_slug == "gyms":
        body = (
            f"Hi {owner_name}, fitness research: {title} (n={trial_n}). "
            f"Share with members—want a summary + social post?"
        )
    else:  # pharmacies
        body = (
            f"Hi {owner_name}, compliance info: {title}. "
            f"Worth a team memo—shall I draft one?"
        )

    # Truncate to 320 chars
    if len(body) > 320:
        body = body[:310] + "..."

    return ComposedAction(
        conversation_id=f"conv_{merchant_id}_research_{digest_item.get('id', '')}",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger["id"],
        template_name=f"vera_research_digest_{category_slug[:3]}_v1",
        template_params=[owner_name, title, source],
        body=body,
        cta="binary_yes_no",
        suppression_key=trigger.get("suppression_key", f"research:{category_slug}:{top_item_id}"),
        rationale=f"Research digest with specificity (n={trial_n}, source). Direct ask."
    )

def compose_perf_dip(category: dict, merchant: dict, trigger: dict) -> ComposedAction:
    """Compose a performance dip recovery message."""
    merchant_id = merchant["merchant_id"]
    owner_name = merchant.get("identity", {}).get("owner_first_name", "there")
    perf = merchant.get("performance", {})
    calls_pct = perf.get("delta_7d", {}).get("calls_pct", 0)
    peer_stats = category.get("peer_stats", {})

    body = (
        f"Hi {owner_name}, your calls dipped {abs(calls_pct)*100:.0f}% this week — "
        f"noticed. Let's figure out why. "
        f"Could be seasonal. Want me to check how peers in your radius are doing, "
        f"+ suggest a mini-nudge for next week?"
    )

    if len(body) > 320:
        body = body[:310] + "..."

    return ComposedAction(
        conversation_id=f"conv_{merchant_id}_perf_dip",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger["id"],
        template_name="vera_perf_recovery_v1",
        template_params=[owner_name, f"{abs(calls_pct)*100:.0f}%"],
        body=body,
        cta="binary_yes_no",
        suppression_key=trigger.get("suppression_key", f"perf_dip:{merchant_id}"),
        rationale="Performance dip detected. Loss-aversion framing + diagnostic offer."
    )

def compose_recall_reminder(category: dict, merchant: dict, trigger: dict, customer: dict) -> ComposedAction:
    """Compose a customer recall reminder message on behalf of merchant."""
    merchant_id = merchant["merchant_id"]
    customer_id = customer["customer_id"]

    cust_name = customer.get("identity", {}).get("name", "Customer").split()[0]  # First name only
    merchant_name = merchant.get("identity", {}).get("name", "Our clinic")
    lang_pref = customer.get("identity", {}).get("language_pref", "en")

    # Get real offers if available
    offers = merchant.get("offers", [])
    offer_title = offers[0].get("title", "service") if offers else "service"
    offer_price = offers[0].get("price", "₹599") if offers else "₹599"
    
    # Ensure offer_price is clean (remove duplicates if present)
    if " @ " in offer_price:
        offer_price = offer_price.split(" @ ")[0]  # Take first price only

    # Build message with language pref
    if "hi" in lang_pref.lower():
        body = (
            f"Hi {cust_name}, {merchant_name} yahan 🏥 "
            f"Aapki last visit se 6 months ho gaye — "
            f"recall due. "
            f"Slots ready hain. "
            f"{offer_title} @ {offer_price}. "
            f"Reply YES to book."
        )
    else:
        body = (
            f"Hi {cust_name}, {merchant_name} here 🏥 "
            f"It's been 6 months—your recall is due. "
            f"Slots available. "
            f"{offer_title} @ {offer_price}. "
            f"Reply YES to book."
        )

    if len(body) > 320:
        body = body[:310] + "..."

    return ComposedAction(
        conversation_id=f"conv_{customer_id}_recall_{merchant_id}",
        merchant_id=merchant_id,
        customer_id=customer_id,
        send_as="merchant_on_behalf",
        trigger_id=trigger["id"],
        template_name="merchant_recall_reminder_v1",
        template_params=[cust_name, merchant_name, offer_title, offer_price],
        body=body,
        cta="binary_yes_no",
        suppression_key=trigger.get("suppression_key", f"recall:{customer_id}:6mo"),
        rationale=f"Recall due. Language: {lang_pref}. Specific offer + booking CTA."
    )

def compose_curious_ask(category: dict, merchant: dict, trigger: dict) -> ComposedAction:
    """Compose a curiosity-driven merchant engagement message."""
    merchant_id = merchant["merchant_id"]
    owner_name = merchant.get("identity", {}).get("owner_first_name", "there")

    body = (
        f"Quick check {owner_name} — what's the most-asked service at your store this week? "
        f"I'll turn it into a Google post + a ready-reply for customers. 5 min of your time."
    )

    if len(body) > 320:
        body = body[:310] + "..."

    return ComposedAction(
        conversation_id=f"conv_{merchant_id}_curious_ask",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger["id"],
        template_name="vera_curious_ask_v1",
        template_params=[owner_name],
        body=body,
        cta="open_ended",
        suppression_key=trigger.get("suppression_key", f"curious:{merchant_id}"),
        rationale="Merchant engagement via low-stakes question. Curiosity + reciprocity levers."
    )

def compose_offer_spotlight(category: dict, merchant: dict, trigger: dict) -> ComposedAction:
    """Compose a spotlight on merchant's active offer."""
    merchant_id = merchant["merchant_id"]
    owner_name = merchant.get("identity", {}).get("owner_first_name", "there")
    offers = merchant.get("offers", [])

    if not offers:
        # Fallback to compose_curious_ask if no offers
        return compose_curious_ask(category, merchant, trigger)

    offer = offers[0]
    offer_title = offer.get("title", "your offer")

    body = (
        f"Hi {owner_name}, your {offer_title} is live! "
        f"Want me to spot it in a Google post + push it to your 3-month-inactive customers?"
    )

    if len(body) > 320:
        body = body[:310] + "..."

    return ComposedAction(
        conversation_id=f"conv_{merchant_id}_offer_spotlight",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger["id"],
        template_name="vera_offer_push_v1",
        template_params=[owner_name, offer_title],
        body=body,
        cta="binary_yes_no",
        suppression_key=trigger.get("suppression_key", f"offer:{merchant_id}:{offer.get('id', '')}"),
        rationale="Spotlight on active offer. Effort externalization (we do the work). Binary CTA."
    )

def compose_message(
    category: dict,
    merchant: dict,
    trigger: dict,
    customer: Optional[dict] = None
) -> ComposedAction:
    """Main composer: route by trigger kind."""

    trigger_kind = trigger.get("kind", "unknown")
    merchant_id = merchant["merchant_id"]
    owner_name = merchant.get("identity", {}).get("owner_first_name", "there")

    if trigger_kind == "research_digest":
        return compose_research_digest(category, merchant, trigger)
    elif trigger_kind == "perf_dip":
        return compose_perf_dip(category, merchant, trigger)
    elif trigger_kind == "recall_due" and customer:
        return compose_recall_reminder(category, merchant, trigger, customer)
    elif trigger_kind == "curious_ask_due":
        return compose_curious_ask(category, merchant, trigger)
    elif trigger_kind in ["perf_spike", "milestone_reached"]:
        return compose_offer_spotlight(category, merchant, trigger)
    elif trigger_kind == "compliance_update":
        # New: Compliance/regulatory trigger
        payload = trigger.get("payload", {})
        compliance_item = payload.get("title", "compliance update")
        body = (
            f"Hi {owner_name}, new compliance requirement: {compliance_item}. "
            f"You'll want your team aware. Need me to draft a memo?"
        )
        return ComposedAction(
            conversation_id=f"conv_{merchant_id}_compliance",
            merchant_id=merchant_id,
            customer_id=None,
            send_as="vera",
            trigger_id=trigger["id"],
            template_name="vera_compliance_alert_v1",
            template_params=[owner_name, compliance_item],
            body=body[:320],
            cta="binary_yes_no",
            suppression_key=trigger.get("suppression_key", f"compliance:{trigger_kind}"),
            rationale="Compliance alert. Specific requirement. Direct ask."
        )
    elif trigger_kind == "customer_feedback_summary":
        # New: Customer feedback trigger
        payload = trigger.get("payload", {})
        sentiment = payload.get("sentiment", "mixed")
        summary = payload.get("summary", "recent feedback")
        body = (
            f"Hi {owner_name}, {sentiment} customer feedback this week: {summary}. "
            f"Want me to suggest action items?"
        )
        return ComposedAction(
            conversation_id=f"conv_{merchant_id}_feedback",
            merchant_id=merchant_id,
            customer_id=None,
            send_as="vera",
            trigger_id=trigger["id"],
            template_name="vera_feedback_alert_v1",
            template_params=[owner_name, sentiment],
            body=body[:320],
            cta="binary_yes_no",
            suppression_key=trigger.get("suppression_key", f"feedback:{trigger_kind}"),
            rationale="Customer feedback summary. Sentiment-tagged. Actionable."
        )
    elif trigger_kind == "offer_expiry_due":
        # New: Offer expiry reminder
        payload = trigger.get("payload", {})
        offers = merchant.get("offers", [])
        if offers:
            offer = offers[0]
            offer_title = offer.get("title", "your offer")
            days_left = payload.get("days_left", 2)
            body = (
                f"Hi {owner_name}, {offer_title} expires in {days_left} days! "
                f"Want to extend it or push it out to inactive customers?"
            )
        else:
            body = (
                f"Hi {owner_name}, a key offer is expiring soon. "
                f"Want me to suggest alternatives?"
            )
        return ComposedAction(
            conversation_id=f"conv_{merchant_id}_offer_expiry",
            merchant_id=merchant_id,
            customer_id=None,
            send_as="vera",
            trigger_id=trigger["id"],
            template_name="vera_offer_expiry_v1",
            template_params=[owner_name],
            body=body[:320],
            cta="binary_yes_no",
            suppression_key=trigger.get("suppression_key", f"expiry:{trigger_kind}"),
            rationale="Offer expiry imminent. Time-sensitive. Action required."
        )
    else:
        # Fallback: more specific based on trigger payload
        payload = trigger.get("payload", {})
        title = payload.get("title", "")
        urgency = payload.get("urgency", "normal")
        
        if title:
            # Use the trigger title if available
            body = (
                f"Hi {owner_name}, quick update: {title}. "
                f"Wanted to flag it—impact for your business?"
            )
        else:
            # Generic but still actionable
            body = (
                f"Hi {owner_name}, have a quick question about your business. "
                f"Any blockers this week I can help with?"
            )
        
        return ComposedAction(
            conversation_id=f"conv_{merchant_id}_generic_{trigger_kind}",
            merchant_id=merchant_id,
            customer_id=None,
            send_as="vera",
            trigger_id=trigger["id"],
            template_name="vera_generic_checkin_v1",
            template_params=[owner_name, trigger_kind],
            body=body[:320],
            cta="open_ended",
            suppression_key=trigger.get("suppression_key", f"generic:{merchant_id}:{trigger_kind}"),
            rationale=f"Unmapped trigger kind: {trigger_kind}. Generic engagement."
        )

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(title="Vera Bot", version="0.1.0")
START_TIME = time.time()

# In-memory stores
contexts: dict[tuple[str, str], dict] = {}  # (scope, context_id) -> {version, payload}
conversations: dict[str, dict] = {}  # conversation_id -> {turns: [...], last_sent_body: str}
suppressed: set[str] = set()  # suppression keys that should not be sent

@app.get("/")
async def root():
    """Root endpoint - redirects to healthz."""
    return {
        "message": "Vera Bot is running ✓",
        "endpoints": {
            "health": "/v1/healthz",
            "metadata": "/v1/metadata",
            "context": "POST /v1/context",
            "tick": "POST /v1/tick",
            "reply": "POST /v1/reply"
        }
    }

@app.get("/v1/healthz")
async def healthz():
    """Health check endpoint."""
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _), _ in contexts.items():
        counts[scope] = counts.get(scope, 0) + 1

    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    }

@app.get("/v1/metadata")
async def metadata():
    """Bot metadata."""
    return {
        "team_name": "Solo Builder",
        "team_members": ["Human Coder"],
        "model": "rule-based + optional free LLM",
        "approach": "Trigger-dispatched rule-based composer with merchant fit + category voice",
        "contact_email": "solo@example.com",
        "version": "0.1.0",
        "submitted_at": "2026-04-29T00:00:00Z"
    }

@app.post("/v1/context")
async def push_context(body: CtxBody):
    """Receive and store a context (category, merchant, trigger, or customer)."""
    key = (body.scope, body.context_id)
    cur = contexts.get(key)

    # Check for stale version
    if cur and cur["version"] >= body.version:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": cur["version"]
        }

    # Store new version
    contexts[key] = {
        "version": body.version,
        "payload": body.payload,
        "received_at": datetime.utcnow().isoformat() + "Z"
    }

    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/v1/tick")
async def tick(body: TickBody):
    """
    Periodic wake-up. Judge tells us what triggers are available.
    We decide which ones are worth sending for.
    """
    actions = []

    for trg_id in body.available_triggers:
        # Get trigger context
        trg_data = contexts.get(("trigger", trg_id), {})
        trg = trg_data.get("payload", {})
        if not trg:
            continue

        # Skip if already suppressed
        suppression_key = trg.get("suppression_key", "")
        if suppression_key in suppressed:
            continue

        merchant_id = trg.get("merchant_id")
        customer_id = trg.get("customer_id")
        trigger_scope = trg.get("scope", "merchant")

        # Get merchant context
        merchant_data = contexts.get(("merchant", merchant_id), {})
        merchant = merchant_data.get("payload")
        if not merchant:
            continue

        # Get category context
        category_slug = merchant.get("category_slug")
        category_data = contexts.get(("category", category_slug), {})
        category = category_data.get("payload")
        if not category:
            continue

        # Get customer context if customer-scoped
        customer = None
        if trigger_scope == "customer" and customer_id:
            customer_data = contexts.get(("customer", customer_id), {})
            customer = customer_data.get("payload")

        # Compose message
        try:
            composed = compose_message(category, merchant, trg, customer)

            # Validate body length
            if len(composed.body) > 320:
                # Truncate
                composed.body = composed.body[:310] + "..."

            # Add to actions
            actions.append({
                "conversation_id": composed.conversation_id,
                "merchant_id": composed.merchant_id,
                "customer_id": composed.customer_id,
                "send_as": composed.send_as,
                "trigger_id": composed.trigger_id,
                "template_name": composed.template_name,
                "template_params": composed.template_params,
                "body": composed.body,
                "cta": composed.cta,
                "suppression_key": composed.suppression_key,
                "rationale": composed.rationale
            })

            # Track conversation and mark as suppressed
            if composed.conversation_id not in conversations:
                conversations[composed.conversation_id] = {
                    "turns": [],
                    "last_sent_body": composed.body,
                    "trigger_id": trg_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer_id
                }
            
            # Add suppression key to prevent re-sending
            if suppression_key:
                suppressed.add(suppression_key)

        except Exception as e:
            print(f"Error composing for {trg_id}: {e}")
            continue

    return {"actions": actions}

@app.post("/v1/reply")
async def reply(body: ReplyBody):
    """Handle a merchant/customer reply in a conversation."""
    conv_id = body.conversation_id

    if conv_id not in conversations:
        conversations[conv_id] = {
            "turns": [],
            "last_sent_body": "",
            "auto_reply_count": 0
        }

    conv = conversations[conv_id]
    
    # Record the reply
    turn = {
        "from": body.from_role,
        "message": body.message,
        "turn": body.turn_number
    }
    conv["turns"].append(turn)

    message_lower = body.message.lower().strip()

    # ========== AUTO-REPLY DETECTION ==========
    auto_reply_phrases = [
        "thank you for contacting",
        "our team will respond",
        "auto-reply",
        "out of office",
        "away from office",
        "away from the office",
        "i am out of office",
        "thanks for your message",
        "will get back to you",
        "will respond"
    ]
    is_auto_reply = any(phrase in message_lower for phrase in auto_reply_phrases)

    if is_auto_reply:
        conv["auto_reply_count"] = conv.get("auto_reply_count", 0) + 1
        
        if conv["auto_reply_count"] >= 3:
            return {
                "action": "end",
                "body": "I see you're out of office. Will follow up next week.",
                "rationale": "Auto-reply detected 3+ times. Merchant unavailable."
            }
        elif conv["auto_reply_count"] >= 2:
            return {
                "action": "wait",
                "wait_seconds": 86400,
                "rationale": "Second auto-reply. Waiting 24h for availability."
            }
        else:
            return {
                "action": "wait",
                "wait_seconds": 14400,
                "rationale": "Auto-reply detected. Waiting 4h before retry."
            }

    # ========== NEGATIVE SIGNALS ==========
    negative_signals = [
        "not interested",
        "stop",
        "no thanks",
        "unsubscribe",
        "remove me",
        "don't contact",
        "not relevant"
    ]
    if any(sig in message_lower for sig in negative_signals):
        return {
            "action": "end",
            "body": "Understood. We'll respect your preference.",
            "rationale": "Merchant opted out."
        }

    # ========== POSITIVE SIGNALS ==========
    positive_signals = ["yes", "ok", "sure", "please", "go", "yup", "yeah", "absolutely"]
    is_positive = any(word in message_lower for word in positive_signals)

    if is_positive:
        # Check if customer is trying to book a time
        has_time_info = any(word in message_lower for word in ["wed", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "am", "pm", "o'clock", "6pm", "5pm", "4pm", "3pm", "2pm", "1pm", "booking", "book"])
        
        if has_time_info:
            # Booking confirmation - extract merchant context for personalization
            merchant_id = conv.get("merchant_id")
            customer_id = conv.get("customer_id")
            
            if merchant_id and customer_id:
                merchant_data = contexts.get(("merchant", merchant_id), {})
                merchant = merchant_data.get("payload", {})
                merchant_name = merchant.get("identity", {}).get("name", "our clinic")
                
                customer_data = contexts.get(("customer", customer_id), {})
                customer = customer_data.get("payload", {})
                cust_name = customer.get("identity", {}).get("name", "Customer").split()[0] if customer else "you"
                
                return {
                    "action": "send",
                    "body": f"Perfect! Booking confirmed for {cust_name} at {merchant_name}. You'll get a reminder 2h before. Thanks!",
                    "cta": "none",
                    "rationale": "Booking request with specific time. Confirming with date/merchant."
                }
            else:
                return {
                    "action": "send",
                    "body": "Great! Your booking is confirmed. Check your email for details.",
                    "cta": "none",
                    "rationale": "Booking confirmation."
                }
        else:
            # General positive reply
            return {
                "action": "send",
                "body": "Awesome! I'm working on that now. You'll hear back within 30 min.",
                "cta": "none",
                "rationale": "Positive engagement. Setting expectations."
            }

    # ========== UNCLEAR / QUESTION ==========
    question_signals = ["?", "what", "how", "which", "when", "where", "why", "tell me"]
    is_question = any(sig in message_lower for sig in question_signals)
    
    if is_question:
        return {
            "action": "send",
            "body": "Good question! Can you share a bit more context? That helps me give better suggestions.",
            "cta": "open_ended",
            "rationale": "Merchant asking clarifying question. Encourage more info."
        }

    # ========== DEFAULT: ACKNOWLEDGMENT ==========
    return {
        "action": "send",
        "body": "Thanks for getting back to me! Anything else I can help clarify?",
        "cta": "open_ended",
        "rationale": "Generic acknowledgment for neutral replies."
    }

@app.post("/v1/teardown")
async def teardown():
    """Optional: clear state at end of test."""
    contexts.clear()
    conversations.clear()
    suppressed.clear()
    return {"status": "cleared"}

# ============================================================================
# Utilities for local testing
# ============================================================================

def load_json_file(path: str) -> dict:
    """Load a JSON file."""
    with open(path) as f:
        return json.load(f)

def save_submission(output_path: str, pairs: list[dict]):
    """Save submission.jsonl with composed messages."""
    with open(output_path, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")

if __name__ == "__main__":
    # For local dev: python bot.py
    import uvicorn
    import sys
    import os
    # Use localhost for local testing, 0.0.0.0 for production
    host = "127.0.0.1" if "local" in sys.argv else "0.0.0.0"
    port = int(os.environ.get('PORT', 8080))
    print(f"\n🤖 Vera Bot starting on http://{host}:{port}")
    print("📌 Visit: http://localhost:8080/v1/healthz\n")
    uvicorn.run(app, host=host, port=port)
