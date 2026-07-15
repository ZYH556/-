<template>
  <view class="card" :class="{ compact }">
    <view v-if="eyebrow || title || $slots.action" class="card-head">
      <view class="head-text">
        <text v-if="eyebrow" class="eyebrow">{{ eyebrow }}</text>
        <text v-if="title" class="card-title">{{ title }}</text>
      </view>
      <view v-if="$slots.action" class="head-action">
        <slot name="action" />
      </view>
    </view>
    <slot />
  </view>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: "",
  },
  title: {
    type: String,
    default: "",
  },
  compact: {
    type: Boolean,
    default: false,
  },
});
</script>

<style scoped>
.card {
  margin-top: 26rpx;
  padding: 28rpx;
  background: #ffffff;
  border: 1rpx solid #e7e3da;
  border-radius: 20rpx;
  box-shadow: 0 2rpx 6rpx rgba(5, 26, 36, 0.04);
  box-sizing: border-box;
}

.compact {
  padding: 22rpx;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18rpx;
  margin-bottom: 22rpx;
}

.head-text {
  min-width: 0;
  flex: 1;
}

.head-action {
  flex-shrink: 0;
}
</style>
