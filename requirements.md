# Krise Engine - Requirements Document
## Multi-Agent Intent Orchestrator for AI for Bharat Hackathon

## 1. Executive Summary

Krise Engine is a multi-agent AI commerce system that replaces static technical filters with a goal-oriented SME (Subject Matter Expert) approach. Unlike traditional product-centric platforms (Amazon/Flipkart), Krise Engine is **user-centric**, prioritizing long-term ROI and verifying marketing claims against real-world sentiment.

**Core Philosophy**: Intent-to-Asset Translation - Moving from "What do you want to buy?" to "What do you want to achieve?"

**Target Market**: AI for Bharat Hackathon - Professional Track. Next billion users in India with vernacular support.

**Key Differentiator**: Socratic Friction Agent - A "stubborn" chatbot that stress-tests user assumptions using devil's advocate logic to ensure high-conviction purchases.

---

## 2. User Personas

### 2.1 Persona 1: The Student (Tech Enthusiast)

**Profile**:
- Age: 19-24
- Occupation: Engineering/Design student
- Use Case: Gaming, CAD software (SolidWorks, AutoCAD), content creation
- Budget: ₹40,000 - ₹80,000
- Pain Points:
  - Overwhelmed by technical jargon (TDP, CUDA cores, nits)
  - Influenced by flashy marketing (RGB lighting, "gaming" branding)
  - Doesn't know if specs translate to real-world performance
  - Prone to impulse purchases based on YouTube reviews

**Goals**:
- Run demanding software smoothly (SolidWorks, Blender)
- Play AAA games at 60+ FPS
- Future-proof investment (3-4 years)
- Impress peers with "cool" tech

**Krise Engine Value**:
- Translates "I need to run SolidWorks" into GPU VRAM requirements, CPU multi-core performance
- Challenges assumptions: "Do you really need RGB lighting, or is that ₹5,000 better spent on more RAM?"
- Shows real-world benchmarks from Reddit/YouTube, not manufacturer claims

### 2.2 Persona 2: The Parent (Pragmatic Buyer)

**Profile**:
- Age: 35-50
- Occupation: Small business owner, working professional
- Use Case: Family phone, reliable communication, long battery life
- Budget: ₹15,000 - ₹30,000
- Pain Points:
  - Confused by camera megapixel wars (108MP vs 50MP)
  - Doesn't understand why phones slow down after 1 year
  - Worried about durability (kids drop phones)
  - Skeptical of "flagship killer" marketing

**Goals**:
- Phone that lasts 3+ years without slowing down
- Good battery life (full day usage)
- Durable build (accidental drops)
- Value for money (no unnecessary features)

**Krise Engine Value**:
- Translates "phone for rough use" into IP68 rating, Gorilla Glass, metal frame
- Challenges assumptions: "You mentioned camera quality, but do you actually print photos or just share on WhatsApp?"
- Exposes hidden issues: "This phone has great specs, but 200+ Reddit users report battery degradation after 8 months"

### 2.3 Persona 3: The Rural Entrepreneur (Vernacular User)

**Profile**:
- Age: 25-40
- Occupation: Farmer, local shop owner, service provider
- Use Case: Business management, digital payments, communication
- Budget: ₹8,000 - ₹20,000
- Pain Points:
  - Not comfortable with English technical terms
  - Needs local language support (Hindi, Marathi, Tamil)
  - Limited access to service centers
  - Relies on word-of-mouth recommendations

**Goals**:
- Affordable, reliable device
- Easy to repair locally
- Long battery life (power cuts common)
- Voice-based interaction

**Krise Engine Value**:
- Voice input in Hindi/Marathi via Sarvam AI
- Translates "मजबूत फोन चाहिए" (need strong phone) into durability specs
- Prioritizes local serviceability and spare parts availability
- Shows real user experiences from regional forums

---

## 3. User Stories

### 3.1 Core User Stories

**US-1**: As a student, I want the system to translate my goal ("run SolidWorks smoothly") into technical requirements (GPU VRAM, CPU cores) so I don't have to learn hardware specifications.

**US-2**: As a parent, I want the agent to challenge my assumptions ("Do you really need a 108MP camera?") so I don't waste money on features I won't use.

**US-3**: As a user, I want to see real-world experiences from Reddit/YouTube, not just manufacturer marketing, so I can make informed decisions.

