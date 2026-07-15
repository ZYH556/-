<template>
  <view class="metric-grid">
    <view v-for="item in items" :key="item.label" class="metric">
      <text class="metric-label">{{ item.label }}</text>
      <text class="metric-value">{{ item.value }}</text>
    </view>
  </view>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});
</script>

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.metric {
  padding: 22rpx;
  border: 1rpx solid #e7e3da;
  background: #fbfaf7;
}

.metric-label {
  color: #64748b;
  font-size: 22rpx;
}

.metric-value {
  display: block;
  margin-top: 8rpx;
  color: #051a24;
  font-size: 38rpx;
  font-weight: 700;
}
</style>
