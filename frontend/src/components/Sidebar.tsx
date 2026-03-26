"use client";

import { 
    Home, 
    GraduationCap, 
    CheckCircle, 
    Calendar, 
    FileText, 
    MessageSquare, 
    Target, 
    Settings,
    LogOut,
    User
} from "lucide-react";
import { useAuth } from "./AuthProvider";

interface SidebarProps {
    activeView: string;
    onNavigate: (view: string) => void;
}

const NAV_ITEMS = [
    { id: "dashboard", icon: <Home size={20} />, label: "Dashboard" },
    { id: "courses", icon: <GraduationCap size={20} />, label: "Cours" },
    { id: "tasks", icon: <CheckCircle size={20} />, label: "Tasks" },
    { id: "calendar", icon: <Calendar size={20} />, label: "Calendar" },
    { id: "documents", icon: <FileText size={20} />, label: "Documents" },
    { id: "chat", icon: <MessageSquare size={20} />, label: "Chat" },
    { id: "focus", icon: <Target size={20} />, label: "Focus Mode" },
];

export default function Sidebar({ activeView, onNavigate }: SidebarProps) {
    const { user, logout } = useAuth();

    return (
        <aside className="nf-sidebar">
            {/* Logo */}
            <div className="nf-sidebar__logo">
                <div className="nf-sidebar__logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18.5 2.5H14.5L9.5 14L8.5 14L8.5 2.5H4.5V21.5H8.5L13.5 10L14.5 10L14.5 21.5H18.5V2.5Z" fill="url(#paint0_linear)" />
                        <defs>
                            <linearGradient id="paint0_linear" x1="4.5" y1="2.5" x2="18.5" y2="21.5" gradientUnits="userSpaceOnUse">
                                <stop stopColor="#fff" />
                                <stop offset="1" stopColor="#e0dffe" />
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <span className="nf-sidebar__logo-text">NovaFlow</span>
            </div>

            {/* User Profile Info */}
            {user && (
                <div className="nf-sidebar__user">
                    <div className="nf-sidebar__user-avatar-premium">
                        {user.full_name ? 
                            user.full_name.split(' ').map((n: any) => n[0]).join('').toUpperCase().slice(0, 2) : 
                            user.email[0].toUpperCase()
                        }
                    </div>
                    <div className="nf-sidebar__user-info">
                        <span className="nf-sidebar__user-name">{user.full_name || user.email.split('@')[0]}</span>
                        <span className="nf-sidebar__user-email">{user.email}</span>
                    </div>
                </div>
            )}

            {/* Navigation */}
            <nav className="nf-sidebar__nav">
                {NAV_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        className={`nf-sidebar__item ${activeView === item.id ? "nf-sidebar__item--active" : ""}`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nf-sidebar__icon">{item.icon}</span>
                        {item.label}
                    </button>
                ))}
            </nav>

            {/* Footer - Settings & Logout */}
            <div className="nf-sidebar__footer">
                <button
                    className={`nf-sidebar__item ${activeView === "settings" ? "nf-sidebar__item--active" : ""}`}
                    onClick={() => onNavigate("settings")}
                >
                    <span className="nf-sidebar__icon"><Settings size={20} /></span>
                    Settings
                </button>
                
                <button
                    className="nf-sidebar__item nf-sidebar__item--logout"
                    onClick={() => logout()}
                >
                    <span className="nf-sidebar__icon"><LogOut size={20} /></span>
                    Déconnexion
                </button>
            </div>
        </aside>
    );
}
