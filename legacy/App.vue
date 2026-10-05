<template>
  <div id="app">
    <MonsterIndex />
  </div>
</template>

<script>
import MonsterIndex from './components/MonsterIndex.vue';

export default {
  components: {
    MonsterIndex,
  },
};
</script>

<style>
/* Optional: Add global styles if necessary */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #2a2a3a;
  color: white;
}
</style>
