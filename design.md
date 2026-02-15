# Krise Engine - System Design Document
## Multi-Agent Intent Orchestrator for AI for Bharat Hackathon

## 1. System Overview

### 1.1 Vision

Krise Engine transforms e-commerce from a product-search experience into a goal-oriented consultation. Instead of asking "What do you want to buy?", it asks "What do you want to achieve?" - then translates that intent into technical specifications, validates assumptions through Socratic dialogue, and verifies marketing claims against real-world sentiment.

### 1.2 Core Philosophy

- **Intent-First**: Start with user goals, not product categories
- **Friction as Feature**: Deliberate questioning prevents impulse purchases
- **Sentiment over Marketing**: Reddit/YouTube opinions > manufacturer claims
- **Continuous Learning**: Every swipe retrains the recommendation model
- **Bharat-Ready**: Vernacular voice support for next billion users

### 1.3 Key Differentiators vs Traditional E-commerce

| Traditional (Amazon/Flipkart) | Krise Engine |
|-------------------------------|--------------|
| Filter by specs (user must know) | Describe goals (system translates) |
| Static product listings | Dynamic Socratic dialogue |
| Manufacturer descriptions | Real-world sentiment auditing |
| Impulse-friendly UI | Friction-by-design (conviction building) |
| English-centric | Vernacular voice (Hindi, Marathi, etc.) |
| Product-centric | User-centric (long-term ROI) |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                         │
│  React Native App (Swipe UI) + Voice Input (Sarvam AI)          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                       │
│              WebSocket (real-time) + REST (async)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Orchestrator (Core)                      │
│         Task Routing | State Management | Error Recovery         │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Intent     │    │   Socratic   │    │   Scraper    │
│   Mapper     │───▶│   Friction   │◀───│    Agent     │
│   Agent      │    │    Agent     │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Data Parser (Claude 3.5)                  │
│         Raw HTML → Structured JSON + Sentiment Analysis          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Weighted Scoring Engine                         │
│    Technical Match (40%) + Sentiment (30%) + VFM (20%) +        │
│                      Availability (10%)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Swipe Feedback Loop                            │
│         User Swipes → Update Weights → Re-rank Products          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  PostgreSQL | MongoDB | Redis | Qdrant (Vector DB)              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

#### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Async Tasks**: Celery + Redis
- **WebSocket**: FastAPI native WebSocket
- **API**: REST + WebSocket hybrid

#### AI/ML
- **LLM**: Claude 3.5 Sonnet (primary), Gemini 1.5 Pro (fallback)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector DB**: Qdrant (self-hosted)
- **Sentiment**: Fine-tuned DistilBERT on Indian e-commerce reviews
- **NLP**: spaCy (preprocessing)

#### Scraping
- **Dynamic Sites**: Playwright (Flipkart, Amazon)
- **Static Sites**: BeautifulSoup4
- **Structured Crawling**: Scrapy
- **Anti-Detection**: Proxy rotation, user-agent randomization

#### Voice (Bharat-Ready)
- **STT**: Sarvam AI (Hindi, Marathi, Tamil, Telugu, Bengali)
- **TTS**: ElevenLabs (natural voice)
- **Language Detection**: fastText

#### Data Storage
- **Relational**: PostgreSQL (sessions, products)
- **Document**: MongoDB (reviews, social data)
- **Cache**: Redis (real-time data, task queue)
- **Vector**: Qdrant (semantic search)

#### Frontend
- **Mobile**: React Native (Android priority)
- **Gestures**: react-native-gesture-handler
- **State**: Zustand
- **UI**: NativeBase

---

## 3. Multi-Agent System Design

### 3.1 Agent Orchestrator (Central Coordinator)

**Responsibility**: Manage agent lifecycle, route tasks, maintain system state

**Core Functions**:

1. **Task Routing**
   - Analyze incoming user message
   - Determine which agent(s) to invoke
   - Create execution plan (sequential or parallel)

2. **State Management**
   - Maintain conversation context across agents
   - Track user intent profile evolution
   - Store swipe history and preference weights

3. **Error Recovery**
   - Implement circuit breakers for failing agents
   - Fallback strategies (LLM failure → rule-based)
   - Graceful degradation (scraping failure → cached data)

4. **Performance Monitoring**
   - Track agent response times
   - Log errors and anomalies
   - Trigger alerts for system issues

**Workflow**:
```python
async def orchestrate(user_message: str, session_id: str):
    # 1. Load session state
    session = await get_session(session_id)
    
    # 2. Determine phase
    if session.intent_profile is None:
        # Phase 1: Intent Mapping
        intent_profile = await intent_mapper.process(user_message)
        session.intent_profile = intent_profile
        
        # Phase 2: Socratic Friction
        if intent_profile.conviction_score < 0.8:
            question = await socratic_agent.generate_question(intent_profile)
            return {"type": "question", "content": question}
    
    # 3. High conviction → Fetch products
    if session.intent_profile.conviction_score >= 0.8:
        # Parallel execution
        products_task = scraper_agent.fetch_products(intent_profile)
        sentiment_task = scraper_agent.fetch_sentiment(intent_profile)
        
        products, sentiments = await asyncio.gather(products_task, sentiment_task)
        
        # 4. Score and rank
        scored_products = scoring_engine.rank(products, sentiments, intent_profile)
        
        return {"type": "recommendations", "products": scored_products}
```

**State Schema**:
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "phase": "intent_mapping | socratic_friction | product_recommendation",
  "intent_profile": {...},
  "conversation_history": [...],
  "swipe_history": [...],
  "preference_weights": {...},
  "conviction_score": 0.75,
  "created_at": "timestamp",
  "last_updated": "timestamp"
}
```

---

### 3.2 Intent Mapper Agent

**Responsibility**: Translate natural language goals into technical specifications

**Architecture**:
```
User Input (text/voice)
    ↓
Language Detection (fastText)
    ↓
Translation to English (if needed)
    ↓
Intent Classification (LLM + Vector DB)
    ↓
Specification Mapping (Semantic Search)
    ↓
Constraint Extraction (Budget, Brand, etc.)
    ↓
