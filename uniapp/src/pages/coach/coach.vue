<template>
  <view class="page">
    <rl-page-header
      eyebrow="AI Coach"
      title="AI 智能辅导"
      description="一句话触发诊断、资源生成、视频推送和错题复盘，移动端用于录屏演示。"
    />

    <rl-agent-flow :steps="agentFlows.coach" />

    <rl-card eyebrow="Dialogue" title="辅导对话">
      <textarea class="textarea" v-model="question" />
      <button class="btn section-gap" @click="submit">{{ running ? "诊断中..." : "发送" }}</button>
      <view v-if="resultVisible" class="coach-result">
        <rl-tag tone="good">已生成辅导动作</rl-tag>
        <text class="result-title">命中薄弱点：Vue 组件通信、Pinia 状态管理</text>
        <view v-for="item in actions" :key="item" class="action-item">
          <text>{{ item }}</text>
        </view>
      </view>
    </rl-card>

    <rl-card eyebrow="Weakness" title="薄弱环节">
      <view class="chips">
        <rl-tag v-for="item in weakPoints" :key="item" tone="warm">{{ item }}</rl-tag>
      </view>
    </rl-card>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { agentFlows, weakPoints } from "@/common/demo-data.js";

const question = ref("我想先补 Vue 的组件通信，再做一套专项练习。");
const running = ref(false);
const resultVisible = ref(true);
const actions = ["推送 18 分钟短视频", "生成 3 道专项练习", "同步错题复盘到学习路径"];

function submit() {
  running.value = true;
  resultVisible.value = false;
  setTimeout(() => {
    running.value = false;
    resultVisible.value = true;
  }, 900);
}
</script>

<style scoped>
.coach-result {
  margin-top: 22rpx;
  padding: 24rpx;
  border: 1rpx solid #bbf7d0;
  background: #ecfdf5;
}

.result-title {
  display: block;
  margin-top: 14rpx;
  color: #051a24;
  font-size: 28rpx;
  font-weight: 700;
}

.action-item {
  margin-top: 14rpx;
  padding: 16rpx;
  border: 1rpx solid #bbf7d0;
  background: #ffffff;
  color: #166534;
  font-size: 24rpx;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
</style>
