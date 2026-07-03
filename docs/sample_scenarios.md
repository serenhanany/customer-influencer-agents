# Sample Scenarios

These scenarios validate the Customer and Influencer agent personas against realistic HappyTuna crisis events. Each scenario specifies the injected attribute values and the expected JSON output so results can be compared against a known baseline.

---

## How to Read This File

Each scenario contains:

- **Event** — the crisis event fed to both agents.
- **Customer Persona** — injected attribute values for that run.
- **Influencer Persona** — injected attribute values for that run.
- **Expected Customer Output** — the JSON the Customer Agent should produce.
- **Expected Influencer Output** — the JSON the Influencer Agent should produce.

---

# Scenario 1 – Unverified Salmonella Rumor

## Event

An anonymous social media account posts that a batch of HappyTuna canned tuna caused salmonella poisoning. No official statement has been issued. The post is gaining traction but has no supporting evidence.

## Customer Persona

```json
{
  "loyalty": 0.65,
  "trust_level": 0.70,
  "risk_sensitivity": 0.85,
  "price_sensitivity": 0.40,
  "complaint_tendency": 0.50,
  "forgiveness_level": 0.60,
  "switch_tendency": 0.45
}
```

## Influencer Persona

```json
{
  "audience_size": 120000,
  "influence_level": 0.72,
  "credibility": 0.88,
  "sensationalism": 0.20,
  "controversy_seeking": 0.15,
  "brand_support": 0.60,
  "viral_probability": 0.40,
  "content_style": "analytical",
  "platform": "twitter"
}
```

## Expected Customer Output

```json
{
  "action": "wait_for_more_information",
  "emotion": "concern",
  "reasoning": "The rumor has no official backing. My trust in HappyTuna is still moderate-high and my loyalty prevents me from overreacting to an unverified post. I will monitor for an official statement before taking further action.",
  "trust_score": 0.58,
  "confidence": 0.74,
  "next_action_required": true
}
```

## Expected Influencer Output

```json
{
  "action": "wait_before_posting",
  "tone": "neutral",
  "post": "",
  "reasoning": "The claim is unverified. My credibility depends on accuracy. Publishing an alarm without evidence would damage my standing and unnecessarily panic my audience.",
  "credibility_score": 0.88,
  "viral_probability": 0.10,
  "estimated_public_impact": "low",
  "confidence": 0.82
}
```

---

# Scenario 2 – Fake Illness Video Goes Viral

## Event

A TikTok video claiming the creator was hospitalized after eating HappyTuna reaches 500,000 views within 24 hours. No medical or laboratory evidence is provided. The company has not yet responded publicly.

## Customer Persona

```json
{
  "loyalty": 0.30,
  "trust_level": 0.40,
  "risk_sensitivity": 0.90,
  "price_sensitivity": 0.70,
  "complaint_tendency": 0.80,
  "forgiveness_level": 0.25,
  "switch_tendency": 0.75
}
```

## Influencer Persona

```json
{
  "audience_size": 850000,
  "influence_level": 0.88,
  "credibility": 0.55,
  "sensationalism": 0.82,
  "controversy_seeking": 0.75,
  "brand_support": 0.20,
  "viral_probability": 0.78,
  "content_style": "emotional",
  "platform": "tiktok"
}
```

## Expected Customer Output

```json
{
  "action": "stop_buying",
  "emotion": "anger",
  "reasoning": "A viral video with this reach is alarming. My risk sensitivity is very high and my loyalty to HappyTuna is low, so I will not give the company the benefit of the doubt. I am stopping purchases immediately and may return the product I have at home.",
  "trust_score": 0.18,
  "confidence": 0.85,
  "next_action_required": true
}
```

## Expected Influencer Output

```json
{
  "action": "criticize_company",
  "tone": "alarming",
  "post": "500K views and HappyTuna still hasn't said a word. When a company goes silent on a health scare this big, that silence speaks volumes. I'm not buying until we get answers. #HappyTunaScandal",
  "reasoning": "High viral moment, company silence, and my controversy-seeking personality push me toward an aggressive post. My sensationalism amplifies the emotional angle, and my platform rewards short punchy reactions.",
  "credibility_score": 0.48,
  "viral_probability": 0.82,
  "estimated_public_impact": "high",
  "confidence": 0.79
}
```

---

# Scenario 3 – Official Voluntary Recall Announced

## Event

HappyTuna issues an official press release announcing a voluntary recall of Production Line A products due to a confirmed salmonella risk. The company provides a recall hotline, a refund policy, and commits to a third-party safety audit.

## Customer Persona

```json
{
  "loyalty": 0.80,
  "trust_level": 0.55,
  "risk_sensitivity": 0.70,
  "price_sensitivity": 0.35,
  "complaint_tendency": 0.40,
  "forgiveness_level": 0.72,
  "switch_tendency": 0.30
}
```

## Influencer Persona

```json
{
  "audience_size": 230000,
  "influence_level": 0.68,
  "credibility": 0.82,
  "sensationalism": 0.30,
  "controversy_seeking": 0.20,
  "brand_support": 0.55,
  "viral_probability": 0.45,
  "content_style": "investigative",
  "platform": "youtube"
}
```

## Expected Customer Output

```json
{
  "action": "return_product",
  "emotion": "concern",
  "reasoning": "The company confirmed the contamination and is offering a refund, which shows accountability. My high forgiveness level means I am willing to give them a chance to fix this. I will return the product, use the hotline, and monitor the audit results before deciding whether to buy again.",
  "trust_score": 0.62,
  "confidence": 0.90,
  "next_action_required": true
}
```

## Expected Influencer Output

```json
{
  "action": "share_news",
  "tone": "informative",
  "post": "HappyTuna has issued a voluntary recall for Production Line A over a confirmed salmonella risk. They're offering full refunds and have called for a third-party safety audit. I'll be covering the audit process closely — transparency from here matters. Full recall details linked below.",
  "reasoning": "The company took a responsible step. My investigative style means I will track whether the audit delivers. Sharing the factual recall now protects my audience and maintains my credibility.",
  "credibility_score": 0.85,
  "viral_probability": 0.48,
  "estimated_public_impact": "medium",
  "confidence": 0.91
}
```
