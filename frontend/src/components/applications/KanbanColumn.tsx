import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Application, ApplicationStatus } from '@/types/application';
import ApplicationCard from './ApplicationCard';

interface KanbanColumnProps {
  id: ApplicationStatus;
  title: string;
  applications: Application[];
  onApplicationClick: (app: Application) => void;
}

export default function KanbanColumn({ id, title, applications, onApplicationClick }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id,
    data: {
      type: 'Column',
      status: id,
    },
  });

  return (
    <div className="kanban-column flex min-w-0 flex-col p-4">
      <h3 className="mb-4 flex items-center justify-between font-semibold text-white">
        <span>{title}</span>
        <span className="kanban-count">
          {applications.length}
        </span>
      </h3>
      
      <div 
        ref={setNodeRef} 
        className={`flex-1 overflow-y-auto space-y-3 p-1 rounded transition-colors min-h-[150px] ${
          isOver ? 'kanban-is-over' : ''
        }`}
      >
        <SortableContext 
          items={applications.map(app => app.id.toString())}
          strategy={verticalListSortingStrategy}
        >
          {applications.map((app) => (
            <ApplicationCard 
              key={app.id} 
              application={app} 
              onClick={onApplicationClick} 
            />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}
