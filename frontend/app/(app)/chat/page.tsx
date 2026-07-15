"use client";

import { PageHeader } from "@/components/workspace";
import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { OneSentenceVideoPush } from "@/components/learning-demo/OneSentenceVideoPush";
import { TutorActionBar } from "@/components/chat/TutorActionBar";
import { TutorEmptyState } from "@/components/chat/TutorEmptyState";
import { VirtualHumanPanel } from "@/components/virtual-human/VirtualHumanPanel";
import { Workspace } from "../../_components/Workspace";
import { useAuthSession } from "@/lib/authContext";

export default function ChatPage() {
  const { auth, onLogout } = useAuthSession();
  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="AI Tutor"
        title="1 对 1 AI 学习导师"
        description="围绕你的课程、考试或项目目标，先诊断基础与薄弱点，再协助规划路径、解释知识点、生成练习和推荐学习资源。"
      />
      <AgentProcessPanel page="chat" />
      <OneSentenceVideoPush />
      <Workspace
        embedded
        token={auth.access_token}
        user={auth.user}
        onLogout={onLogout}
        showTools={false}
        emptyState={<TutorEmptyState />}
        actionBar={({ disabled, onSelect }) => (
          <TutorActionBar disabled={disabled} onSelect={onSelect} />
        )}
      />
      <VirtualHumanPanel />
    </section>
  );
}
