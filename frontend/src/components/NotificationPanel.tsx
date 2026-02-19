"use client";

import React, { useState, useEffect, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Notification {
    id: string;
    title: string;
    content: string;
    type: "info" | "warning" | "deadline" | "success";
    timestamp: string;
    read: boolean;
}

export default function NotificationPanel() {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const unreadCount = notifications.filter((n) => !n.read).length;

    const fetchNotifications = async () => {
        try {
            const res = await fetch(`${API_URL}/api/notifications`);
            if (res.ok) {
                const data = await res.json();
                setNotifications(data.notifications || []);
            }
        } catch (err) {
            console.error("Error fetching notifications:", err);
        }
    };

    useEffect(() => {
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const markAsRead = async (id: string) => {
        try {
            const res = await fetch(`${API_URL}/api/notifications/read/${id}`, { method: "POST" });
            if (res.ok) {
                setNotifications((prev) =>
                    prev.map((n) => (n.id === id ? { ...n, read: true } : n))
                );
            }
        } catch (err) {
            console.error("Error marking as read:", err);
        }
    };

    const markAllAsRead = async () => {
        try {
            const res = await fetch(`${API_URL}/api/notifications/read-all`, { method: "POST" });
            if (res.ok) {
                setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
            }
        } catch (err) {
            console.error("Error marking all as read:", err);
        }
    };

    const clearAll = async () => {
        if (!confirm("Clear all notifications?")) return;
        try {
            const res = await fetch(`${API_URL}/api/notifications`, { method: "DELETE" });
            if (res.ok) {
                setNotifications([]);
            }
        } catch (err) {
            console.error("Error clearing notifications:", err);
        }
    };

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        if (diff < 60000) return "Just now";
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString("en-US");
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case "deadline": return "⏰";
            case "warning": return "⚠️";
            case "success": return "✅";
            default: return "ℹ️";
        }
    };

    return (
        <div style={{ position: "relative" }} ref={dropdownRef}>
            <button
                className="nf-btn--icon"
                onClick={() => setIsOpen(!isOpen)}
                style={{ position: "relative" }}
            >
                <span>🔔</span>
                {unreadCount > 0 && (
                    <span style={{
                        position: "absolute",
                        top: "-2px",
                        right: "-2px",
                        background: "var(--nf-danger)",
                        color: "white",
                        fontSize: "9px",
                        fontWeight: 700,
                        borderRadius: "50%",
                        width: "16px",
                        height: "16px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: "0 0 0 2px var(--nf-bg-primary)"
                    }}>
                        {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <div className="nf-card nf-animate-in" style={{
                    position: "absolute",
                    top: "120%",
                    right: 0,
                    width: "320px",
                    maxHeight: "450px",
                    zIndex: 1000,
                    padding: 0,
                    overflow: "hidden",
                    boxShadow: "var(--nf-shadow-lg)",
                    border: "1px solid var(--nf-border-active)"
                }}>
                    <div style={{
                        padding: "12px 16px",
                        borderBottom: "1px solid var(--nf-border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        background: "var(--nf-bg-secondary)"
                    }}>
                        <span style={{ fontWeight: 600, fontSize: "13px" }}>Notifications</span>
                        {notifications.length > 0 && (
                            <div style={{ display: "flex", gap: "8px" }}>
                                <button
                                    onClick={markAllAsRead}
                                    style={{ fontSize: "11px", color: "var(--nf-accent)", background: "none", border: "none", cursor: "pointer", fontWeight: 500 }}
                                >
                                    Read All
                                </button>
                                <button
                                    onClick={clearAll}
                                    style={{ fontSize: "11px", color: "var(--nf-text-muted)", background: "none", border: "none", cursor: "pointer" }}
                                >
                                    Clear
                                </button>
                            </div>
                        )}
                    </div>

                    <div style={{ maxHeight: "380px", overflowY: "auto" }}>
                        {notifications.length === 0 ? (
                            <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--nf-text-muted)" }}>
                                <span style={{ fontSize: "24px", display: "block", marginBottom: "8px" }}>📭</span>
                                <p style={{ fontSize: "13px" }}>No notifications</p>
                            </div>
                        ) : (
                            notifications.map((notif) => (
                                <div
                                    key={notif.id}
                                    onClick={() => !notif.read && markAsRead(notif.id)}
                                    style={{
                                        padding: "12px 16px",
                                        borderBottom: "1px solid var(--nf-border)",
                                        background: notif.read ? "transparent" : "var(--nf-accent-glow)",
                                        cursor: "pointer",
                                        transition: "background var(--nf-transition)",
                                        position: "relative"
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--nf-bg-hover)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.background = notif.read ? "transparent" : "var(--nf-accent-glow)")}
                                >
                                    {!notif.read && (
                                        <div style={{
                                            position: "absolute",
                                            left: "4px",
                                            top: "50%",
                                            transform: "translateY(-50%)",
                                            width: "5px",
                                            height: "5px",
                                            borderRadius: "50%",
                                            background: "var(--nf-accent)"
                                        }} />
                                    )}
                                    <div style={{ display: "flex", gap: "10px" }}>
                                        <span style={{ fontSize: "16px" }}>{getTypeIcon(notif.type)}</span>
                                        <div style={{ flex: 1 }}>
                                            <div style={{
                                                fontSize: "13px",
                                                fontWeight: notif.read ? 500 : 700,
                                                color: "var(--nf-text)",
                                                marginBottom: "2px"
                                            }}>
                                                {notif.title}
                                            </div>
                                            <div style={{ fontSize: "12px", color: "var(--nf-text-secondary)", lineHeight: 1.4 }}>
                                                {notif.content}
                                            </div>
                                            <div style={{ fontSize: "10px", color: "var(--nf-text-muted)", marginTop: "4px" }}>
                                                {formatTime(notif.timestamp)}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