**US-4**: As a rural user, I want to interact in my native language (Hindi/Marathi) using voice, so I'm not excluded by language barriers.

**US-5**: As a budget-conscious buyer, I want the system to prioritize long-term ROI (repairability, software updates) over flashy features, so my purchase lasts longer.

**US-6**: As an indecisive shopper, I want the agent to "fight" my decision with devil's advocate questions, so I gain conviction in my final choice.

**US-7**: As a user, I want to swipe through product cards and have the system learn my preferences in real-time, so recommendations improve instantly.

**US-8**: As a skeptical buyer, I want the system to audit manufacturer claims (e.g., "2-day battery") against real user reports, so I know what to expect.

### 3.2 Socratic Friction Stories

**US-9**: As a user who says "I want the latest flagship," I want the agent to ask "Why? What specific features do you need that your current phone lacks?" so I don't overspend.

**US-10**: As a user who prioritizes camera quality, I want the agent to ask "Do you print photos or just share on social media?" so I understand if a mid-range camera is sufficient.

**US-11**: As a user who wants "gaming performance," I want the agent to ask "Which games? At what settings?" so I get the right GPU tier.

**US-12**: As a user influenced by brand loyalty, I want the agent to challenge "Why only Apple/Samsung? Have you considered alternatives with better value?" so I explore objectively.

### 3.3 Post-Decision Stories

**US-13**: As a user who completed a purchase, I want the system to monitor prices for 30 days and alert me to drops, so I can claim price protection.

**US-14**: As a user, I want to be notified when a newer model is released, so I can decide if I should upgrade or return my recent purchase.

**US-15**: As a user, I want the system to track my warranty and remind me before expiration, so I don't miss extended warranty options.

---

## 4. Functional Requirements

### 4.1 Phase 1: Semantic Intent Mapping

**FR-1.1**: Natural Language Understanding
- Accept user input describing goals, not products
  - Example: "I need a laptop for outdoor field work" (not "I need a laptop with 500 nits brightness")
  - Example: "Phone for rough use by kids" (not "I need IP68 rating")
- Support Hindi, Marathi, Tamil, Telugu, Bengali (via Sarvam AI)
- Voice input with speech-to-text conversion

**FR-1.2**: Intent-to-Specification Translation
- Map lifestyle goals to technical specifications:
  - "Outdoor use" → Brightness >400 nits, anti-glare coating, IP rating
  - "Gaming" → GPU tier (RTX 3060+), refresh rate >120Hz, cooling system
  - "SolidWorks" → GPU VRAM >6GB, CPU multi-core score, RAM >16GB
  - "Rough use" → Gorilla Glass Victus, IP68, metal frame, drop test certification
  - "Long-term" → Software update commitment, repairability score, warranty >2 years
- Maintain vector database of intent→spec mappings with confidence scores

**FR-1.3**: Context Extraction
- Extract implicit constraints from conversation:
  - Budget (explicit or inferred from "affordable", "premium")
  - Usage patterns (heavy user vs casual)
  - Environment (urban vs rural, climate considerations)
  - Technical literacy level (adjust explanation depth)

**FR-1.4**: Intent Profile Generation
- Create weighted preference vector
- Identify must-haves vs nice-to-haves
- Flag contradictions ("cheap" + "flagship" = conflict)
- Export as structured JSON for downstream agents

### 4.2 Phase 2: Socratic Friction Agent

**FR-2.1**: Assumption Stress-Testing
- Identify weak or impulsive reasoning in user statements
- Generate devil's advocate questions:
  - User: "I want the latest iPhone"
  - Agent: "Why? What specific features do you need that your current phone lacks?"
  - User: "I need a gaming laptop"
  - Agent: "Which games? At what settings? Do you need portability or is desktop an option?"

**FR-2.2**: Feature Necessity Validation
- Challenge unnecessary feature requests:
  - "You mentioned 108MP camera. Do you print large photos or just share on WhatsApp?"
  - "You want RGB lighting. Does that improve performance, or is it aesthetic?"
  - "You need 1TB storage. How much do you currently use?"

**FR-2.3**: Budget Reality Check
- Highlight trade-offs when budget is insufficient:
  - "Your budget is ₹50,000 but you want flagship specs. Would you compromise on camera for better processor?"
  - "This feature adds ₹8,000. Is it worth 16% of your budget?"

