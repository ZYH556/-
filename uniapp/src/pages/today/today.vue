<template>
  <view class="page">
    <rl-page-header
      eyebrow="Today"
      title="今日学习"
      :description="`围绕《${activeCourse.course}》推进今日主任务，移动端同步展示路径、资源和 Agent 过程。`"
    />

    <rl-agent-flow :steps="agentFlows.today" />

    <rl-card eyebrow="Main Task" title="Vue 组件通信专项补强">
      <template #action>
        <rl-tag tone="dark">进行中</rl-tag>
      </template>
      <text class="muted">先完成短视频，再做 3 道状态管理练习，最后把错题复盘回写到学习路径。</text>
      <view class="section-gap">
        <rl-progress label="今日进度" :percent="62" />
      </view>
    </rl-card>

    <rl-card eyebrow="One Sentence" title="一句话推送视频">
      <input class="input" v-model="command" />
      <button class="btn section-gap" @click="runPush">{{ running ? "Agent 调用中..." : "执行" }}</button>
      <view v-if="pushed" class="push-result">
        <rl-tag tone="good">已推送</rl-tag>
        <text class="push-title">Vue 3 组件通信与 Pinia 状态管理</text>
        <text class="muted">视频 Agent 已关联课程和薄弱点，建议 18 分钟内完成。</text>
      </view>
    </rl-card>

    <rl-card eyebrow="Quick Entry" title="录屏入口">
      <view class="entry-grid">
        <button class="btn btn-ghost" @click="go('/pages/knowledge/knowledge')">知识库</button>
        <button class="btn btn-ghost" @click="go('/pages/coach/coach')">AI 辅导</button>
        <button class="btn btn-ghost" @click="go('/pages/course/course')">精品课程</button>
        <button class="btn btn-ghost" @click="go('/pages/profile/profile')">学习画像</button>
      </view>
    </rl-card>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { activeCourse, agentFlows } from "@/common/demo-data.js";

const command = ref("给我推送一个适合当前薄弱点的短视频");
const running = ref(false);
const pushed = ref(true);

function runPush() {
  running.value = true;
  pushed.value = false;
  setTimeout(() => {
    running.value = false;
    pushed.value = true;
  }, 900);
}

function go(url) {
  uni.switchTab({ url });
}
</script>

<style scoped>
.push-result {
  margin-top: 22rpx;
  padding: 22rpx;
  border: 1rpx solid #bae6fd;
  background: #ecfeff;
}

.push-title {
  display: block;
  margin-top: 14rpx;
  color: #051a24;
  font-size: 30rpx;
  font-weight: 700;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}
</style>