Intent Profile (JSON)
```

**Core Components**:

1. **Intent Classifier**
   - Uses Claude 3.5 with few-shot prompting
   - Extracts primary use case (gaming, work, photography, etc.)
   - Identifies implicit requirements (durability, battery, portability)
   - Assigns confidence scores

2. **Specification Mapper**
   - Vector database of intent→spec mappings
   - Semantic search for similar intents
   - Example mappings:
     ```python
     {
       "outdoor laptop": {
         "display_brightness": {"min": 400, "weight": 0.9},
         "ip_rating": {"min": "IP53", "weight": 0.7},
         "anti_glare": {"required": true, "weight": 0.8}
       },
       "gaming phone": {
         "refresh_rate": {"min": 120, "weight": 0.9},
         "processor": {"tier": "flagship", "weight": 0.85},
         "cooling": {"required": true, "weight": 0.7}
       }
     }
     ```

3. **Constraint Extractor**
   - Budget (explicit or inferred)
   - Brand preferences/aversions
   - Size/weight constraints
   - Deal-breakers (e.g., "no Chinese brands")

4. **Profile Builder**
   - Weighted preference vector
   - Must-haves vs nice-to-haves
   - Contradiction detection

**LLM Prompt Template**:
```
You are an expert product consultant. A user has described their needs.
Extract the following:
1. Primary use case (gaming, work, photography, etc.)
2. Technical requirements (be specific with numbers)
3. Budget constraints
4. Brand preferences
5. Deal-breakers

User input: "{user_message}"

Respond in JSON format:
{
  "primary_use_case": "...",
  "technical_requirements": {...},
  "constraints": {...},
  "confidence": 0.0-1.0
}
```

**Output Schema**:
```json
{
  "session_id": "uuid",
  "primary_use_case": "gaming_laptop",
  "secondary_use_cases": ["video_editing", "portability"],
  "technical_requirements": {
    "gpu": {"min_tier": "RTX_3060", "weight": 0.9},
    "refresh_rate": {"min": 120, "weight": 0.8},
    "cooling": {"required": true, "weight": 0.7}
  },
  "constraints": {
    "budget": {"max": 80000, "currency": "INR", "flexible": true},
    "weight": {"max_kg": 2.5},
    "brand_preferences": ["asus", "msi", "lenovo"]
  },
  "deal_breakers": ["integrated_gpu", "60hz_display"],
  "confidence_score": 0.82,
  "ambiguities": ["Unclear if portability is critical"]
}
```

---

### 3.3 Socratic Friction Agent

**Responsibility**: Stress-test user assumptions through devil's advocate questioning

**Philosophy**: Friction prevents impulse purchases and builds conviction

**Core Logic**:
```python
def generate_friction_question(intent_profile):
    # 1. Identify weak reasoning
    weak_points = detect_weak_reasoning(intent_profile)
    
    # 2. Challenge assumptions
    if "latest_flagship" in intent_profile.keywords:
        return "Why do you need the latest model? What specific features are you missing in your current device?"
    
    # 3. Validate feature necessity
    if intent_profile.requirements.camera.megapixels > 50:
        return "You mentioned high megapixels. Do you print large photos, or is this for social media?"
    
    # 4. Budget reality check
    if intent_profile.budget < required_budget:
        return f"Your budget is ₹{budget}, but your requirements need ₹{required}. Which feature would you compromise on?"
    
    # 5. Brand bias challenge
    if len(intent_profile.brand_preferences) == 1:
        return f"You only want {brand}. Have you considered alternatives with better value?"
```

**Question Categories**:

1. **Assumption Challenges**
   - "Why do you think you need that feature?"
   - "Where did you hear that this is important?"
   - "Have you used this feature before?"

2. **Feature Necessity**
   - "Do you actually use X, or is it nice-to-have?"
   - "How often will you use this feature?"
   - "Is this worth ₹X,000 extra?"

3. **Budget Reality**
   - "Your budget is tight. What's your priority: A or B?"
   - "Would you wait 2 months to save ₹10,000 for a better model?"

4. **Brand Bias**
   - "Why only this brand? What about alternatives?"
   - "Are you paying for the logo or the performance?"

5. **Long-term Thinking**
   - "Will this still meet your needs in 2 years?"
   - "Have you considered repairability and software updates?"

**Conviction Scoring**:
```python
def calculate_conviction(conversation_history):
    score = 0.5  # baseline
    
    # Increase conviction if:
    # - User provides specific use cases (+0.1)
    # - User has done prior research (+0.15)
    # - User answers friction questions confidently (+0.1 per answer)
    # - User has clear budget and priorities (+0.1)
    
    # Decrease conviction if:
    # - User uses vague terms ("best", "latest") (-0.1)
    # - User contradicts themselves (-0.15)
    # - User influenced by marketing buzzwords (-0.1)
    # - User hesitates on friction questions (-0.1)
    
    return min(max(score, 0), 1)
```

**Example Dialogue**:
```
User: "I want the latest iPhone"
Agent: "Why the latest? What specific features do you need that your current phone lacks?"

User: "It has a better camera"
Agent: "Better how? Do you print photos, shoot professionally, or mainly share on Instagram?"

User: "Mostly Instagram"
Agent: "Instagram compresses images heavily. A mid-range phone with a good sensor might be sufficient. Would you consider saving ₹40,000?"

User: "Hmm, maybe. But I want it to last long"
Agent: "Great! Let's focus on software update commitment and build quality instead of camera megapixels."
[Conviction score increases from 0.4 to 0.7]
```

---

### 3.4 Scraper Agent

**Responsibility**: Real-time data aggregation from marketplaces and social platforms

**Architecture**: Master-Worker Pattern

```
Scraper Orchestrator
    ↓
┌───────────┬───────────┬───────────┬───────────┐
│  Amazon   │ Flipkart  │  Reddit   │  YouTube  │
│  Worker   │  Worker   │  Worker   │  Worker   │
└───────────┴───────────┴───────────┴───────────┘
    ↓           ↓           ↓           ↓
