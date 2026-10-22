'use client';
import { useState } from 'react';
import { 
  DndContext, 
  closestCorners, 
  KeyboardSensor, 
  PointerSensor, 
  useSensor, 
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { Application, ApplicationStatus, ApplicationUpdate } from '@/types/application';
import KanbanColumn from './KanbanColumn';
import ApplicationCard from './ApplicationCard';
import ApplicationModal from './ApplicationModal';

interface KanbanBoardProps {
  applications: Application[];
  onStatusChange: (id: number, newStatus: ApplicationStatus) => Promise<void>;
  onUpdateApplication: (id: number, data: ApplicationUpdate) => Promise<void>;
  onGenerateChecklist: (id: number) => Promise<any>;
}

const COLUMNS: { id: ApplicationStatus; title: string }[] = [
  { id: 'saved', title: 'Kaydedilenler' },
  { id: 'applied', title: 'Başvurulanlar' },
  { id: 'hr_interview', title: 'İK Görüşmesi' },
  { id: 'technical_interview', title: 'Teknik Görüşme' },
  { id: 'offer', title: 'Teklif Alındı' },
  { id: 'rejected', title: 'Reddedildi' },
];

export default function KanbanBoard({ 
  applications, 
  onStatusChange, 
  onUpdateApplication,
  onGenerateChecklist
}: KanbanBoardProps) {
  const [activeApplication, setActiveApplication] = useState<Application | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    if (active.data.current?.type === 'Application') {
      setActiveApplication(active.data.current.application);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveApplication(null);
    const { active, over } = event;
    
    if (!over) return;

    const applicationId = parseInt(active.id.toString());
    const overId = over.id.toString();

    // Sütun üzerine bırakıldıysa (sütun id'si bir statü ise)
    const newStatus = COLUMNS.find(c => c.id === overId)?.id;
    
    if (newStatus && active.data.current?.application.status !== newStatus) {
      await onStatusChange(applicationId, newStatus);
      return;
    }

    // Başka bir kartın üzerine bırakıldıysa (aynı sütunda veya farklı sütunda)
    if (over.data.current?.type === 'Application') {
      const targetStatus = over.data.current.application.status;
      if (active.data.current?.application.status !== targetStatus) {
        await onStatusChange(applicationId, targetStatus);
      }
    }
  };

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-grid">
          {COLUMNS.map(col => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              title={col.title}
              applications={applications.filter(app => app.status === col.id)}
              onApplicationClick={setSelectedApplication}
            />
          ))}
        </div>
        
        <DragOverlay>
          {activeApplication ? (
            <ApplicationCard application={activeApplication} onClick={() => {}} />
          ) : null}
        </DragOverlay>
      </DndContext>

      {selectedApplication && (
        <ApplicationModal
          application={selectedApplication}
          onClose={() => setSelectedApplication(null)}
          onSave={async (id, data) => {
            await onUpdateApplication(id, data);
            setSelectedApplication(null);
          }}
          onGenerateChecklist={onGenerateChecklist}
        />
      )}
    </>
  );
}
