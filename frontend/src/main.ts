import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import HomeView from './views/HomeView.vue'
import SessionView from './views/SessionView.vue'

const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        { path: '/', name: 'home', component: HomeView },
        { path: '/session/:id', name: 'session', component: SessionView },
    ],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
