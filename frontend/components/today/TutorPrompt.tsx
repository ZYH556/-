import Link from "next/link";
import { MessageSquareText, Sparkles } from "lucide-react";

type TutorPromptProps = {
  prompt: {
    message: string;
    actionLabel: string;
    href: string;
  };
};

export function TutorPrompt({ prompt }: TutorPromptProps) {
  return (
    <section className="bg-[#051a24] p-5 text-white">
      <div className="flex items-center gap-2 text-cyan-100">
        <Sparkles size={17} aria-hidden />
        <span className="text-xs font-medium uppercase tracking-[0.18em]">AI Tutor</span>
      </div>
      <p className="mt-4 text-lg font-medium leading-7">
        {prompt.message}
      </p>
      <Link
        href={prompt.href}
        className="mt-5 inline-flex items-center gap-2 bg-white px-4 py-2.5 text-sm font-medium text-[#051a24] transition-opacity hover:opacity-90"
      >
        <MessageSquareText size={16} aria-hidden />
        {prompt.actionLabel}
      </Link>
    </section>
  );
}
