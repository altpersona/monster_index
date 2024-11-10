<template>
  <div class="monster-index">
    <div class="title">MONSTER INDEX</div>

    <div class="card">
      <!-- Placeholder Image for Monster (Replace with your actual image path) -->
      <img class="monster-image" src="https://via.placeholder.com/200x250" alt="Monster Image" />

      <div class="section-title">MONSTER INDEX</div>

      <div class="stats">
        <!-- Loop through stats array to generate stat bars -->
        <div class="stat-row" v-for="stat in stats" :key="stat.name">
          <div class="stat-name">{{ stat.name }}</div>
          <div class="stat-bar-container">
            <div class="stat-bar" :style="{ width: stat.width + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="buttons">
        <!-- Action Buttons -->
        <button class="action-button">ACTIV</button>
        <button class="action-button secondary">RENOWN</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      // Sample stats data (name and width as percentage for each stat bar)
      stats: [
        { name: 'Strength', width: 75 },
        { name: 'Speed', width: 50 },
        { name: 'Magic', width: 60 },
        { name: 'Defense', width: 40 },
      ],
    };
  },
};
</script>

<style scoped>
/* Base styling for the Monster Index component */
.monster-index {
  font-family: 'Fantasy', sans-serif;
  color: #ccc;
  text-align: center;
  padding: 20px;
  background-color: #1e1e2f;
  border-radius: 10px;
  width: 320px;
  margin: 0 auto;
}

/* Title styling */
.title {
  font-size: 1.8em;
  color: #ffffff;
  margin-bottom: 15px;
}

/* Card styling */
.card {
  background-color: #292943;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

/* Monster Image */
.monster-image {
  width: 100%;
  border-radius: 10px;
  margin-bottom: 15px;
}

/* Section title styling */
.section-title {
  font-size: 1.2em;
  color: #ffffff;
  margin: 15px 0;
}

/* Stats section styling */
.stats {
  margin: 15px 0;
}

.stat-row {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.stat-name {
  flex: 1;
  font-size: 0.9em;
  color: #b0b0d6;
}

.stat-bar-container {
  flex: 2;
  background-color: #44446b;
  border-radius: 5px;
  overflow: hidden;
  height: 10px;
  margin-left: 10px;
}

.stat-bar {
  height: 100%;
  background-color: #7b5ebc;
  transition: width 0.3s;
}

/* Buttons section styling */
.buttons {
  display: flex;
  justify-content: space-around;
  margin-top: 15px;
}

/* Action buttons styling */
.action-button {
  padding: 5px 15px;
  font-size: 0.9em;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  background-color: #7b5ebc;
  color: white;
  transition: background-color 0.3s;
}

.action-button:hover {
  background-color: #9b7edd;
}

.action-button.secondary {
  background-color: #bc5e7b;
}

.action-button.secondary:hover {
  background-color: #e06a92;
}
</style>
