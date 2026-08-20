# 📈 OpenShorts — Reels Content Plan
### 10 high-demand trading/finance topics × a 1,000-reel engine per topic = 10,000 unique reels

> Purpose: a ready-to-use content system for automated reels with OpenShorts
> (AI Shorts prompt → reel, or Clip Generator long video → clips) and the Android app.
> All templates are **educational only** — no buy/sell/hold recommendations (see [Compliance](#-compliance--sebi-guardrails)).

---

## 1. What the public actually wants (demand snapshot, 2026)

**Finance is the #1 content category for short-form video**, not just among niches but by
advertiser economics — the strongest proxy for sustained public demand:

- Finance/investing shorts carry the **highest RPM of any niche** (~$0.15–0.45 for Shorts,
  $10–25 for long-form) because banks, brokers and fintechs pay the most for attention
  ([FluxNote](https://fluxnote.io/guides/best-niches-youtube-shorts-monetization),
  [OutlierKit](https://outlierkit.com/blog/youtube-rpm-finance-niche)).
- In India, **Instagram and YouTube dominate investor reach** — they are the primary
  platforms where retail investors consume financial content
  ([ET BFSI / CFA Institute](https://bfsi.economictimes.indiatimes.com/articles/only-6-of-finfluencers-are-sebi-registered-a-regulatory-wake-up-call/132684989)).
- Retail participation keeps rising, and the audience skews young — the average finfluencer
  audience is under 35 and prefers **short, accessible, jargon-free explanations**.
- India's top stock-market channels (15M+ subs) prove the appetite spans
  *basics → technical analysis → trading discipline*
  ([Pocketful](https://www.pocketful.in/blog/best-youtube-channels-for-stock-market-in-india/)).

**Demand patterns to exploit**

| Signal | When | Topic to push |
|---|---|---|
| Tax season (India) | Jan–Mar | #10 Taxes on trading income |
| Union Budget / RBI policy | Feb, Apr, Jun, Aug, Oct, Dec | #9 Market news explained |
| Market crash / sharp fall | Any time | #7 Psychology & mistakes, #3 Risk discipline |
| IPO wave | Clusters | #8 IPOs explained |
| Earnings season | Quarterly | #9 News explained, #2 Chart patterns |
| Evergreen | Always | #1 Basics, #5 SIPs, #6 Personal finance |

**What outperforms within the niche**

1. "X explained simply" (jargon removed) — biggest beginner pool
2. Mistakes & myth-busting — highest comments/shares
3. Number/stat shock ("70% of traders lose money") — highest stops/loops
4. Micro-niches ("SIPs for beginners") beat broad topics
5. English content earns ~2–3× more RPM than regional, but **Hindi + Hinglish
   reaches 10× more eyeballs in India** — run both tracks (the AI Shorts pipeline
   supports `en` and `es`; for Hindi use the Clip Generator on Hindi long-form or
   prompt Gemini with Hindi script instructions).

---

## 2. The 10 topics (ranked by demand)

| # | Topic | Demand driver |
|---|---|---|
| T1 | Stock Market Basics (Beginner 101) | Largest audience pool, ever-growing new investors |
| T2 | Candlesticks & Chart Patterns | Most-searched "how-to" in trading content |
| T3 | Intraday Discipline & Risk | High intent + high caution; education-only framing |
| T4 | F&O / Options Explained Simply | Massive curiosity; biggest education gap |
| T5 | Mutual Funds, SIPs & Compounding | High-RPM micro-niche, safest evergreen |
| T6 | Technical Indicators (RSI, MACD, EMA…) | Evergreen tool explainers, easy to serialize |
| T7 | Trading Psychology & Common Mistakes | Highest engagement (comments, shares) |
| T8 | IPOs & Primary Markets | Spikes with every IPO wave |
| T9 | Market News Explained (Budget/RBI/Fed) | Timely spikes, highest shareability |
| T10 | Personal Finance & Taxes for Investors | Tax-season spike; broad mass appeal |

---

## 3. The 1,000-reel engine (per topic)

Each topic = **10 subtopics × 10 hooks × 10 angles = 1,000 unique reels.**

Reel ID: `T{topic}-S{subtopic}-H{hook}-A{angle}` — e.g. `T2-S04-H07-A01`.
Reel number within a topic = `(S-1)×100 + (H-1)×10 + A`.

### The 10 universal angles

| ID | Angle | Formula |
|---|---|---|
| A1 | Myth-busting | "Stop believing that {myth}… here's the truth" |
| A2 | Mistake spotlight | "The #1 mistake {audience} make is…" |
| A3 | Rule / checklist | "3 rules before you {action}" |
| A4 | Explain like I'm new | "{Concept} explained with one chai-shop example" |
| A5 | Number shock | "{Stat} — and most people don't know this" |
| A6 | Comparison | "{Option A} vs {Option B} — the honest difference" |
| A7 | Quiz / spot-it | "Can you spot the {fake breakout / bad trade}?" |
| A8 | Micro-story | "A friend did {X}. Here's what happened…" |
| A9 | Timely explainer | "Why {index/stock/market} moved today" |
| A10 | 30-day challenge | "Try {habit} for 30 days, watch {result}" |

### Per-topic hook bank — 10 hooks each (fill `{subtopic}` from the subtopic list)

The hooks below are **universal plug-in lines**; combine any hook with any subtopic
to get 100 distinct pairings, then × 10 angles = 1,000.

| # | Hook template (open with this line) |
|---|---|
| H1 | "Nobody explains {subtopic} properly. So I will — in 40 seconds." |
| H2 | "If you're new to the market, this {subtopic} video can save you years." |
| H3 | "I wish someone told me this about {subtopic} 5 years ago." |
| H4 | "90% of people get {subtopic} wrong. Here's the 10% version." |
| H5 | "Forget everything you heard about {subtopic}. Start here." |
| H6 | "This one rule about {subtopic} changed how I trade." |
| H7 | "{Subtopic} — the mistake that costs beginners lakhs." |
| H8 | "Before your next trade, watch this {subtopic} explainer." |
| H9 | "Your broker will never tell you this about {subtopic}." |
| H10 | "Stop scrolling. {Subtopic}, in plain English/Hindi." |

**Worked example — one reel fully spelled out**

> **ID:** `T2-S04-H07-A01` · **Reel #304 of 1000** in T2 (Candlesticks)
> - **Subtopic S04:** Doji candles
> - **Hook H07:** "Doji — the mistake that costs beginners lakhs."
> - **Angle A01:** Myth-busting → "Stop believing a doji always means reversal. It means
>   *indecision*. A doji after a rally means one thing, in a range it means nothing…"
> - **CTA:** "Follow for one candlestick pattern every day. Comment 'DOJI' and I'll send
>   you a free 7-pattern checklist."

### Prompt you paste into the OpenShorts app (AI Shorts → description)

```
Create a {DURATION}-second educational reel for Indian retail investors.
Topic: {TOPIC NAME}. Subtopic: {SUBTOPIC}. Angle: {ANGLE LABEL}.
Open with this hook, word for word: "{HOOK}".
Explain in simple {LANGUAGE} with one everyday example. No jargon, no
stock names, no buy/sell advice, no profit claims.
Tone: {TONE}. End with CTA: "{CTA}".
```

Recommended app settings: `num_scripts = 3`, `style = educational` (or `ugc`),
`actor_gender` alternate per batch, `video_mode = lowcost` for volume, `voice` = Drew
(male, confident) or Rachel (female, calm).

---

## 4. Topic playbooks

### T1 · Stock Market Basics (Beginner 101)
**Subtopics:** S01 What is the stock market · S02 NSE/BSE explained · S03 What is NIFTY &
SENSEX · S04 Demat & trading account · S05 How a stock's price moves · S06 Market cap
(large/mid/small) · S07 Dividends · S08 Bonus & stock splits · S09 Bull vs bear market ·
S10 How to read a trading screen (LTP, volume, % change).
**Best angles:** A4 explain-simply, A5 number shock, A2 mistake spotlight.
**Filled prompt example:** `Create a 40-second educational reel for Indian retail
investors. Topic: Stock Market Basics. Subtopic: What is NIFTY. Angle: Explain like I'm
new. Open with this hook, word for word: "Nobody explains NIFTY properly. So I will — in
40 seconds." Explain in simple English with one everyday example…`
**Hashtags:** #Nifty #StockMarketBasics #ShareMarketIndia #InvestingForBeginners #StockMarket

### T2 · Candlesticks & Chart Patterns
**Subtopics:** S01 Candlestick anatomy (body/wick) · S02 Bullish vs bearish candle ·
S03 Doji · S04 Hammer & hanging man · S05 Engulfing patterns · S06 Support & resistance ·
S07 Head & shoulders · S08 Double top/bottom · S09 Flag & triangle continuation ·
S10 Fake breakouts.
**Best angles:** A7 spot-it quiz, A1 myth-busting, A3 checklist.
**Hashtags:** #CandlestickPatterns #PriceAction #TechnicalAnalysis #TradingForBeginners #ChartPatterns

### T3 · Intraday Discipline & Risk
**Subtopics:** S01 What intraday really is · S02 Stop-loss: non-negotiable · S03 Position
sizing · S04 Risk-reward ratio · S05 Trading plan vs impulse · S06 Overtrading ·
S07 Entry vs exit quality · S08 Daily loss limit · S09 Journaling trades · S10 The maths
of losing streaks.
**Best angles:** A2 mistakes, A3 rules, A5 stats.
**Hashtags:** #IntradayTrading #RiskManagement #StopLoss #TradingDiscipline #StockMarketIndia

### T4 · F&O / Options Explained Simply
**Subtopics:** S01 What is a derivative · S02 Futures vs options · S03 Call option ·
S04 Put option · S05 Premium & strike price · S06 Expiry & lot size · S07 Option buying
vs selling · S08 Why most option buyers lose · S09 Hedging idea · S10 SEBI margin rules
for F&O.
**Best angles:** A4 explain-simply (critical here), A2 mistakes, A1 myths.
**Hashtags:** #OptionsTrading #FuturesAndOptions #OptionBasics #Derivatives #NiftyOptions

### T5 · Mutual Funds, SIPs & Compounding
**Subtopics:** S01 What is a mutual fund · S02 SIP explained · S03 Power of compounding ·
S04 Equity vs debt funds · S05 Index funds · S06 Expense ratio & NAV · S07 ELSS & tax
saving · S08 Lump sum vs SIP · S09 Withdrawal & SWP · S10 SIP myths.
**Best angles:** A6 comparison, A5 stats, A10 30-day challenge.
**Hashtags:** #MutualFunds #SIP #Compounding #IndexFunds #InvestingBasics

### T6 · Technical Indicators
**Subtopics:** S01 Moving averages (SMA/EMA) · S02 RSI · S03 MACD · S04 Bollinger Bands ·
S05 Volume analysis · S06 Fibonacci retracement · S07 VWAP · S08 Stochastic · S09 ADX /
trend strength · S10 Indicator combos that actually help.
**Best angles:** A3 checklist, A1 myth-busting, A6 comparison (RSI vs MACD).
**Hashtags:** #RSI #MACD #TradingIndicators #TechnicalAnalysis #StockMarketTips

### T7 · Trading Psychology & Common Mistakes
**Subtopics:** S01 FOMO trades · S02 Revenge trading · S03 Averaging losers · S04 Cutting
winners early · S05 Overconfidence after a win streak · S06 Trading borrowed money ·
S07 Following Telegram tips blindly · S08 Confirmation bias · S09 Expectation vs
probability · S10 The 90% losing stat — and how to be the 10%.
**Best angles:** A8 micro-story, A2 mistakes, A5 stats.
**Hashtags:** #TradingPsychology #StockMarketMistakes #FOMO #TraderMindset #Discipline

### T8 · IPOs & Primary Markets
**Subtopics:** S01 What is an IPO · S02 Why companies list · S03 How to apply (ASBA/UPI) ·
S04 Allotment & listing day · S05 Grey market premium — what it is · S06 Listing gains
myth · S07 IPO vs buying listed shares · S08 Red flags in DRHP · S09 SME IPOs · S10
Lock-in & anchor investors.
**Best angles:** A1 myths (listing gains), A9 timely, A4 explain-simply.
**Hashtags:** #IPO #IPOAlert #PrimaryMarket #ShareMarketIndia #StockMarketNews

### T9 · Market News Explained
**Subtopics:** S01 Why markets fall/rise today · S02 Union Budget basics · S03 RBI rate
decisions · S04 Inflation & CPI · S05 Fed & global cues · S06 Crude oil & rupee ·
S07 FII vs DII flows · S08 Earnings results · S09 Sector rotations · S10 Geopolitics &
markets.
**Best angles:** A9 timely explainer, A4 simplify, A5 number shock.
**Hashtags:** #StockMarketNews #NiftyToday #MarketUpdate #RBI #Budget2026

### T10 · Personal Finance & Taxes for Investors
**Subtopics:** S01 Salary first, trading second · S02 Emergency fund before stocks ·
S03 The 50-30-20 split · S04 Tax on intraday/F&O income · S05 STCG vs LTCG · S06 Tax on
dividends · S07 Section 80C & ELSS · S08 Advance tax for traders · S09 Filing ITR as an
investor · S10 Insurance before investing.
**Best angles:** A2 mistakes, A3 checklist, A6 comparison. **Push Jan–Mar.**
**Hashtags:** #TaxSaving #IncomeTax #PersonalFinance #ITR #FinancialPlanning

---

## 5. Posting template (every reel)

**Caption (Instagram/TikTok):**
```
{HOOK LINE}
→ {One-line value promise}
💾 Save this before your next trade.
{2–4 hashtags from the topic set}

⚠️ Educational content. Not investment advice. Markets are subject to risks.
```

**On-screen/script CTA rotation (cycle these):**
1. "Follow for one {topic} explainer every day."
2. "Comment '{WORD}' and I'll send you the free {checklist/PDF}."
3. "Share this with one friend who's new to the market."
4. "Save this — you'll need it at 9:15 AM."

---

## 6. Cadence & scheduling

| Pace | Reels/day | Time to finish all 10,000 |
|---|---|---|
| Conservative | 2 | ~13.7 years |
| Standard | 3 | ~9.1 years |
| Aggressive | 5 | ~5.5 years |
| Max (AI-assisted) | 10 | ~2.7 years |

**Recommended mix:** 3 evergreen (T1–T7 rotation) + 1 timely (T9/T8) per day.
Best posting windows (IST): **8–9 AM** (pre-market), **12–1 PM** (lunch), **7–9 PM**
(post-market recap). Use the app's scheduling sheet (date/time/Asia/Kolkata).

---

## 7. ⚠️ Compliance & SEBI guardrails (non-negotiable)

Per the CFA Institute *Clicks and Credibility 2.0* report: only ~6% of Indian finfluencers
are SEBI-registered while ~33% still issue stock recommendations — and SEBI is actively
acting against them
([ET BFSI](https://bfsi.economictimes.indiatimes.com/articles/only-6-of-finfluencers-are-sebi-registered-a-regulatory-wake-up-call/132684989)).

**Rules baked into every template above:**
1. **Education only** — no buy/sell/hold, no stock names as "picks", no target prices.
2. **No performance promises** — never "this made me ₹X", never guaranteed returns.
3. **Always disclaim** — the caption disclaimer line is mandatory on every post.
4. **Disclose affiliations** — any broker/app link must be marked as promo.
5. **Verify numbers** — stats used in A5/A9 must come from public data (NSE, RBI,
   exchange filings); Gemini-sourced numbers must be checked before posting.
6. **Review before auto-publish** — a human must glance at every AI-written script
   (the app supports review-then-publish; never blind-auto-post).

---

## 8. How to use this with OpenShorts

> **⚡ This whole plan is already automated.** The repo ships a cron-driven bot —
> `automation/reels_bot.py` + `.github/workflows/reels-bot.yml` — that picks the
> next reel from this exact 10×10×10 bank every day, generates it via the
> OpenShorts API, and posts it to Instagram automatically. The topic weights,
> hooks, angles, subtopics, myths, stats, CTAs and hashtags in this document are
> encoded 1:1 in `automation/content/topics.json`. See `automation/README.md`
> for the secrets to add and how to switch it on.
>
> **Recent upgrades (v2):**
> - 🛡️ **Gemini verification gate** — every script is fact-checked and
>   compliance-audited (no advice, no invented numbers, good faith) before
>   anything is generated; unsafe scripts are never posted.
> - 📰 **News reels** — the morning slot builds reels from the latest headlines
>   (sarkarikyp.com, Google News, Moneycontrol, ET, Livemint), strictly from
>   source facts, with attribution.
> - 🔁 **Bilingual reels** — each reel randomly starts in Hindi or English and
>   flips mid-reel; subtitles always run in the opposite language of the speech.
>
> **Recent upgrades (v3):**
> - 🎭 **100 AI influencers** — `automation/content/influencers.json`: 10 topics ×
>   10 personas (5 men + 5 women, ages 25/30/35/40/45), each with a realistic
>   face sheet, age-appropriate dress code, catchphrase, city, profession and
>   voice. Rotation is automatic; `avatar_url` pins a persona to one consistent
>   face.
> - 💬 **Engagement format** — every script includes a mid-roll viewer question,
>   a micro-story/example opening, and a comment-inviting CTA (verified by the
>   Gemini gate).
> - 💰 **Growth & revenue playbook** — see `automation/README.md` §4d for the
>   roadmap to India's top finance page.

1. Pick a reel ID (e.g. `T2-S04-H07-A01`), assemble hook + subtopic + angle from the tables.
2. Paste the master prompt (Section 3) into the **Android app → AI Shorts → description**.
3. Pick a script (3 are generated), tap **Generate reel**, preview.
4. Add the caption + hashtags from the topic playbook, schedule or **Publish to Instagram**.
5. Track which IDs perform; double down on the winning subtopic × angle cells.
