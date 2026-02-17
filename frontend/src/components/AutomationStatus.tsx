import React, { useState, useEffect, useRef } from 'react';

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

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1. Logs
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

                // 2. Active Jobs
                const jobsRes = await fetch(`${API_URL}/api/automation/jobs`);
                if (jobsRes.ok) {
                    const jobsData = await jobsRes.json();
                    setJobs(jobsData);
                    setIsAnalysing(jobsData.length > 0);

                    // Détecter la fin de jobs (transition: jobs > 0 → jobs = 0)
                    if (prevJobCount.current > 0 && jobsData.length === 0) {
                        window.dispatchEvent(new CustomEvent("novaflow-automation-done"));
                    }
                    prevJobCount.current = jobsData.length;
                }

            } catch (error) {
                console.error("Error fetching automation data", error);
            }
        };

        const interval = setInterval(fetchData, 2000);
        fetchData();

        return () => clearInterval(interval);
    }, []);

    const killJob = async (jobId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Arrêter cette tâche ?")) return;
        try {
            await fetch(`${API_URL}/api/automation/jobs/${jobId}`, { method: 'DELETE' });
            // Force refresh
            setJobs(jobs.filter(j => j.id !== jobId));
        } catch (err) {
            alert("Erreur lors de l'annulation");
        }
    };

    if (!lastMessage && jobs.length === 0) return null;

    return (
        <div style={{ position: 'relative' }}>
            {/* Badge Principal */}
            <div
                className="nf-automation-status"
                onClick={() => setShowDetails(!showDetails)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12px',
                    color: isAnalysing ? 'var(--nf-accent)' : 'var(--nf-text-muted)',
                    background: 'rgba(0,0,0,0.2)',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    marginRight: '12px',
                    border: isAnalysing ? '1px solid var(--nf-accent-dim)' : '1px solid transparent',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer',
                    userSelect: 'none'
                }}
            >
                {isAnalysing && (
                    <span className="nf-spinner-dot" style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'currentColor',
                        display: 'inline-block',
                        animation: 'pulse 1s infinite'
                    }} />
                )}
                <span style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {jobs.length > 0 ? `${jobs.length} tâche(s) en cours...` : lastMessage}
                </span>
            </div>

            {/* Dropdown Détails */}
            {showDetails && (
                <div className="nf-card nf-animate-in" style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '8px',
                    width: '320px',
                    zIndex: 1000,
                    padding: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                    background: 'var(--nf-bg-secondary)',
                    border: '1px solid var(--nf-border)'
                }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                        Processus Actifs
                        <span style={{ color: 'var(--nf-text-muted)', fontSize: '11px', fontWeight: 400 }}>Mise à jour auto</span>
                    </h4>

                    {jobs.length === 0 ? (
                        <p style={{ fontSize: '12px', color: 'var(--nf-text-muted)', fontStyle: 'italic' }}>Aucun processus en cours.</p>
                    ) : (
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                            {jobs.map(job => (
                                <li key={job.id} style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '8px 0',
                                    borderBottom: '1px solid var(--nf-border-dim)',
                                    fontSize: '12px'
                                }}>
                                    <div>
                                        <div style={{ fontWeight: 500 }}>{job.name}</div>
                                        <div style={{ color: 'var(--nf-text-muted)', fontSize: '10px' }}>{job.duration} écoulées</div>
                                    </div>
                                    <button
                                        onClick={(e) => killJob(job.id, e)}
                                        title="Arrêter le processus"
                                        style={{
                                            background: 'var(--nf-error)',
                                            color: '#fff',
                                            border: 'none',
                                            borderRadius: '4px',
                                            padding: '2px 6px',
                                            fontSize: '10px',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        KILL
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}

                    <div style={{ marginTop: '12px', borderTop: '1px solid var(--nf-border)', paddingTop: '8px' }}>
                        <h4 style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px', color: 'var(--nf-text-muted)' }}>Derniers Logs</h4>
                        <div style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--nf-text-muted)', maxHeight: '100px', overflowY: 'auto' }}>
                            {logs.map((log, i) => (
                                <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
                            ))}
                        </div>
                    </div>

                    <style jsx>{`
                    @keyframes pulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                    100% { opacity: 1; transform: scale(1); }
                    }
                `}</style>
                </div>
            )}
        </div>
    );
}