**FR-2.4**: Conviction Scoring
- Track user confidence through conversation
- Require high conviction (>80%) before showing products
- If conviction is low, continue Socratic questioning
- Prevent impulse purchases through friction

**FR-2.5**: Bias Detection
- Identify brand bias ("I only want Apple")
- Challenge with objective comparisons
- Expose marketing influence ("You mentioned 'flagship killer' - where did you hear that term?")

### 4.3 Phase 3: Autonomous Scraper Agent

**FR-3.1**: Multi-Source Data Aggregation
- Real-time scraping using Playwright (JavaScript-heavy sites)
- Fallback to BeautifulSoup4 for static sites
- Target sources:
  - **Marketplaces**: Amazon India, Flipkart, Snapdeal, Croma
  - **Forums**: Reddit (r/IndianGaming, r/Android, r/Laptops)
  - **Video**: YouTube (extract transcripts for reviews)
  - **Social**: Twitter/X for product mentions
  - **Manufacturer sites**: Official specs and warranty info

**FR-3.2**: Live Pricing & Stock
- Scrape current prices every 30 minutes
- Detect flash sales and limited-time offers
- Track stock availability across regions
- Identify price manipulation patterns (fake discounts)

**FR-3.3**: Sentiment Mining
- Extract unscripted user opinions from:
  - Reddit comment threads (sort by "top" and "controversial")
  - YouTube video transcripts (not just description)
  - Forum discussions (TeamBHP, Digit, XDA)
- Identify common complaints and praise patterns
- Detect fake/sponsored reviews (sentiment uniformity, timing patterns)

**FR-3.4**: Data Freshness
- Maximum data age: 1 hour for prices, 24 hours for reviews
- Cache results to reduce scraping load
- Implement exponential backoff for rate limiting
- Respect robots.txt and terms of service

**FR-3.5**: Anti-Detection Measures
- Rotate user agents and headers
- Use proxy rotation (Indian IPs preferred)
- Randomize request timing
- Handle CAPTCHAs gracefully (fallback to cached data)

### 4.4 Phase 4: Opinion Summaries (Claim Auditing)

**FR-4.1**: Manufacturer Claim Extraction
- Parse marketing materials for specific claims:
  - "2-day battery life"
  - "Fastest charging in segment"
  - "Military-grade durability"
  - "Pro-level camera"

**FR-4.2**: Real-World Validation
- Cross-reference claims with user experiences:
  - Claim: "2-day battery" → Reality: "Most users report 1-1.5 days with moderate use"
  - Claim: "Fastest charging" → Reality: "Charges in 45 min, but OnePlus does it in 30 min"
  - Claim: "Military-grade" → Reality: "Passed MIL-STD-810G, but users report screen cracks from waist-height drops"

**FR-4.3**: Sentiment Aggregation
- Summarize 500+ reviews into key themes:
  - **Pros**: Most praised features (with mention count)
  - **Cons**: Most criticized issues (with mention count)
  - **Hidden Issues**: Problems not in marketing (e.g., "Heats up during video calls")

**FR-4.4**: Context-Aware Synthesis
- Generate personalized insights based on user intent:
  - User intent: "Outdoor use" → Highlight: "Screen is highly reflective in direct sunlight (23 mentions)"
  - User intent: "Gaming" → Highlight: "Thermal throttling after 30 min of gaming (15 mentions)"

**FR-4.5**: Confidence Scoring
- Assign confidence to each insight based on:
  - Sample size (more reviews = higher confidence)
  - Recency (recent reviews weighted higher)
  - Source credibility (Reddit > random blog)
  - Sentiment consistency (unanimous vs mixed)

### 4.5 Phase 5: Swipe-to-Refine UI

**FR-5.1**: Gesture-Driven Interface
- Card-based product presentation (React Native)
- Swipe gestures:
  - **Right**: Interested (add to shortlist)
  - **Left**: Not interested (discard)
  - **Up**: Save for later (bookmark)
  - **Down**: Show more details (expand card)

**FR-5.2**: Immediate Feedback Loop
- On left swipe, prompt: "Why not?" with quick-select reasons:
  - Too expensive
  - Wrong brand
  - Insufficient specs
  - Poor reviews
  - Aesthetic preference
- Immediately recalibrate remaining deck based on feedback

