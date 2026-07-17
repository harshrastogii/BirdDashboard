"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Telescope } from "lucide-react";

import { visibleSections } from "./nav-config";
import { cn } from "@/lib/utils";
import { APP_NAME, FEATURES } from "@/lib/config";

export function Sidebar() {
  const pathname = usePathname();
  const sections = visibleSections(FEATURES.roadmapModules);

  return (
    <aside className="hidden md:flex h-svh w-64 shrink-0 flex-col border-r border-border bg-card">
      <Link href="/dashboard" className="flex items-center gap-2.5 px-5 h-16 border-b border-border">
        <span className="grid place-items-center size-8 rounded-md bg-primary text-primary-foreground">
          <Telescope className="size-5" />
        </span>
        <span className="font-semibold tracking-tight">{APP_NAME}</span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {sections.map((section) => (
          <div key={section.title} className="mb-5">
            <p className="specimen-label px-2 mb-1.5">{section.title}</p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                        active
                          ? "bg-primary/10 text-primary font-medium"
                          : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                      )}
                    >
                      <Icon className="size-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                      {item.status === "soon" && (
                        <span className="ml-auto text-[10px] uppercase tracking-wide text-muted-foreground/70">
                          Soon
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-5 py-3 specimen-label">
        PRT840 · Charles Darwin University
      </div>
    </aside>
  );
}
