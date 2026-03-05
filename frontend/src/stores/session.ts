import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
    createSession as apiCreateSession,
    sendMessage as apiSendMessage,
    swipeProduct as apiSwipe,
    type SessionResponse,
    type MessageResponse,
    type IntentProfile,
    type ProductScore,
    getProfile as apiGetProfile,
} from '@/lib/api'

export interface ChatMessage {
    role: 'user' | 'agent' | 'system'
    content: string
    timestamp: number
    type?: string
    widget?: {
        widget_type: string
        label: string
        options?: string[]
        min_value?: number
        max_value?: number
        step?: number
    } | null
}

export const useSessionStore = defineStore('session', () => {
    const sessionId = ref<string | null>(null)
    const phase = ref<string>('idle')
    const messages = ref<ChatMessage[]>([])
    const intentProfile = ref<IntentProfile | null>(null)
    const products = ref<ProductScore[]>([])
    const convictionScore = ref(0)
    const isLoading = ref(false)
    const shortlist = ref<string[]>([])
    const progressSteps = ref<string[]>([])

    const hasProducts = computed(() => products.value.length > 0)

    async function startSession(language: string = 'en') {
        isLoading.value = true
        try {
            const res: SessionResponse = await apiCreateSession(language)
            sessionId.value = res.session_id
            phase.value = res.phase
            messages.value = []
            products.value = []
            intentProfile.value = null
            convictionScore.value = 0

            // Welcome message
            messages.value.push({
                role: 'agent',
                content: "I'm Krise, your AI shopping advisor. Tell me what you want to **achieve**, not what product you want. For example: *\"I need a phone for outdoor photography\"* or *\"laptop for running SolidWorks on a budget\"*.",
                timestamp: Date.now(),
                type: 'info',
            })
            progressSteps.value = []
        } finally {
            isLoading.value = false
        }
        return sessionId.value
    }

    async function sendMessage(content: string) {
        if (!sessionId.value) return

        messages.value.push({
            role: 'user',
            content,
            timestamp: Date.now(),
        })

        isLoading.value = true
        progressSteps.value = []

        let profilePoll: number | null = null
        if (phase.value === 'product_recommendation' || convictionScore.value >= 0.7) {
            // Start polling for progress if we're generating products
            profilePoll = window.setInterval(async () => {
                if (!isLoading.value) {
                    if (profilePoll) clearInterval(profilePoll)
                    return
                }
                try {
                    const profileRes = await apiGetProfile(sessionId.value!)
                    if (profileRes.progress_steps) {
                        progressSteps.value = profileRes.progress_steps
                    }
                } catch {
                    // Ignore poll errors
                }
            }, 1000)
        }

        try {
            const res: MessageResponse = await apiSendMessage(sessionId.value, content)

            const msg: ChatMessage = {
                role: 'agent',
                content: res.content,
                timestamp: Date.now(),
                type: res.type,
            }

            // Attach widget if the backend sent one
            if ((res as any).widget) {
                msg.widget = (res as any).widget
            }

            messages.value.push(msg)

            if (res.intent_profile) {
                intentProfile.value = res.intent_profile
            }
            convictionScore.value = res.conviction_score

            if (res.type === 'recommendations' && res.products.length > 0) {
                products.value = res.products
                phase.value = 'product_recommendation'
            } else if (res.type === 'question') {
                phase.value = 'socratic_friction'
            }

            // Fetch final profile for progress if polled
            try {
                const finalProfile = await apiGetProfile(sessionId.value)
                if (finalProfile.progress_steps) progressSteps.value = finalProfile.progress_steps
            } catch { }

        } catch (err: any) {
            messages.value.push({
                role: 'system',
                content: `Something went wrong: ${err.message || 'Network error'}`,
                timestamp: Date.now(),
                type: 'error',
            })
        } finally {
            isLoading.value = false
            if (profilePoll) window.clearInterval(profilePoll)
        }
    }

    async function handleSwipe(productId: string, direction: string, reason?: string) {
        if (!sessionId.value) return

        if (direction === 'right') {
            shortlist.value.push(productId)
        }

        try {
            const res = await apiSwipe(sessionId.value, productId, direction, reason)
            // Remove swiped product
            products.value = products.value.filter((p: ProductScore) => p.product.id !== productId)

            // If new products were fetched (deck refill), add them
            if (res.remaining_count > products.value.length) {
                // Server has more products; could refresh from API
            }

            // Check if deck is empty after swipe and all products consumed
            if (products.value.length === 0) {
                sendMessage("I've finished shortlisting the recommended products.")
            }
        } catch (err) {
            console.error('Swipe failed:', err)
        }
    }

    return {
        sessionId,
        phase,
        messages,
        intentProfile,
        products,
        convictionScore,
        isLoading,
        shortlist,
        hasProducts,
        progressSteps,
        startSession,
        sendMessage,
        handleSwipe,
    }
})
