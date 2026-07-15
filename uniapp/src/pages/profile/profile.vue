<template>
  <view class="page">
    <rl-page-header
      eyebrow="Profile"
      title="学习画像"
      :description="`${activeCourse.subject} · ${activeCourse.grade}，目标方向：${activeCourse.target}`"
    />

    <rl-agent-flow :steps="agentFlows.profile" />

    <rl-card eyebrow="Learner" title="当前画像">
      <rl-metric-grid :items="profileMetrics" />
    </rl-card>

    <rl-card eyebrow="Gap" title="行业能力差距">
      <view v-for="item in capabilityGaps" :key="item.label" class="gap-item">
        <view class="between">
          <text class="gap-title">{{ item.label }}</text>
          <rl-tag tone="warm">{{ item.status }}</rl-tag>
        </view>
        <rl-progress :label="`当前 ${item.current}% / 目标 ${item.target}%`" :percent="item.current" />
      </view>
    </rl-card>

    <rl-card eyebrow="Mentor" title="导师匹配">
      <view v-for="mentor in mentorCards" :key="mentor.name" class="mentor">
        <view>
          <text class="mentor-name">{{ mentor.name }}</text>
          <text class="muted">{{ mentor.title }}</text>
        </view>
        <rl-tag tone="accent">{{ mentor.match }}%</rl-tag>
      </view>
    </rl-card>
  </view>
</template>

<script setup>
import { activeCourse, agentFlows, capabilityGaps, mentorCards } from "@/common/demo-data.js";

const profileMetrics = [
  { label: "学习天数", value: "27" },
  { label: "正确率", value: "74%" },
  { label: "知识文档", value: "236" },
  { label: "待复盘", value: "8" },
];
</script>

<style scoped>
.gap-item {
  margin-top: 18rpx;
  padding: 20rpx;
  border: 1rpx solid #e7e3da;
  background: #fbfaf7;
}

.gap-title {
  max-width: 420rpx;
  color: #051a24;
  font-size: 26rpx;
  font-weight: 700;
}

.mentor {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14rpx;
  padding: 20rpx;
  border: 1rpx solid #e7e3da;
  background: #fbfaf7;
}

.mentor-name {
  display: block;
  color: #051a24;
  font-size: 28rpx;
  font-weight: 700;
}
</style>
