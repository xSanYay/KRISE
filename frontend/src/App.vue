<template>
  <div class="app-wrapper">
    <AppHeader />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppHeader from './components/layout/AppHeader.vue'
</script>

<style scoped>
.app-wrapper {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.app-main {
  flex: 1;
  overflow: auto;
}
</style>
