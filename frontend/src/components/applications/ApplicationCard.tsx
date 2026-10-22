import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Application } from '@/types/application';

interface ApplicationCardProps {
  application: Application;
  onClick: (app: Application) => void;
}

export default function ApplicationCard({ application, onClick }: ApplicationCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: application.id.toString(), data: { type: 'Application', application } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onClick(application)}
      className={`application-card cursor-pointer p-4 ${
        isDragging ? 'ring-2 ring-blue-500 shadow-lg z-50' : ''
      }`}
    >
      <h4 className="font-semibold text-gray-900 dark:text-white truncate" title={application.position}>
        {application.position}
      </h4>
      <p className="text-sm text-gray-600 dark:text-gray-400 truncate" title={application.company}>
        {application.company}
      </p>
      {application.applied_at && (
        <p className="text-xs text-gray-400 mt-2">
          {new Date(application.applied_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
