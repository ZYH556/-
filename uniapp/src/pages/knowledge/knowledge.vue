<template>
  <view class="page">
    <rl-page-header
      eyebrow="Knowledge"
      title="个人知识库"
      description="移动端展示 200+ 知识文档、用户需求和文档 Agent 持续调用过程。"
    />

    <rl-agent-flow :steps="agentFlows.knowledge" />

    <rl-card eyebrow="Live Retrieval" title="知识库调用监控">
      <template #action>
        <rl-tag tone="accent">调用中</rl-tag>
      </template>
      <rl-metric-grid :items="metrics" />
      <view class="active-doc">
        <text class="muted">正在调用文档</text>
        <text class="active-title">{{ activeDoc.title }}</text>
        <text class="muted">{{ activeDoc.course }} · {{ activeDoc.format }}</text>
      </view>
    </rl-card>

    <rl-card eyebrow="Documents" :title="`已接入 ${knowledgeDocs.length} 份知识文档`">
      <scroll-view class="doc-list" scroll-y>
        <view
          v-for="doc in visibleDocs"
          :key="doc.id"
          class="doc-item"
          :class="{ active: doc.id === activeDoc.id }"
        >
          <view class="doc-icon">文</view>
          <view class="doc-body">
            <text class="doc-title">{{ doc.title }}</text>
            <text class="muted">{{ doc.course }}</text>
          </view>
          <view class="doc-tags">
            <rl-tag tone="muted">{{ doc.format }}</rl-tag>
            <rl-tag tone="warm">演示</rl-tag>
          </view>
        </view>
      </scroll-view>
    </rl-card>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { agentFlows, knowledgeDocs, userNeeds, weakPoints } from "@/common/demo-data.js";

const callIndex = ref(0);
let timer;

const metrics = [
  { label: "知识文档", value: `${knowledgeDocs.length}+` },
  { label: "用户需求", value: String(userNeeds.length) },
  { label: "薄弱点标签", value: String(weakPoints.length) },
  { label: "检索调用", value: "持续中" },
];

const activeDoc = computed(() => knowledgeDocs[callIndex.value % knowledgeDocs.length]);
const visibleDocs = computed(() => knowledgeDocs.slice(0, 48));

onMounted(() => {
  timer = setInterval(() => {
    callIndex.value = (callIndex.value + 1) % knowledgeDocs.length;
  }, 1000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.active-doc {
  margin-top: 24rpx;
  padding: 22rpx;
  border: 1rpx solid #bae6fd;
  background: #ecfeff;
}

.active-title {
  display: block;
  margin: 8rpx 0;
  color: #051a24;
  font-size: 28rpx;
  font-weight: 700;
}

.doc-list {
  height: 720rpx;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #e7e3da;
}

.doc-item.active {
  padding-left: 16rpx;
  padding-right: 16rpx;
  border: 1rpx solid #67e8f9;
  background: #ecfeff;
}

.doc-icon {
  width: 64rpx;
  height: 64rpx;
  border-radius: 14rpx;
  background: #e0f2fe;
  color: #0e7490;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 64rpx;
  text-align: center;
}

.doc-body {
  min-width: 0;
  flex: 1;
}

.doc-title {
  display: block;
  overflow: hidden;
  color: #051a24;
  font-size: 26rpx;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-tags {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
</style>
