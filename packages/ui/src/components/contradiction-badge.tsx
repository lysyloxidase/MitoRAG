import { AlertTriangle } from "lucide-react";

export function ContradictionBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded border border-[#ff4242]/50 bg-[#3a1518] px-3 py-1 text-sm text-[#ffb3b8]">
      <AlertTriangle size={14} />
      {label}
    </span>
  );
}
