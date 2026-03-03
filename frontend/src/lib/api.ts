const API_BASE = '/api/v1'

export interface SessionResponse {
    session_id: string
    status: string
    phase: string
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

export interface MessageResponse {
    type: 'question' | 'recommendations' | 'info' | 'error'
    content: string
    intent_profile: IntentProfile | null
    products: ProductScore[]
    conviction_score: number
}

export async function createSession(language: string = 'en'): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language }),
    })
    return res.json()
}

export async function sendMessage(sessionId: string, content: string): Promise<MessageResponse> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, type: 'text' }),
    })
    return res.json()
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
    return res.json()
}

export async function getProducts(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/products`)
    return res.json()
}

export async function getProfile(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/profile`)
    return res.json()
}
