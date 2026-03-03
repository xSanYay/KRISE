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
} from '@/lib/api'

export interface ChatMessage {
    role: 'user' | 'agent' | 'system'
    content: string
    timestamp: number
    type?: string
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
                content: "Hey! I'm Krise — your AI shopping advisor. Tell me what you want to **achieve**, not what product you want. For example: *\"I need a phone for outdoor photography\"* or *\"laptop for running SolidWorks on a budget\"*. What are you looking for?",
                timestamp: Date.now(),
                type: 'info',
            })
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
        try {
            const res: MessageResponse = await apiSendMessage(sessionId.value, content)

            messages.value.push({
                role: 'agent',
                content: res.content,
                timestamp: Date.now(),
                type: res.type,
            })

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
        } catch (err: any) {
            messages.value.push({
                role: 'system',
                content: `Something went wrong: ${err.message || 'Network error'}`,
                timestamp: Date.now(),
                type: 'error',
            })
        } finally {
            isLoading.value = false
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
            products.value = products.value.filter(p => p.product.id !== productId)

            if (res.next_product) {
                // Re-sort might have changed
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
        startSession,
        sendMessage,
        handleSwipe,
    }
})