**FR-5.3**: Real-Time Model Retraining
- Update user preference weights after each swipe:
  - User swipes left on 3 phones >₹60,000 → Lower budget ceiling
  - User swipes right on phones with >5000mAh battery → Increase battery weight
  - User swipes left on Samsung → Reduce Samsung brand score
- Re-rank remaining cards in deck instantly

**FR-5.4**: Explainable Recommendations
- Show "Why this product?" on each card:
  - "Matches your 'outdoor use' requirement with 500 nits brightness"
  - "Best value in your ₹50,000 budget based on Reddit sentiment"
  - "Addresses your durability concern with IP68 + Gorilla Glass Victus"

**FR-5.5**: Comparison Mode
- Allow side-by-side comparison of 2-3 products
- Highlight differentiators relevant to user intent
- Show "winner" in each category (price, performance, durability)

### 4.6 Phase 6: Weighted Scoring Engine

**FR-6.1**: Multi-Factor Scoring Algorithm
```
Total Score = (Technical Match × 40%) + 
              (Sentiment Score × 30%) + 
              (Value for Money × 20%) + 
              (Availability × 10%)
```

**FR-6.2**: Technical Match Calculation
- For each technical requirement in intent profile:
  - Full match: 100 points × weight
  - Partial match: 50 points × weight
  - No match: 0 points
  - Exceeds requirement: Bonus 10 points
- Example:
  - Requirement: Brightness >400 nits (weight: 0.9)
  - Product: 500 nits
  - Score: 110 × 0.9 = 99 points

**FR-6.3**: Sentiment Score Calculation
- Aggregate sentiment from all sources (Reddit, YouTube, forums)
- Weight by source credibility:
  - Reddit: 1.0x
  - YouTube: 0.8x (more sponsored content)
  - Amazon reviews: 0.6x (fake review risk)
- Normalize to 0-100 scale

**FR-6.4**: Value for Money Calculation
- Compare price to performance benchmarks
- Factor in long-term costs (repairability, software updates)
- Penalize overpriced products
- Reward "sweet spot" products (80% performance at 60% price)

**FR-6.5**: Dynamic Weight Adjustment
- Adjust weights based on user behavior:
  - User consistently swipes left on expensive products → Increase price weight
  - User swipes right on high-sentiment products → Increase sentiment weight
- A/B test different weight configurations

### 4.7 Phase 7: LLM Data Parser

**FR-7.1**: Raw HTML to Structured Data
- Extract product information from unstructured HTML:
  - Product title, brand, model
  - Price (current, original, discount)
  - Specifications (parse tables, lists, paragraphs)
  - Images (high-resolution URLs)
  - Availability (in stock, out of stock, pre-order)

**FR-7.2**: Specification Normalization
- Standardize units across sources:
  - "6.5 inches" = "6.5 in" = "165 mm"
  - "4500 mAh" = "4.5 Ah"
  - "Full HD+" = "1080p" = "2400×1080"
- Handle missing data gracefully (mark as "unknown")

**FR-7.3**: LLM-Powered Extraction
- Use Claude 3.5 / Gemini for intelligent parsing:
  - Identify specifications even in unstructured text
  - Extract implicit information ("all-day battery" → ~8-10 hours)
  - Resolve ambiguities ("Pro model" → identify exact variant)

**FR-7.4**: Validation & Error Handling
- Validate extracted data against known ranges:
  - Price: ₹1,000 - ₹5,00,000 (flag outliers)
  - Battery: 1000 - 10,000 mAh
  - Screen size: 4 - 18 inches
- Flag suspicious data for manual review
- Retry extraction with different LLM prompt if confidence is low

---

## 5. Non-Functional Requirements

### 5.1 Performance

**NFR-1.1**: Intent classification latency <2 seconds  
**NFR-1.2**: Scraping latency <5 seconds per source (parallel execution)  
**NFR-1.3**: Swipe feedback processing <500ms (instant UI update)  
**NFR-1.4**: LLM data parsing <3 seconds per product  
**NFR-1.5**: Support 1,000 concurrent users (hackathon demo scale)

### 5.2 Accuracy

**NFR-2.1**: Intent-to-spec mapping accuracy >85%  
**NFR-2.2**: Sentiment classification accuracy >80%  
**NFR-2.3**: Price accuracy within 5% of actual (real-time scraping)  
**NFR-2.4**: Specification extraction accuracy >90%  
**NFR-2.5**: Fake review detection precision >75%

