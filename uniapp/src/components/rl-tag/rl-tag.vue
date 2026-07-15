<template>
  <text class="rl-tag" :class="toneClass">
    <slot />
  </text>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  tone: {
    type: String,
    default: "accent",
  },
});

const toneClass = computed(() => `rl-tag-${props.tone}`);
</script>

<style scoped>
.rl-tag {
  display: inline-flex;
  align-items: center;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 600;
}

.rl-tag-accent {
  background: #eef8fb;
  color: #0e7490;
}

.rl-tag-dark {
  background: #051a24;
  color: #ffffff;
}

.rl-tag-warm {
  background: #fff7ed;
  color: #b45309;
}

.rl-tag-good {
  background: #ecfdf5;
  color: #047857;
}

.rl-tag-muted {
  background: #f1f5f9;
  color: #64748b;
}
</style>
