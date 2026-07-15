<template>
  <rl-card eyebrow="Trace" :title="title">
    <template #action>
      <rl-tag tone="accent">{{ doneCount }}/{{ steps.length }}</rl-tag>
    </template>
    <view class="flow">
      <view v-for="(step, index) in steps" :key="`${step[0]}-${index}`" class="agent-step">
        <view class="row">
          <view class="agent-dot" />
          <text class="agent-name">{{ step[0] }}</text>
          <rl-tag :tone="index < doneCount ? 'good' : 'warm'">
            {{ index < doneCount ? "已完成" : "调用中" }}
          </rl-tag>
        </view>
        <text class="agent-task">{{ step[1] }}</text>
        <text class="muted">{{ step[2] }}</text>
      </view>
    </view>
  </rl-card>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: "Agent 调用过程",
  },
  steps: {
    type: Array,
    default: () => [],
  },
  doneCount: {
    type: Number,
    default: 2,
  },
});
</script>

<style scoped>
.flow {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.agent-step {
  padding: 20rpx;
  border: 1rpx solid #e7e3da;
  background: #fbfaf7;
}

.agent-dot {
  width: 18rpx;
  height: 18rpx;
  margin-right: 12rpx;
  border-radius: 999rpx;
  background: #0e7490;
}

.agent-name {
  min-width: 0;
  flex: 1;
  color: #051a24;
  font-size: 26rpx;
  font-weight: 700;
}

.agent-task {
  display: block;
  margin-top: 14rpx;
  color: #051a24;
  font-size: 26rpx;
}
</style>
