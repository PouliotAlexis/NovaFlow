import React, { useState, useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';

type Job = {
    id: string;
    name: string;
    duration: string;
    status: string;
};

export default function AutomationStatus() {
    const [logs, setLogs] = useState<string[]>([]);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [isAnalysing, setIsAnalysing] = useState(false);
    const [lastMessage, setLastMessage] = useState("");
    const [showDetails, setShowDetails] = useState(false);
    const prevJobCount = useRef(0);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    useEffect(() => {
        const fetchData = async () => {
            try {
                const logsRes = await fetch(`${API_URL}/api/automation/logs`);
                if (logsRes.ok) {
                    const data = await logsRes.json();
                    const newLogs = data.logs || [];
                    setLogs(newLogs);
                    if (newLogs.length > 0) {
                        const lastLog = newLogs[newLogs.length - 1];
                        const cleanMessage = lastLog.replace(/^\[.*?\]\s*/, '');
                        setLastMessage(cleanMessage);
                    }
                }

                const jobsRes = await fetch(`${API_URL}/api/automation/jobs`);
                if (jobsRes.ok) {
                    const jobsData = await jobsRes.json();
                    setJobs(jobsData);
                    setIsAnalysing(jobsData.length > 0);

                    if (prevJobCount.current > 0 && jobsData.length === 0) {
                        window.dispatchEvent(new CustomEvent("novaflow-automation-done"));
                    }
                    prevJobCount.current = jobsData.length;
                }
            } catch (error) {
                console.warn("Error fetching automation data", error);
            }
        };

        const interval = setInterval(fetchData, 2000);
        fetchData();
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowDetails(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const killJob = async (jobId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Stop this process?")) return;
        try {
            await fetch(`${API_URL}/api/automation/jobs/${jobId}`, { method: 'DELETE' });
            setJobs(jobs.filter(j => j.id !== jobId));
        } catch (err) {
            alert("Error stopping process");
        }
    };

    if (!lastMessage && jobs.length === 0) return null;

    return (
        <div style={{ position: 'relative' }} ref={dropdownRef}>
            {/* Main Badge */}
            <div
                onClick={() => setShowDetails(!showDetails)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    color: isAnalysing ? 'var(--nf-accent)' : 'var(--nf-text-muted)',
                    background: isAnalysing ? 'var(--nf-accent-glow)' : 'var(--nf-bg-card)',
                    padding: '5px 12px',
                    borderRadius: '16px',
                    border: isAnalysing ? '1px solid var(--nf-accent-dim)' : '1px solid var(--nf-border)',
                    transition: 'all var(--nf-transition)',
                    cursor: 'pointer',
                    userSelect: 'none' as const,
                    fontWeight: 500,
                }}
            >
                {isAnalysing ? (
                    <Activity size={12} className="nf-spin-slow" />
                ) : (
                    <Activity size={12} style={{ opacity: 0.5 }} />
                )}
                <span style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {jobs.length > 0 ? `${jobs.length} active process${jobs.length > 1 ? "es" : ""}` : lastMessage}
                </span>
            </div>

            {/* Dropdown */}
            {showDetails && (
                <div className="nf-card nf-animate-in" style={{
                    position: 'absolute',
                    top: '110%',
                    right: 0,
                    width: '320px',
                    zIndex: 1000,
                    padding: 0,
                    overflow: 'hidden',
                    boxShadow: 'var(--nf-shadow-lg)',
                    border: '1px solid var(--nf-border-active)',
                }}>
                    <div style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid var(--nf-border)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'var(--nf-bg-secondary)'
                    }}>
                        <span style={{ fontWeight: 600, fontSize: '13px' }}>Active Processes</span>
                        <span style={{ color: 'var(--nf-text-muted)', fontSize: '10px' }}>Auto-refresh</span>
                    </div>

                    <div style={{ padding: '12px 16px' }}>
                        {jobs.length === 0 ? (
                            <p style={{ fontSize: '12px', color: 'var(--nf-text-muted)', fontStyle: 'italic' }}>No active processes.</p>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {jobs.map(job => (
                                    <div key={job.id} style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: '8px',
                                        background: 'var(--nf-bg-card)',
                                        borderRadius: 'var(--nf-radius-xs)',
                                        border: '1px solid var(--nf-border)',
                                        fontSize: '12px'
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: 500, color: 'var(--nf-text)' }}>{job.name}</div>
                                            <div style={{ color: 'var(--nf-text-muted)', fontSize: '10px' }}>{job.duration} elapsed</div>
                                        </div>
                                        <button
                                            onClick={(e) => killJob(job.id, e)}
                                            className="nf-btn nf-btn--danger"
                                            style={{ fontSize: '10px', padding: '3px 8px' }}
                                        >
                                            STOP
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div style={{ marginTop: '12px', borderTop: '1px solid var(--nf-border)', paddingTop: '8px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px', color: 'var(--nf-text-muted)' }}>Recent Logs</div>
                            <div style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--nf-text-muted)', maxHeight: '80px', overflowY: 'auto' }}>
                                {logs.slice(-5).map((log, i) => (
                                    <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
