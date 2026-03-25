import React, { useState } from "react";
import { Book, Download, ChevronRight, ChevronDown, ChevronUp, Calendar, CheckSquare } from "lucide-react";
import MiniCalendar from "./MiniCalendar";
import TaskList from "./TaskList";

interface CourseCardProps {
  id: string;
  name: string;
  filesCount: number;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onSync: (id: string) => void;
  onOpenChat: (id: string) => void;
}

export default function CourseCard({ id, name, filesCount, isExpanded = false, onToggleExpand, onSync, onOpenChat }: CourseCardProps) {
  return (
    <div 
      className={`nf-card nf-card--glow nf-course-card ${isExpanded ? 'nf-course-card--expanded' : ''}`} 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '20px',
        gridColumn: isExpanded ? '1 / -1' : 'auto',
        transition: 'all 0.3s ease-in-out',
        width: '100%',
        padding: '24px'
      }}

    >
      <div className="nf-course-card__header" style={{ display: 'flex', gap: '20px', alignItems: 'center', position: 'relative' }}>
        <div className="nf-course-card__icon" style={{ 
          width: '56px', 
          height: '56px', 
          borderRadius: '14px', 
          background: 'var(--nf-accent-glow)', 
          color: 'var(--nf-accent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          border: '1px solid var(--nf-accent-dim)'
        }}>
          <Book size={28} />
        </div>
        <div className="nf-course-card__info" style={{ flex: 1 }}>
          <h3 className="nf-course-card__title" style={{ fontSize: '18px', fontWeight: 600, marginBottom: '6px', color: 'var(--nf-text)' }}>
            {name}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ 
              display: 'inline-block', 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              background: filesCount > 0 ? 'var(--nf-success)' : 'var(--nf-warning)' 
            }} />
            <p className="nf-course-card__subtitle" style={{ fontSize: '13px', color: 'var(--nf-text-secondary)', margin: 0 }}>
              {filesCount} document{filesCount > 1 ? 's' : ''} synchronisé{filesCount > 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <button 
          className="nf-btn nf-btn--ghost nf-btn--icon" 
          onClick={onToggleExpand}
          style={{ width: '36px', height: '36px', borderRadius: '10px' }}
          title={isExpanded ? "Réduire" : "Voir les détails"}
        >

          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
      </div>
      
      {isExpanded && (
        <div className="nf-course-card__details nf-animate-in" style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
          gap: '24px',
          padding: '20px',
          background: 'rgba(0,0,0,0.1)',
          borderRadius: '12px',
          border: '1px solid var(--nf-border-dim)'
        }}>
          <div className="nf-course-details__section">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <Calendar size={18} color="var(--nf-accent)" />
              <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Agenda du cours</h4>
            </div>
            <MiniCalendar courseName={name} noWrapper={true} />
          </div>
          <div className="nf-course-details__section">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <CheckSquare size={18} color="var(--nf-success)" />
              <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Tâches à faire</h4>
            </div>
            <TaskList courseName={name} courseId={id} compact noWrapper={true} />
          </div>
        </div>
      )}
      
      <div className="nf-course-card__actions" style={{ display: 'flex', gap: '12px', marginTop: 'auto' }}>
        <button 
          className="nf-btn nf-btn--ghost"
          style={{ padding: '0 24px', height: '40px', fontSize: '14px' }}
          onClick={() => onSync(id)}
        >
          <Download size={16} />
          Synchroniser
        </button>
        <button 
          className="nf-btn nf-btn--primary"
          style={{ flex: 1, justifyContent: 'center', height: '40px', fontSize: '15px' }}
          onClick={() => onOpenChat(id)}
        >
          Discuter avec le cours
          <ChevronRight size={18} />
        </button>
      </div>


    </div>
  );
}