### 5.3 Scalability

**NFR-3.1**: Handle 10,000+ products in vector database  
**NFR-3.2**: Process 500+ reviews per product  
**NFR-3.3**: Support 5+ product categories (phones, laptops, tablets, TVs, appliances)  
**NFR-3.4**: Horizontal scaling for scraper workers (10+ parallel scrapers)

### 5.4 Localization (Bharat-Ready)

**NFR-4.1**: Support 5 Indian languages (Hindi, Marathi, Tamil, Telugu, Bengali)  
**NFR-4.2**: Voice input accuracy >80% for vernacular languages  
**NFR-4.3**: Currency in INR with regional formatting (lakhs/crores)  
**NFR-4.4**: Regional product availability awareness (North vs South India)  
**NFR-4.5**: Low-bandwidth mode for rural users (<100 kbps)

### 5.5 Reliability

**NFR-5.1**: System uptime >95% (hackathon demo period)  
**NFR-5.2**: Graceful degradation if scraping fails (use cached data)  
**NFR-5.3**: Fallback to rule-based intent mapping if LLM is unavailable  
**NFR-5.4**: Error recovery within 30 seconds

### 5.6 Security & Privacy

**NFR-6.1**: No PII storage (conversations are ephemeral)  
**NFR-6.2**: Anonymized analytics only  
**NFR-6.3**: HTTPS for all API communication  
**NFR-6.4**: Rate limiting to prevent abuse (100 requests/min per user)

---

## 6. Success Metrics

### 6.1 User Engagement Metrics

**M-1**: Conversation completion rate >70%  
- Measures: % of users who complete intent profiling and reach product recommendations

**M-2**: Average session duration >8 minutes  
- Measures: Time spent in Socratic dialogue + swipe interaction

**M-3**: Swipe-to-shortlist ratio >30%  
- Measures: % of swiped products added to shortlist (indicates relevance)

**M-4**: Return user rate >40%  
- Measures: Users who come back for second purchase decision

### 6.2 Decision Quality Metrics

**M-5**: Reduction in decision paralysis: 50% fewer products viewed before decision  
- Baseline: Traditional e-commerce users view 20-30 products
- Target: Krise Engine users view 8-12 products

**M-6**: Purchase conviction score >4/5  
- Post-purchase survey: "How confident are you in your decision?"

**M-7**: Return rate <5%  
- Measures: % of purchases returned due to "not as expected"
- Baseline: E-commerce return rate is 15-20%

**M-8**: Feature utilization accuracy >80%  
- Measures: % of features user said they needed that they actually use (6-month follow-up)

### 6.3 System Performance Metrics

**M-9**: Intent classification accuracy >85%  
- Validated against human expert labeling

**M-10**: Sentiment prediction accuracy >80%  
- Predicted sentiment vs actual user satisfaction (post-purchase survey)

**M-11**: Scraping success rate >90%  
- % of scraping attempts that return valid data

**M-12**: LLM parsing accuracy >90%  
- % of extracted specifications that match ground truth

### 6.4 Business Impact Metrics (Hackathon Pitch)

**M-13**: Cost savings: ₹5,000 average savings per user  
- By preventing over-specification and exposing overpriced products

**M-14**: Time savings: 60% reduction in research time  
- From 2-3 hours of YouTube/Reddit research to 15-20 min conversation

**M-15**: Satisfaction score: >4.5/5 NPS (Net Promoter Score)  
- "Would you recommend Krise Engine to a friend?"

**M-16**: Market differentiation: 80% of users say "This is different from Amazon/Flipkart"  
- Validates unique value proposition

---

## 7. Technical Requirements

### 7.1 Backend (Python)

**TR-1.1**: FastAPI framework (async/await for concurrent operations)  
**TR-1.2**: Celery for background task processing (scraping, sentiment analysis)  
**TR-1.3**: Redis for caching and task queue  
**TR-1.4**: WebSocket support for real-time UI updates

### 7.2 AI/ML Stack

