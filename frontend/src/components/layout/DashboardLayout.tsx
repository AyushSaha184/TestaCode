import type { PropsWithChildren } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

interface DashboardLayoutProps extends PropsWithChildren {
  title: string;
  subtitle: string;
}

export function DashboardLayout({ title, subtitle, children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen">
      <Sidebar isMobile />
      <div className="lg:pl-56">
        <Header title={title} subtitle={subtitle} />
        <main className="px-3 pb-6 md:px-5">{children}</main>
      </div>
    </div>
  );
}
