import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import ChatWindow from "@/components/ChatWindow";
import { MessageSquare } from "lucide-react";
import { Toaster } from "react-hot-toast";

export function AppShell() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-transparent md:flex">
      {/* Mobile Menu Overlay — always rendered, visibility controlled by CSS
          to keep sibling positions stable for React reconciliation */}
      <div
        className={`fixed inset-0 z-30 bg-black/50 md:hidden transition-opacity duration-200 ${
          isMobileMenuOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setIsMobileMenuOpen(false)}
      />

      {/* Sidebar - Desktop or Mobile Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-40 w-72 transform transition-transform duration-300 ease-in-out md:relative md:transform-none md:transition-none ${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <Sidebar onClose={() => setIsMobileMenuOpen(false)} />
      </div>

      {/* Main Content Area */}
      <div className="flex min-h-screen flex-1 flex-col w-full">
        <Topbar onMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)} />
        <main className="flex-1 p-4 md:p-6">
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>

      {/* Chat Toggle Button — always rendered, hidden via CSS when chat is open */}
      <button
        onClick={() => setIsChatOpen(true)}
        className={`fixed right-4 bottom-4 w-14 h-14 bg-blue-500 text-white rounded-full shadow-lg hover:bg-blue-600 transition-all flex items-center justify-center z-40 ${
          isChatOpen ? "scale-0 opacity-0 pointer-events-none" : "scale-100 opacity-100"
        }`}
        title={t("common.openChat")}
        aria-label={t("common.openChat")}
      >
        <MessageSquare className="w-6 h-6" />
      </button>

      {/* Chat Window */}
      <ChatWindow isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />

      {/* Toast Notifications */}
      <Toaster position="top-right" />
    </div>
  );
}

