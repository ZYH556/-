"use client";

import { Workspace } from "../../_components/Workspace";
import { useAuthSession } from "@/lib/authContext";

export default function ChatPage() {
  const { auth, onLogout } = useAuthSession();
  return <Workspace embedded token={auth.access_token} user={auth.user} onLogout={onLogout} />;
}
