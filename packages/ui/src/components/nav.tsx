import { BarChart3, Library, MessageSquareText, Network } from "lucide-react";
import Link from "next/link";

const items = [
  { href: "/", label: "Chat", icon: MessageSquareText },
  { href: "/kg", label: "KG Explorer", icon: Network },
  { href: "/papers", label: "Papers", icon: Library },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 }
] as const;

export function Nav() {
  return (
    <nav className="sticky top-0 z-30 border-b border-line bg-[#0b1016]/95 backdrop-blur">
      <div className="flex min-h-14 items-center justify-between px-4 md:px-6">
        <Link className="flex items-center gap-3 font-semibold text-ink" href="/">
          <span className="grid h-8 w-8 place-items-center rounded bg-ox text-sm text-[#101820]">
            M
          </span>
          MitoRAG
        </Link>
        <div className="flex items-center gap-1">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                className="inline-flex items-center gap-2 rounded px-3 py-2 text-sm text-muted hover:bg-[#13202a] hover:text-ink"
                href={item.href}
                key={item.href}
              >
                <Icon size={16} />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
