// In production (S3), VITE_API_URL is injected at build time pointing to App Runner.
// In dev, it's empty so Vite's proxy handles /api → localhost:8000.
const API_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`

async function parseJsonResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        const text = await res.text().catch(() => '')
        let detail = text
        try { detail = (JSON.parse(text) as { detail?: string }).detail ?? text } catch { /* ignore */ }
        throw new Error(`Server error ${res.status}: ${detail.slice(0, 200)}`)
    }
    const text = await res.text()
    if (!text) throw new Error('Empty response from server')
    return JSON.parse(text) as T
}

export type SessionMode = 'standard' | 'socratic_decision'

export interface SessionResponse {
    session_id: string
    status: string
    phase: string
    mode: SessionMode
}

export interface IntentProfile {
    primary_use_case: string
    secondary_use_cases: string[]
    product_category: string
    confidence_score: number
    conviction_score: number
    constraints: {
        budget_max: number | null
        brand_preferences: string[]
    }
    ambiguities: string[]
}

export interface PriceInfo {
    current: number
    original: number | null
    currency: string
    discount_percent: number | null
}

export interface SentimentData {
    overall_score: number
    pros: string[]
    cons: string[]
    hidden_issues: string[]
    summary: string
    sample_size: number
}

export interface Product {
    id: string
    title: string
    brand: string
    price: PriceInfo
    specifications: Record<string, string>
    images: string[]
    url: string
    source: string
    availability: string
    rating: number | null
    review_count: number | null
    sentiment: SentimentData
}

export interface ProductScore {
    product: Product
    total_score: number
    technical_match: number
    sentiment_score: number
    value_for_money: number
    availability_score: number
    explanation: string
}

export interface WidgetRequest {
    widget_type: string
    label: string
    options?: string[]
    min_value?: number
    max_value?: number
    step?: number
}

export interface DecisionOutcome {
    verdict: 'Hard No' | 'Probably No' | 'Weak Yes' | 'Strong Yes'
    rationale: string
    recommendation: string
    non_consumer_alternative: string
    key_tradeoffs: string[]
}

export interface MessageResponse {
    type: 'question' | 'recommendations' | 'info' | 'error' | 'conclusion'
    content: string
    intent_profile: IntentProfile | null
    products: ProductScore[]
    conviction_score: number
    widget?: WidgetRequest | null
    mode: SessionMode
    stage: string
    turn: number
    max_turns: number
    completed: boolean
    decision_outcome?: DecisionOutcome | null
    conclusion_products?: ProductScore[]
    can_search_more?: boolean
}

export interface ProfileResponse {
    session_id: string
    mode: SessionMode
    phase: string
    initial_statement: string
    intent_profile: IntentProfile
    conviction_score: number
    socratic_turns: number
    decision_turns: number
    decision_stage: string
    decision_complete: boolean
    decision_outcome?: DecisionOutcome | null
    progress_steps: string[]
}

export async function createSession(language: string = 'en', mode: SessionMode = 'standard'): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, mode }),
    })
    return parseJsonResponse<SessionResponse>(res)
}

export async function sendMessage(sessionId: string, content: string): Promise<MessageResponse> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 90000)
    try {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, type: 'text' }),
            signal: controller.signal,
        })
        return parseJsonResponse<MessageResponse>(res)
    } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
            throw new Error('Request timed out — the search is taking too long. Please try again.')
        }
        throw err
    } finally {
        clearTimeout(timeoutId)
    }
}

export async function swipeProduct(
    sessionId: string,
    productId: string,
    direction: string,
    reason?: string,
) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/swipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, direction, reason }),
    })
    return parseJsonResponse(res)
}

export async function getProducts(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/products`)
    return parseJsonResponse(res)
}

export async function getProfile(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/profile`)
    return parseJsonResponse<ProfileResponse>(res)
}
