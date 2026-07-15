<template>
  <view class="page">
    <rl-page-header
      eyebrow="Courses"
      title="精品课程"
      description="围绕一门课组织视频、章节、讨论区和 AI 回复，保证移动端录屏完整。"
    />

    <rl-agent-flow :steps="agentFlows.course" />

    <rl-card eyebrow="Player" :title="currentCourse.title">
      <view class="player" @click="playing = !playing">
        <text class="play-icon">{{ playing ? "暂停" : "播放" }}</text>
        <text class="player-title">{{ currentChapter }}</text>
        <text class="player-sub">{{ currentCourse.weakPoint }} · {{ currentCourse.minutes }} 分钟</text>
      </view>
      <view class="section-gap">
        <rl-progress label="课程进度" :percent="currentCourse.progress" />
      </view>
    </rl-card>

    <rl-card eyebrow="Chapters" title="课程目录">
      <view v-for="(chapter, index) in currentCourse.chapters" :key="chapter" class="chapter" :class="{ active: index === chapterIndex }" @click="chapterIndex = index">
        <text>{{ chapter }}</text>
        <rl-tag :tone="index === chapterIndex ? 'accent' : 'muted'">{{ index === chapterIndex ? "学习中" : "待学" }}</rl-tag>
      </view>
    </rl-card>

    <rl-card eyebrow="Recommended" title="薄弱点课程推荐">
      <view v-for="course in courses" :key="course.id" class="course-card" @click="selectCourse(course.id)">
        <text class="course-title">{{ course.title }}</text>
        <text class="muted">{{ course.weakPoint }}</text>
        <rl-progress :percent="course.progress" />
      </view>
    </rl-card>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { agentFlows, courses } from "@/common/demo-data.js";

const selectedId = ref(courses[0].id);
const chapterIndex = ref(0);
const playing = ref(false);
const currentCourse = computed(() => courses.find((item) => item.id === selectedId.value) || courses[0]);
const currentChapter = computed(() => currentCourse.value.chapters[chapterIndex.value] || currentCourse.value.chapters[0]);

function selectCourse(id) {
  selectedId.value = id;
  chapterIndex.value = 0;
  playing.value = true;
}
</script>

<style scoped>
.player {
  display: flex;
  min-height: 360rpx;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28rpx;
  border-radius: 18rpx;
  background: #071923;
  color: #ffffff;
  text-align: center;
}

.play-icon {
  padding: 18rpx 26rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.24);
  border-radius: 999rpx;
  color: #ffffff;
  font-size: 26rpx;
}

.player-title {
  margin-top: 28rpx;
  color: #ffffff;
  font-size: 34rpx;
  font-weight: 700;
}

.player-sub {
  margin-top: 12rpx;
  color: rgba(255, 255, 255, 0.64);
  font-size: 24rpx;
}

.chapter,
.course-card {
  margin-top: 14rpx;
  padding: 20rpx;
  border: 1rpx solid #e7e3da;
  background: #fbfaf7;
}

.chapter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #051a24;
  font-size: 26rpx;
}

.chapter.active {
  border-color: #67e8f9;
  background: #ecfeff;
}

.course-title {
  display: block;
  margin-bottom: 8rpx;
  color: #051a24;
  font-size: 28rpx;
  font-weight: 700;
}
</style>
