"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Activity,
  TrendingUp,
  Search,
  BarChart3,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Blockchain", href: "/blockchain", icon: Activity },
  { name: "Smart Money", href: "/smart-money", icon: TrendingUp },
  { name: "Address Lookup", href: "/address", icon: Search },
  { name: "Metrics", href: "/metrics", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 border-r bg-card">
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">B</span>
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-sm">Babylon</span>
            <span className="text-xs text-muted-foreground">Analytics</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                isActive
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t">
        <div className="text-xs text-muted-foreground">
          <div className="font-medium">Babylon Genesis Chain</div>
          <div>On-Chain Analytics Platform</div>
        </div>
      </div>
    </div>
  );
}
