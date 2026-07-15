<template>
  <view class="header">
    <text class="eyebrow">{{ eyebrow }}</text>
    <text class="title">{{ title }}</text>
    <text v-if="description" class="desc">{{ description }}</text>
    <view v-if="$slots.action" class="action">
      <slot name="action" />
    </view>
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
    required: true,
  },
  description: {
    type: String,
    default: "",
  },
});
</script>

<style scoped>
.header {
  padding-top: 8rpx;
}

.action {
  margin-top: 22rpx;
}
</style>