┌─────────────────────────────────────────────┐
│         LLM Data Parser (Claude 3.5)        │
│      Raw HTML → Structured JSON             │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│         Data Normalization & Storage        │
│      PostgreSQL + MongoDB + Redis           │
└─────────────────────────────────────────────┘
```

**Scraping Strategy**:

1. **Marketplace Scraping** (Amazon, Flipkart)
   - Use Playwright for JavaScript-heavy sites
   - Extract: Title, Price, Specs, Images, Availability
   - Handle pagination and lazy loading
   - Respect rate limits (1 request/second)

2. **Social Sentiment Scraping** (Reddit, YouTube)
   - Reddit: Use PRAW API + scraping for old threads
   - YouTube: Extract transcripts via youtube-transcript-api
   - Focus on product-specific subreddits and review videos
   - Filter for recency (last 6 months)

3. **Anti-Detection Measures**
   - Rotate user agents (mobile, desktop, various browsers)
   - Use residential proxies (Indian IPs)
   - Randomize request timing (1-3 second delays)
   - Handle CAPTCHAs via 2Captcha

**Parallel Execution**:
```python
async def fetch_all_data(product_query):
    tasks = [
        fetch_amazon(product_query),
        fetch_flipkart(product_query),
        fetch_reddit_sentiment(product_query),
        fetch_youtube_reviews(product_query)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle failures gracefully
    valid_results = [r for r in results if not isinstance(r, Exception)]
    return valid_results
```

**Data Freshness**:
- Prices: Cache for 30 minutes
- Specs: Cache for 24 hours
- Reviews: Cache for 7 days
- Sentiment: Cache for 7 days

---

### 3.5 LLM Data Parser

**Responsibility**: Convert raw HTML/text into structured product data

**Challenge**: Each marketplace has different HTML structure. Traditional scrapers break easily.

**Solution**: Use LLM (Claude 3.5) to intelligently extract data from unstructured HTML.

**Workflow**:
```
Raw HTML (Amazon product page)
    ↓
Extract relevant sections (remove nav, footer, ads)
    ↓
Send to Claude 3.5 with extraction prompt
    ↓
Receive structured JSON
    ↓
Validate and normalize
    ↓
Store in database
```

**LLM Prompt Template**:
```
You are a data extraction expert. Extract product information from this HTML.

HTML:
{html_content}

Extract the following in JSON format:
{
  "title": "Full product name",
  "brand": "Brand name",
  "model": "Model number",
  "price": {
    "current": number,
    "original": number,
    "currency": "INR"
  },
  "specifications": {
    "display_size": "6.5 inches",
    "battery": "5000 mAh",
    "processor": "Snapdragon 8 Gen 2",
    ...
  },
  "availability": "in_stock | out_of_stock | pre_order",
  "images": ["url1", "url2"]
}

If a field is not found, use null.
```

**Specification Normalization**:
```python
def normalize_specs(raw_specs):
    normalized = {}
    
    # Standardize units
    if "display_size" in raw_specs:
        # "6.5 inches" → 6.5
        normalized["display_size_inches"] = extract_number(raw_specs["display_size"])
    
    if "battery" in raw_specs:
        # "5000 mAh" → 5000
        normalized["battery_mah"] = extract_number(raw_specs["battery"])
    
    # Standardize processor tiers
    if "processor" in raw_specs:
        normalized["processor_tier"] = classify_processor(raw_specs["processor"])
        # "Snapdragon 8 Gen 2" → "flagship"
    
    return normalized
```

**Validation**:
```python
def validate_product_data(data):
    errors = []
    
    # Price validation
    if not (1000 <= data["price"]["current"] <= 500000):
        errors.append("Price out of reasonable range")
    
    # Spec validation
    if "battery_mah" in data and not (1000 <= data["battery_mah"] <= 10000):
        errors.append("Battery capacity unrealistic")
    
    # Completeness check
    required_fields = ["title", "price", "brand"]
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    return len(errors) == 0, errors
```

**Fallback Strategy**:
- If LLM extraction fails, use regex patterns
- If both fail, mark product as "incomplete" and skip
- Log failures for manual review

---

### 3.6 Weighted Scoring Engine

**Responsibility**: Rank products based on multi-factor scoring algorithm

**Formula**:
```
Total Score = (Technical Match × 40%) + 
              (Sentiment Score × 30%) + 
              (Value for Money × 20%) + 
              (Availability × 10%)
```

**Component Breakdown**:

#### 1. Technical Match Score (40% weight)

```python
def calculate_technical_match(product, intent_profile):
    score = 0
    total_weight = 0
    
    for requirement, params in intent_profile.technical_requirements.items():
        weight = params["weight"]
        total_weight += weight
        
        if requirement in product.specs:
            product_value = product.specs[requirement]
            required_value = params["min"]
            
            if product_value >= required_value:
                # Full match
                score += 100 * weight
                
                # Bonus for exceeding requirement
                if product_value > required_value * 1.2:
                    score += 10 * weight
            else:
                # Partial match (within 80%)
                if product_value >= required_value * 0.8:
                    score += 50 * weight
                else:
                    # No match
                    score += 0
    
    return (score / total_weight) if total_weight > 0 else 0
```

**Example**:
```
Intent: Gaming laptop
Requirements:
  - GPU: RTX 3060 (weight: 0.9)
  - Refresh rate: 120Hz (weight: 0.8)
  - Cooling: Required (weight: 0.7)

Product A: RTX 3070, 144Hz, Advanced cooling
  - GPU: 110 * 0.9 = 99 (exceeds requirement)
  - Refresh rate: 110 * 0.8 = 88 (exceeds)
  - Cooling: 100 * 0.7 = 70 (meets)
  - Total: (99 + 88 + 70) / 2.4 = 107.08 / 100 = 100 (capped)

Product B: RTX 3050, 120Hz, Basic cooling
  - GPU: 50 * 0.9 = 45 (below requirement)
  - Refresh rate: 100 * 0.8 = 80 (meets)
  - Cooling: 100 * 0.7 = 70 (meets)
  - Total: (45 + 80 + 70) / 2.4 = 81.25
```

#### 2. Sentiment Score (30% weight)

```python
def calculate_sentiment_score(product, intent_profile):
    # Aggregate sentiment from all sources
    sentiments = {
        "reddit": product.reddit_sentiment,      # weight: 1.0
        "youtube": product.youtube_sentiment,    # weight: 0.8
        "amazon": product.amazon_sentiment       # weight: 0.6
    }
    
    weighted_sentiment = 0
    total_weight = 0
    
    for source, sentiment in sentiments.items():
        if sentiment is not None:
            weight = SOURCE_WEIGHTS[source]
            weighted_sentiment += sentiment * weight
            total_weight += weight
    
    base_score = (weighted_sentiment / total_weight) * 100
    
    # Adjust for context-specific issues
    for issue in product.common_issues:
        if issue.category in intent_profile.priorities:
            # Penalize if issue is in user's priority area
            base_score -= issue.severity * 10
    
    return max(base_score, 0)
```

**Example**:
```
Product: OnePlus 11
Reddit sentiment: 0.75 (positive)
YouTube sentiment: 0.80 (positive)
Amazon sentiment: 0.85 (positive)

Weighted: (0.75*1.0 + 0.80*0.8 + 0.85*0.6) / 2.4 = 0.785
Base score: 78.5

Common issues:
  - "Heats up during gaming" (severity: 0.3)
  
User priority: Gaming
Penalty: 0.3 * 10 = 3

Final sentiment score: 78.5 - 3 = 75.5
```

#### 3. Value for Money Score (20% weight)

```python
def calculate_vfm_score(product, intent_profile):
    # Compare price to performance
    performance_score = product.benchmark_score  # e.g., AnTuTu, Geekbench
    price = product.price
    
    # Calculate price-to-performance ratio
    ptp_ratio = performance_score / price
    
    # Compare to category average
    category_avg_ptp = get_category_average_ptp(product.category)
    
    if ptp_ratio > category_avg_ptp * 1.2:
        # Excellent value
        vfm_score = 100
    elif ptp_ratio > category_avg_ptp:
        # Good value
        vfm_score = 80
    elif ptp_ratio > category_avg_ptp * 0.8:
        # Average value
        vfm_score = 60
    else:
        # Poor value
        vfm_score = 40
    
    # Adjust for long-term costs
    if product.repairability_score > 7:
        vfm_score += 10  # Easy to repair = better long-term value
    
    if product.software_update_years >= 3:
        vfm_score += 10  # Long software support = better value
    
    return min(vfm_score, 100)
```

#### 4. Availability Score (10% weight)

```python
def calculate_availability_score(product, user_location):
    score = 0
    
    # In stock
    if product.in_stock:
        score += 50
    else:
        return 0  # Out of stock = 0 score
    
    # Delivery time
    if product.delivery_days <= 2:
        score += 30  # Fast delivery
    elif product.delivery_days <= 5:
        score += 20  # Moderate delivery
    else:
        score += 10  # Slow delivery
    
    # Local availability (service centers)
    service_centers = get_nearby_service_centers(product.brand, user_location)
    if len(service_centers) > 0:
        score += 20  # Local service available
    
    return score
```

**Final Scoring**:
```python
def calculate_final_score(product, intent_profile, user_location):
    technical = calculate_technical_match(product, intent_profile)
    sentiment = calculate_sentiment_score(product, intent_profile)
    vfm = calculate_vfm_score(product, intent_profile)
    availability = calculate_availability_score(product, user_location)
    
    final_score = (
        technical * 0.40 +
        sentiment * 0.30 +
        vfm * 0.20 +
        availability * 0.10
    )
    
    # Deal-breaker check
    if has_deal_breakers(product, intent_profile):
        final_score = 0
    
    return final_score
```

---

### 3.7 Swipe Feedback Loop

**Responsibility**: Learn from user swipes and retrain model in real-time

**Workflow**:
```
User swipes left on Product A
    ↓
Prompt: "Why not?" → User selects "Too expensive"
    ↓
Update preference weights: Increase price sensitivity
    ↓
Re-score all remaining products in deck
    ↓
Re-rank and update UI instantly
```

**Weight Update Algorithm**:
```python
def update_weights_from_swipe(swipe_action, reason, intent_profile):
    if swipe_action == "left":
        if reason == "too_expensive":
            # Increase price weight
            intent_profile.weights["price"] *= 1.2
            
            # Lower budget ceiling
            intent_profile.constraints["budget"]["max"] *= 0.9
        
        elif reason == "wrong_brand":
            # Reduce brand score
            brand = swipe_action.product.brand
            intent_profile.brand_scores[brand] *= 0.5
        
        elif reason == "insufficient_specs":
            # Increase technical match weight
            intent_profile.weights["technical_match"] *= 1.15
        
        elif reason == "poor_reviews":
            # Increase sentiment weight
            intent_profile.weights["sentiment"] *= 1.2
    
    elif swipe_action == "right":
        # Reinforce positive signals
        brand = swipe_action.product.brand
        intent_profile.brand_scores[brand] *= 1.3
        
        # Learn from product features
        for feature, value in swipe_action.product.specs.items():
            if feature in intent_profile.technical_requirements:
                # User liked this feature level
                intent_profile.technical_requirements[feature]["preferred"] = value
    
    # Normalize weights
    normalize_weights(intent_profile.weights)
    
    return intent_profile
```

**Real-Time Re-ranking**:
```python
async def handle_swipe(swipe_data, session_id):
    # 1. Update weights
    session = await get_session(session_id)
    updated_profile = update_weights_from_swipe(
        swipe_data.action,
        swipe_data.reason,
        session.intent_profile
    )
    
    # 2. Re-score remaining products
    remaining_products = session.product_deck[session.current_index:]
    
    for product in remaining_products:
        product.score = calculate_final_score(
            product,
            updated_profile,
            session.user_location
        )
    
    # 3. Re-rank
    remaining_products.sort(key=lambda p: p.score, reverse=True)
    
    # 4. Update session
    session.product_deck[session.current_index:] = remaining_products
    await save_session(session)
    
    # 5. Send next product to UI via WebSocket
    next_product = remaining_products[0]
    await websocket.send_json({
        "type": "next_product",
        "product": next_product.to_dict()
    })
```

**Learning Patterns**:
```python
# Pattern 1: Price sensitivity
# User swipes left on 3 products >₹60,000
# → Lower budget ceiling to ₹55,000

# Pattern 2: Brand preference
# User swipes right on 2 Samsung products
# → Increase Samsung brand score by 30%

# Pattern 3: Feature importance
# User swipes left on phones with <5000mAh battery
# → Increase battery requirement to 5000mAh minimum

# Pattern 4: Sentiment sensitivity
# User swipes left on products with <4.0 rating
# → Increase sentiment weight by 20%
```

---

## 4. Data Pipeline

### 4.1 Data Flow: Raw HTML → Structured Data

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Scraping (Playwright / BeautifulSoup)             │
│  Output: Raw HTML from Amazon, Flipkart, Reddit, YouTube   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: HTML Cleaning                                      │
│  - Remove navigation, footer, ads                           │
│  - Extract main content sections                            │
│  - Preserve structure (tables, lists)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: LLM Data Parser (Claude 3.5)                       │
│  - Extract product details                                  │
│  - Parse specifications                                     │
│  - Identify sentiment in reviews                            │
│  Output: Structured JSON                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Data Normalization                                 │
│  - Standardize units (inches, mAh, etc.)                    │
│  - Classify processors (flagship, mid-range, budget)        │
│  - Normalize prices (handle discounts, taxes)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Data Validation                                    │
│  - Check for missing required fields                        │
│  - Validate ranges (price, battery, etc.)                   │
│  - Flag suspicious data                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Data Enrichment                                    │
│  - Add benchmark scores (AnTuTu, Geekbench)                 │
│  - Calculate repairability score                            │
│  - Fetch software update commitment                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Storage                                            │
│  - PostgreSQL: Structured product data                      │
│  - MongoDB: Unstructured reviews, social mentions           │
│  - Qdrant: Vector embeddings for semantic search            │
│  - Redis: Cache for fast retrieval                          │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Sentiment Analysis Pipeline

```
Reddit/YouTube Comments
    ↓
Text Preprocessing (spaCy)
  - Tokenization
  - Stopword removal
  - Lemmatization
    ↓
Aspect Extraction (LLM)
  - Identify aspects: battery, camera, display, performance
    ↓
Sentiment Classification (DistilBERT)
  - Per-aspect sentiment: positive, negative, neutral
  - Confidence score
    ↓
Aggregation
  - Overall sentiment: weighted average
  - Common issues: cluster negative mentions
  - Praise patterns: cluster positive mentions
    ↓
Context-Aware Synthesis (Claude 3.5)
  - Generate human-readable summary
  - Highlight issues relevant to user intent
    ↓
Store in MongoDB
```

**Example**:
```
Input: "Battery life is amazing, easily lasts 2 days. But the camera is disappointing in low light."

Aspect Extraction:
  - battery: "amazing, easily lasts 2 days"
  - camera: "disappointing in low light"

Sentiment Classification:
  - battery: positive (0.92 confidence)
  - camera: negative (0.87 confidence)

Aggregation:
  - Overall sentiment: 0.65 (mixed)
  - Praise: Battery life (234 mentions)
  - Issue: Low-light camera (89 mentions)

Context-Aware Synthesis (for user who prioritizes battery):
  "Excellent battery life confirmed by 234 users (2-day usage). However, camera struggles in low light (89 mentions). If photography isn't critical, this is a strong choice."
```

---

## 5. API Design

### 5.1 REST Endpoints

```
POST   /api/v1/sessions                    # Start new session
POST   /api/v1/sessions/{id}/message       # Send message (text/voice)
GET    /api/v1/sessions/{id}/profile       # Get intent profile
POST   /api/v1/sessions/{id}/swipe         # Record swipe action
GET    /api/v1/products/{id}               # Get product details
GET    /api/v1/products/{id}/sentiment     # Get sentiment analysis
POST   /api/v1/voice/transcribe            # Voice to text (Sarvam AI)
```

### 5.2 WebSocket Events

```
Client → Server:
  - message: User sends text input
  - voice: User sends voice input (audio blob)
  - swipe: User swipes on product card
  - feedback: User provides explicit feedback

Server → Client:
  - typing: Agent is processing
  - question: Socratic friction question
  - recommendations: Product cards
  - profile_updated: Intent profile changed
  - score_updated: Product scores recalculated
```

### 5.3 Request/Response Examples

**Start Session**:
```json
POST /api/v1/sessions
{
  "user_id": "uuid",
  "language": "hi",  // Hindi
  "location": {"city": "Mumbai", "state": "Maharashtra"}
}

Response:
{
  "session_id": "uuid",
  "status": "active",
  "phase": "intent_mapping"
}
```

**Send Message**:
```json
POST /api/v1/sessions/{id}/message
{
  "content": "मुझे गेमिंग के लिए फोन चाहिए",
  "type": "text"
}

Response:
{
  "type": "question",
  "content": "कौन से गेम खेलते हैं? BGMI या casual games?",
  "intent_profile": {
    "primary_use_case": "gaming",
    "confidence": 0.65
  }
}
```

**Record Swipe**:
```json
POST /api/v1/sessions/{id}/swipe
{
  "product_id": "uuid",
  "direction": "left",
  "reason": "too_expensive"
}

Response:
{
  "next_product": {...},
  "updated_weights": {
    "price": 0.85,
    "technical_match": 0.70
  },
  "remaining_count": 8
}
```

---

## 6. Agent Interaction Flow

### 6.1 Complete User Journey

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Intent Mapping (Turns 1-3)                        │
├─────────────────────────────────────────────────────────────┤
│  User: "मुझे गेमिंग के लिए फोन चाहिए"                      │
│  Intent Mapper: Extracts "gaming" use case                  │
│  Output: Initial intent profile (confidence: 0.65)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Socratic Friction (Turns 4-6)                     │
├─────────────────────────────────────────────────────────────┤
│  Socratic Agent: "कौन से गेम? BGMI या casual?"             │
│  User: "BGMI और COD Mobile"                                │
│  Socratic Agent: "क्या portability ज़रूरी है?"              │
│  User: "हाँ, travel करता हूँ"                              │
│  Output: Refined profile (confidence: 0.85)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Product Fetching (Parallel)                       │
├─────────────────────────────────────────────────────────────┤
│  Scraper Agent:                                             │
│    - Fetch products from Amazon, Flipkart                   │
│    - Fetch Reddit sentiment for gaming phones               │
│    - Fetch YouTube reviews                                  │
│  LLM Parser: Convert raw data to structured JSON            │
│  Output: 50 candidate products                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Scoring & Ranking                                 │
├─────────────────────────────────────────────────────────────┤
│  Scoring Engine:                                            │
│    - Technical match: GPU, refresh rate, cooling            │
│    - Sentiment: Reddit/YouTube opinions                     │
│    - VFM: Price-to-performance ratio                        │
│    - Availability: In stock, delivery time                  │
│  Output: Top 12 products (sorted by score)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Swipe Interaction (Continuous)                    │
├─────────────────────────────────────────────────────────────┤
│  User swipes left on Product A (reason: "too expensive")    │
│  → Update weights: Increase price sensitivity               │
│  → Re-rank remaining 11 products                            │
│  → Show next product instantly                              │
│                                                             │
│  User swipes right on Product B                             │
│  → Add to shortlist                                         │
│  → Reinforce brand preference                               │
│  → Continue swiping                                         │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Agent Communication Protocol

```python
# Orchestrator → Intent Mapper
{
  "task": "extract_intent",
  "input": {
    "message": "मुझे गेमिंग के लिए फोन चाहिए",
    "language": "hi",
    "conversation_history": [...]
  }
}

# Intent Mapper → Orchestrator
{
  "status": "success",
  "output": {
    "intent_profile": {...},
    "confidence": 0.65,
    "ambiguities": ["Unclear if budget is a constraint"]
  }
}

# Orchestrator → Socratic Agent
{
  "task": "generate_friction_question",
  "input": {
    "intent_profile": {...},
    "conversation_history": [...]
  }
}

# Socratic Agent → Orchestrator
{
  "status": "success",
  "output": {
    "question": "कौन से गेम खेलते हैं?",
    "purpose": "clarify_performance_requirements",
    "expected_conviction_increase": 0.15
  }
}

# Orchestrator → Scraper Agent
{
  "task": "fetch_products",
  "input": {
    "intent_profile": {...},
    "sources": ["amazon", "flipkart", "reddit", "youtube"],
    "max_results": 50
  }
}

# Scraper Agent → Orchestrator
{
  "status": "success",
  "output": {
    "products": [...],
    "sentiments": [...],
    "fetch_time_ms": 3200,
    "failed_sources": []
  }
}
```

---

## 7. Deployment Architecture

### 7.1 Development Environment (Docker Compose)

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - SARVAM_API_KEY=${SARVAM_API_KEY}
    depends_on:
      - postgres
      - mongodb
      - redis
      - qdrant
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=krise
      - POSTGRES_USER=krise
      - POSTGRES_PASSWORD=krise123
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  mongodb:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
  
  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
  
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
  
  celery_worker:
    build: ./backend
    command: celery -A app.celery worker --loglevel=info
    depends_on:
      - redis
      - postgres
  
  playwright_scraper:
    build: ./scraper
    command: python scraper_worker.py
    depends_on:
      - redis

volumes:
  postgres_data:
  mongo_data:
  redis_data:
  qdrant_data:
```

### 7.2 Production Architecture (Cloud)

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                     │
│                  SSL Termination (Let's Encrypt)             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  FastAPI     │  │  FastAPI     │  │  FastAPI     │
│  Instance 1  │  │  Instance 2  │  │  Instance 3  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Celery Workers (Auto-scaling)                   │
│  Intent Mapper | Socratic Agent | Scraper | Scorer          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer (Managed)                      │
│  PostgreSQL (RDS) | MongoDB (Atlas) | Redis (ElastiCache)   │
│                  Qdrant (Self-hosted)                        │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Scaling Strategy

**Horizontal Scaling**:
- FastAPI instances: 3-10 (based on load)
- Celery workers: 5-20 (based on queue depth)
- Scraper workers: 10-30 (parallel scraping)

**Auto-scaling Triggers**:
- CPU >70% for 5 minutes → Scale up
- Queue depth >100 tasks → Add workers
- Response time >3 seconds → Scale up

**Database Scaling**:
- PostgreSQL: Read replicas for product catalog
- MongoDB: Sharding for reviews collection
- Redis: Cluster mode for high availability

---

## 8. Monitoring & Observability

### 8.1 Key Metrics

**System Metrics**:
- Request latency (p50, p95, p99)
- Agent processing time
- Scraping success rate
- LLM API latency
- Database query performance
- Cache hit rate

**Business Metrics**:
- Conversation completion rate
- Average conviction score
- Swipe-to-shortlist ratio
- Session duration
- User satisfaction (post-session survey)

**Agent-Specific Metrics**:
- Intent classification accuracy
- Socratic question effectiveness (conviction increase)
- Scraping success rate per source
- Sentiment prediction accuracy
- Scoring algorithm performance

### 8.2 Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "intent_extracted",
    session_id=session_id,
    user_id=user_id,
    primary_use_case="gaming",
    confidence=0.85,
    processing_time_ms=1200
)

# Error logging
logger.error(
    "scraping_failed",
    source="amazon",
    product_query="gaming phone",
    error=str(e),
    retry_count=3
)
```

**Log Aggregation**:
- Centralized logging (ELK Stack or CloudWatch)
- Log retention: 30 days
- PII redaction in logs

### 8.3 Alerting

```yaml
alerts:
  - name: HighErrorRate
    condition: error_rate > 5%
    duration: 5m
    severity: critical
    action: PagerDuty
  
  - name: SlowLLMResponse
    condition: llm_latency_p95 > 5s
    duration: 10m
    severity: warning
    action: Slack
  
  - name: ScrapingFailure
    condition: scraping_success_rate < 80%
    duration: 15m
    severity: warning
    action: Slack
  
  - name: LowConvictionRate
    condition: avg_conviction_score < 0.7
    duration: 1h
    severity: info
    action: Email
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# Test intent extraction
def test_intent_mapper_gaming():
    input_text = "मुझे गेमिंग के लिए फोन चाहिए"
    profile = intent_mapper.extract_intent(input_text)
    
    assert profile.primary_use_case == "gaming"
    assert profile.confidence > 0.6
    assert "refresh_rate" in profile.technical_requirements

# Test scoring algorithm
def test_scoring_engine():
    product = create_mock_product(price=50000, gpu="Snapdragon 8 Gen 2")
    intent = create_mock_intent(use_case="gaming", budget=60000)
    
    score = scoring_engine.calculate_final_score(product, intent)
    
    assert 0 <= score <= 100
    assert score > 70  # Should be a good match
```

### 9.2 Integration Tests

```python
# Test agent communication
async def test_orchestrator_flow():
    session = await create_test_session()
    
    # Send message
    response = await orchestrator.process_message(
        "I need a gaming laptop",
        session.id
    )
    
    # Verify intent extraction
    assert response.type == "question"
    assert session.intent_profile is not None
    
    # Answer friction question
    response = await orchestrator.process_message(
        "BGMI and COD Mobile",
        session.id
    )
    
    # Verify product recommendations
    assert response.type == "recommendations"
    assert len(response.products) > 0
```

### 9.3 End-to-End Tests

```python
# Test complete user journey
async def test_complete_journey():
    # 1. Start session
    session = await api_client.post("/api/v1/sessions", json={
        "user_id": "test_user",
        "language": "en"
    })
    
    # 2. Send initial message
    response = await api_client.post(
        f"/api/v1/sessions/{session.id}/message",
        json={"content": "I need a gaming phone"}
    )
    assert response.json()["type"] == "question"
    
    # 3. Answer questions (2-3 turns)
    # ...
    
    # 4. Receive recommendations
    response = await api_client.get(f"/api/v1/sessions/{session.id}/recommendations")
    assert len(response.json()["products"]) > 0
    
    # 5. Swipe on products
    swipe_response = await api_client.post(
        f"/api/v1/sessions/{session.id}/swipe",
        json={"product_id": "...", "direction": "right"}
    )
    assert swipe_response.status_code == 200
```

### 9.4 Load Testing (Locust)

```python
from locust import HttpUser, task, between

class KriseUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Create session
        response = self.client.post("/api/v1/sessions", json={
            "user_id": f"user_{self.user_id}",
            "language": "en"
        })
        self.session_id = response.json()["session_id"]
    
    @task(3)
    def send_message(self):
        self.client.post(
            f"/api/v1/sessions/{self.session_id}/message",
            json={"content": "I need a gaming phone"}
        )
    
    @task(1)
    def swipe_product(self):
        self.client.post(
            f"/api/v1/sessions/{self.session_id}/swipe",
            json={"product_id": "test_product", "direction": "left"}
        )
```

**Load Test Targets**:
- 1,000 concurrent users
- 10,000 requests/minute
- <2 second response time (p95)
- <1% error rate

---

## 10. Security Considerations

### 10.1 API Security

- **Authentication**: JWT tokens with 24-hour expiry
- **Rate Limiting**: 100 requests/minute per user
- **Input Validation**: Sanitize all user inputs
- **CORS**: Whitelist allowed origins
- **HTTPS**: TLS 1.3 for all communication

### 10.2 Data Privacy

- **No PII Storage**: Conversations are ephemeral (deleted after 7 days)
- **Anonymized Analytics**: User IDs are hashed
- **Voice Data**: Deleted immediately after transcription
- **GDPR Compliance**: Right to deletion, data export

### 10.3 Scraping Ethics

- **Respect robots.txt**: Don't scrape disallowed paths
- **Rate Limiting**: 1 request/second per domain
- **User-Agent**: Identify as "KriseBot" with contact email
- **No Content Storage**: Store only metadata, not full HTML
- **Terms of Service**: Comply with marketplace ToS

---

## 11. Hackathon Demo Plan

### 11.1 5-Minute Demo Flow

**Minute 1: Problem Statement**
- Show traditional e-commerce filters (confusing, technical)
- Highlight decision paralysis (20-30 products viewed)

**Minute 2: Krise Engine Introduction**
- Voice input in Hindi: "मुझे गेमिंग के लिए फोन चाहिए"
- Show intent extraction in real-time
- Display intent profile JSON

**Minute 3: Socratic Friction**
- Agent asks: "कौन से गेम? BGMI या casual?"
- User answers, conviction score increases
- Show weight updates in real-time

**Minute 4: Product Recommendations**
- Show scraping in action (live price fetch)
- Display opinion summary (Reddit sentiment)
- Highlight claim auditing ("2-day battery" vs reality)

**Minute 5: Swipe Interaction**
- User swipes left (reason: "too expensive")
- Show real-time re-ranking
- Final shortlist with explainability

### 11.2 Backup Demo Video

- Pre-recorded 5-minute video
- Covers same flow as live demo
- Includes voiceover explaining architecture
- Shows code snippets and architecture diagrams

### 11.3 Slide Deck Outline

1. **Problem**: Decision paralysis in e-commerce
2. **Solution**: Intent-to-Asset translation
3. **Architecture**: Multi-agent system diagram
4. **Key Innovation**: Socratic Friction Agent
5. **Tech Stack**: FastAPI, Claude 3.5, Playwright, Sarvam AI
6. **Demo**: Live walkthrough
7. **Impact**: Bharat-ready, reduces research time by 60%
8. **Scalability**: Modular agent architecture
9. **Future**: B2B, cross-category intelligence
10. **Team**: Roles and contributions

---

## 12. Future Enhancements (Post-Hackathon)

### 12.1 Phase 2 Features

- **Multi-User Shopping**: Group buying decisions (family, friends)
- **AR Product Visualization**: 3D models of products
- **Price Monitoring**: Post-purchase price drop alerts
- **Trade-In Integration**: Sell old device, buy new
- **EMI Calculator**: Financing options

### 12.2 Phase 3 Features

- **B2B Procurement**: Bulk buying for businesses
- **Cross-Category Intelligence**: Bundle recommendations (laptop + accessories)
- **Sustainability Scoring**: Carbon footprint, repairability
- **Insurance Marketplace**: Extended warranty, device insurance
- **Social Proof**: Friends' recommendations

### 12.3 Technical Improvements

- **Fine-Tuned LLM**: Train custom model on Indian e-commerce data
- **Federated Learning**: Learn from user behavior without storing data
- **Edge Computing**: Run intent extraction on-device for privacy
- **Blockchain**: Transparent review verification
- **Quantum-Resistant Encryption**: Future-proof security

---

## 13. Risk Mitigation

### 13.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API failure | High | Fallback to rule-based intent mapping |
| Scraping blocked | Medium | Use cached data (max 24 hours old) |
| High latency | Medium | Async processing, show loading states |
| Voice API failure | Low | Text-only mode |
| Database downtime | High | Read replicas, automatic failover |

### 13.2 Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low user adoption | High | Focus on vernacular voice, rural users |
| Inaccurate recommendations | High | Show confidence scores, allow feedback |
| Legal issues (scraping) | Medium | Respect ToS, use official APIs where possible |
| Competition | Medium | Unique value prop (Socratic Friction) |
| Monetization challenges | Low | Affiliate links, premium features |

---

## 14. Success Criteria (Hackathon)

### 14.1 Technical Success

- ✅ Working end-to-end demo (intent → recommendations → swipe)
- ✅ Multi-agent system with 4+ agents
- ✅ Real-time scraping from 2+ sources
- ✅ Vernacular voice support (Hindi)
- ✅ Swipe UI with real-time recalibration
- ✅ <3 second response time (p95)

### 14.2 Innovation Success

- ✅ Socratic Friction Agent (unique approach)
- ✅ Intent-to-Asset translation (not just keyword search)
- ✅ Claim auditing (manufacturer vs reality)
- ✅ Reinforcement learning from swipes

### 14.3 Impact Success

- ✅ Bharat-ready (vernacular voice, rural users)
- ✅ Reduces decision paralysis (fewer products viewed)
- ✅ Improves purchase conviction (>80% confidence)
- ✅ Saves research time (60% reduction)

### 14.4 Presentation Success

- ✅ Clear problem statement
- ✅ Compelling live demo
- ✅ Technical depth (architecture diagrams)
- ✅ Social impact (next billion users)
- ✅ Scalability story

---

## Appendix A: Database Schemas

### A.1 PostgreSQL Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE,
    preferred_language VARCHAR(5) DEFAULT 'en',
    location JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    intent_profile JSONB,
    conversation_history JSONB,
    swipe_history JSONB,
    preference_weights JSONB,
    conviction_score FLOAT,
    phase VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500),
    brand VARCHAR(100),
    model VARCHAR(100),
    category VARCHAR(50),
    price JSONB,
    specifications JSONB,
    availability JSONB,
    images TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Product scores table (for caching)
CREATE TABLE product_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    product_id UUID REFERENCES products(id),
    technical_score FLOAT,
    sentiment_score FLOAT,
    vfm_score FLOAT,
    availability_score FLOAT,
    final_score FLOAT,
    explanation JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### A.2 MongoDB Schema

```javascript
// Reviews collection
{
  _id: ObjectId,
  product_id: "uuid",
  source: "reddit | youtube | amazon",
  content: "Full review text",
  sentiment: {
    overall: 0.75,
    aspects: {
      battery: 0.85,
      camera: 0.60,
      performance: 0.80
    }
  },
  author: "username",
  created_at: ISODate,
  upvotes: 123,
  credibility_score: 0.8
}

// Social mentions collection
{
  _id: ObjectId,
  product_id: "uuid",
  platform: "reddit | twitter | youtube",
  url: "https://...",
  content: "Mention text",
  sentiment: 0.65,
  created_at: ISODate,
  engagement: {
    likes: 45,
    comments: 12,
    shares: 3
  }
}
```

### A.3 Qdrant Schema

```python
# Intent embeddings
{
    "id": "uuid",
    "vector": [0.123, -0.456, ...],  # 384 dimensions
    "payload": {
        "type": "intent_mapping",
        "intent_text": "outdoor laptop for field work",
        "specifications": {
            "display_brightness": {"min": 400, "weight": 0.9},
            "ip_rating": {"min": "IP53", "weight": 0.7}
        },
        "examples": [
            "laptop for outdoor use",
            "bright screen for sunlight",
            "durable laptop for field research"
        ]
    }
}

# Product embeddings
{
    "id": "uuid",
    "vector": [0.234, -0.567, ...],
    "payload": {
        "type": "product",
        "product_id": "uuid",
        "title": "Lenovo ThinkPad X1 Carbon",
        "category": "laptop",
        "key_features": ["500 nits", "MIL-STD-810H", "lightweight"]
    }
}
```

---

## Appendix B: LLM Prompts

### B.1 Intent Extraction Prompt

```
You are an expert product consultant for an Indian e-commerce platform.
A user has described their needs. Extract structured intent information.

User message: "{user_message}"
Language: {language}
Conversation history: {conversation_history}

Extract the following in JSON format:
{
  "primary_use_case": "gaming | work | photography | general | ...",
  "secondary_use_cases": ["portability", "battery_life", ...],
  "technical_requirements": {
    "feature_name": {
      "min": number or string,
      "max": number or string (optional),
      "weight": 0.0-1.0 (importance)
    }
  },
  "constraints": {
    "budget": {"max": number, "currency": "INR", "flexible": boolean},
    "size": {"max_weight_kg": number, "max_screen_inches": number},
    "brand_preferences": ["brand1", "brand2"],
    "brand_aversions": ["brand3"]
  },
  "deal_breakers": ["feature1", "feature2"],
  "confidence": 0.0-1.0,
  "ambiguities": ["unclear aspect 1", "unclear aspect 2"]
}

Be specific with technical requirements. For example:
- "gaming" → refresh_rate: {min: 120, weight: 0.9}, gpu: {tier: "flagship", weight: 0.85}
- "outdoor use" → display_brightness: {min: 400, weight: 0.9}, ip_rating: {min: "IP53", weight: 0.7}
- "photography" → camera_sensor_size: {min: "1/1.5", weight: 0.9}, ois: {required: true, weight: 0.8}

If budget is not mentioned, infer from use case:
- "flagship" → ₹80,000+
- "mid-range" → ₹30,000-80,000
- "budget" → <₹30,000
```

### B.2 Socratic Question Generation Prompt

```
You are a Socratic agent designed to stress-test user assumptions and build purchase conviction.

Intent profile: {intent_profile}
Conversation history: {conversation_history}
Current conviction score: {conviction_score}

Your goal: Ask a challenging question that:
1. Identifies weak reasoning or impulsive thinking
2. Validates feature necessity
3. Challenges brand bias
4. Ensures long-term thinking

Question types:
- Assumption challenge: "Why do you think you need X?"
- Feature necessity: "Do you actually use X, or is it nice-to-have?"
- Budget reality: "Your budget is tight. Priority: A or B?"
- Brand bias: "Why only this brand? What about alternatives?"
- Long-term: "Will this meet your needs in 2 years?"

Generate ONE question in JSON format:
{
  "question": "The question text in {language}",
  "purpose": "clarify_requirements | challenge_assumption | validate_budget | ...",
  "expected_conviction_change": -0.1 to +0.2,
  "follow_up_options": ["option1", "option2", "option3"]
}

Be direct but respectful. Use the user's language ({language}).
```

### B.3 Sentiment Summarization Prompt

```
You are a sentiment analysis expert. Summarize user opinions about a product.

Product: {product_name}
Reviews (500+ from Reddit, YouTube, Amazon): {reviews_text}
User's intent: {user_intent}

Generate a context-aware summary in JSON format:
{
  "overall_sentiment": 0.0-1.0,
  "aspect_sentiments": {
    "battery": {"score": 0.0-1.0, "mentions": number},
    "camera": {"score": 0.0-1.0, "mentions": number},
    ...
  },
  "personalized_insights": {
    "pros": [
      "Specific praise relevant to user intent (with mention count)"
    ],
    "cons": [
      "Specific criticism relevant to user intent (with mention count)"
    ],
    "hidden_issues": [
      "Problems not in marketing materials"
    ]
  },
  "confidence": 0.0-1.0,
  "review_count": number,
  "data_sources": ["reddit", "youtube", "amazon"]
}

Focus on insights relevant to the user's intent: {user_intent}
Highlight issues that matter to their use case.
Ignore generic complaints (e.g., "expensive" if user has high budget).
```

---

## Appendix C: Glossary

- **Intent-to-Asset Translation**: Mapping user goals to technical specifications
- **Socratic Friction**: Deliberate questioning to stress-test assumptions and build conviction
- **Conviction Score**: Measure of user confidence in their decision (0.0-1.0)
- **Dark Social**: Unscripted user opinions on Reddit, forums, YouTube (vs official reviews)
- **Swipe-to-Refine**: Gesture-based feedback loop for real-time model retraining
- **Claim Auditing**: Verifying manufacturer marketing claims against real-world user data
- **Weighted Scoring Engine**: Multi-factor algorithm for product ranking
- **LLM Data Parser**: Using LLMs to extract structured data from unstructured HTML
- **Agent Orchestrator**: Central coordinator managing multi-agent system
- **Bharat-Ready**: Designed for next billion users (vernacular voice, low bandwidth, rural focus)

---

**Document Version**: 1.0  
**Last Updated**: February 16, 2026  
**Authors**: Krise Engine Team  
**Hackathon**: AI for Bharat - Professional Track