**TR-2.1**: LLM: Claude 3.5 Sonnet (primary) / Gemini 1.5 Pro (fallback)  
**TR-2.2**: Embeddings: sentence-transformers (all-MiniLM-L6-v2)  
**TR-2.3**: Vector DB: Qdrant (open-source, self-hosted)  
**TR-2.4**: NLP: spaCy for preprocessing (tokenization, NER)  
**TR-2.5**: Sentiment Analysis: Fine-tuned DistilBERT on Indian e-commerce reviews

### 7.3 Scraping Stack

**TR-3.1**: Playwright (JavaScript-heavy sites like Flipkart)  
**TR-3.2**: BeautifulSoup4 (static sites)  
**TR-3.3**: Scrapy (structured crawling)  
**TR-3.4**: Proxy rotation service (BrightData / ScraperAPI)  
**TR-3.5**: CAPTCHA solving (2Captcha integration)

### 7.4 Voice Stack (Bharat-Ready)

**TR-4.1**: Speech-to-Text: Sarvam AI (Indic languages)  
**TR-4.2**: Text-to-Speech: ElevenLabs (natural voice)  
**TR-4.3**: Language detection: fastText  
**TR-4.4**: Translation: Google Translate API (fallback)

### 7.5 Data Storage

**TR-5.1**: PostgreSQL (user sessions, product catalog)  
**TR-5.2**: MongoDB (unstructured reviews, social data)  
**TR-5.3**: Redis (caching, real-time data)  
**TR-5.4**: Qdrant (vector embeddings for semantic search)

### 7.6 Frontend (React Native)

**TR-6.1**: React Native (cross-platform mobile app)  
**TR-6.2**: Gesture handler (react-native-gesture-handler)  
**TR-6.3**: WebSocket client (Socket.io)  
**TR-6.4**: State management (Zustand)  
**TR-6.5**: UI library (NativeBase / React Native Paper)

---

## 8. Out of Scope (Post-Hackathon)

- Payment gateway integration
- Order fulfillment
- Post-purchase price monitoring (Sentry Agent)
- B2B procurement workflows
- AR/VR product visualization
- Social shopping features
- Multi-user group buying

---

## 9. Compliance & Ethics

**C-1**: Transparent AI disclosure ("This is an AI assistant")  
**C-2**: No dark patterns (friction is educational, not manipulative)  
**C-3**: Affiliate disclosure if monetization is added  
**C-4**: Respect scraping ethics (robots.txt, rate limits)  
**C-5**: No storage of scraped copyrighted content (only metadata)  
**C-6**: User consent for voice recording (if stored)

---

## 10. Hackathon-Specific Requirements

### 10.1 Demo Requirements

**D-1**: 5-minute live demo flow:
1. Voice input in Hindi: "मुझे गेमिंग के लिए फोन चाहिए" (I need a phone for gaming)
2. Socratic friction: "Which games? BGMI or just casual games?"
3. Show scraping in action (live price fetch)
4. Display opinion summary (Reddit sentiment)
5. Swipe UI with real-time recalibration

**D-2**: Backup demo video (in case of live demo failure)

**D-3**: Slide deck with architecture diagrams

**D-4**: GitHub repository with README and setup instructions

### 10.2 Judging Criteria Alignment

**J-1**: Innovation: Socratic Friction Agent (unique approach)  
**J-2**: Technical Complexity: Multi-agent orchestration + real-time scraping  
**J-3**: Social Impact: Bharat-ready (vernacular voice, rural users)  
**J-4**: Scalability: Modular agent architecture  
**J-5**: Completeness: End-to-end working prototype

---

## 11. Risk Mitigation

**R-1**: LLM API failure → Fallback to rule-based intent mapping  
**R-2**: Scraping blocked → Use cached data (max 24 hours old)  
**R-3**: Voice API failure → Text-only mode  
**R-4**: High latency → Show loading states, async processing  
**R-5**: Inaccurate sentiment → Show confidence scores, allow user feedback

---

## Appendix A: Glossary

- **Intent-to-Asset Translation**: Mapping user goals to technical specifications
- **Socratic Friction**: Deliberate questioning to stress-test assumptions
- **Conviction Score**: Measure of user confidence in their decision
- **Dark Social**: Unscripted user opinions on Reddit, forums, YouTube
- **Swipe-to-Refine**: Gesture-based feedback loop for model retraining
- **Claim Auditing**: Verifying manufacturer marketing against real-world data
- **Weighted Scoring Engine**: Multi-factor algorithm for product ranking
