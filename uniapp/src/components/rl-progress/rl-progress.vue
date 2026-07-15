<template>
  <view class="progress-wrap">
    <view v-if="label" class="between">
      <text class="muted">{{ label }}</text>
      <text class="percent">{{ percent }}%</text>
    </view>
    <view class="progress">
      <view class="progress-fill" :style="{ width: `${safePercent}%` }" />
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  percent: {
    type: Number,
    default: 0,
  },
  label: {
    type: String,
    default: "",
  },
});

const safePercent = computed(() => Math.max(0, Math.min(100, props.percent)));
</script>

<style scoped>
.progress-wrap {
  width: 100%;
}

.percent {
  color: #051a24;
  font-size: 24rpx;
  font-weight: 600;
}

.progress {
  height: 12rpx;
  margin-top: 12rpx;
  overflow: hidden;
  border-radius: 999rpx;
  background: rgba(5, 26, 36, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: #0e7490;
}
</style>
