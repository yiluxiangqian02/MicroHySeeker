import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { FileText, Edit, Trash2, Play, Calendar } from 'lucide-react';
import { TemplateDialog } from './TemplateDialog';
import { useNavigate } from 'react-router-dom';

interface Template {
  id: string;
  name: string;
  description: string;
  steps: any[];
  tags: string[];
  created_at: string;
}

interface TemplateCardProps {
  template: Template;
  onUpdate: () => void;
}

export function TemplateCard({ template, onUpdate }: TemplateCardProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/templates/${template.id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        onUpdate();
        setIsDeleteDialogOpen(false);
      } else {
        alert(t('templates.deleteError'));
      }
    } catch (error) {
      alert(t('templates.deleteError'));
    } finally {
      setIsDeleting(false);
    }
  };

  const handleInstantiate = async () => {
    try {
      const res = await fetch(`/api/templates/${template.id}/instantiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        navigate(`/experiments/${data.experiment_id}`);
      } else {
        alert(t('templates.instantiateError'));
      }
    } catch (error) {
      alert(t('templates.instantiateError'));
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <>
      <motion.div
        variants={itemVariants}
        whileHover={{ y: -4 }}
        className="card p-6 space-y-4"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">{template.name}</h3>
              <p className="text-sm text-gray-500 flex items-center mt-1">
                <Calendar className="h-3 w-3 mr-1" />
                {new Date(template.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        <p className="text-sm text-gray-600 line-clamp-2">{template.description}</p>

        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{template.steps.length} {t('templates.steps')}</span>
        </div>

        {template.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {template.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs font-medium"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center space-x-2 pt-2 border-t border-slate-200">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleInstantiate}
            className="flex-1 flex items-center justify-center space-x-2 bg-blue-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Play className="h-4 w-4" />
            <span>{t('templates.use')}</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsEditDialogOpen(true)}
            className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg"
          >
            <Edit className="h-4 w-4 text-slate-700" />
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsDeleteDialogOpen(true)}
            className="p-2 bg-red-50 hover:bg-red-100 rounded-lg"
          >
            <Trash2 className="h-4 w-4 text-red-600" />
          </motion.button>
        </div>
      </motion.div>

      {/* Edit Dialog */}
      <TemplateDialog
        isOpen={isEditDialogOpen}
        onClose={() => setIsEditDialogOpen(false)}
        onSuccess={onUpdate}
        template={template}
      />

      {/* Delete Confirmation Dialog */}
      {isDeleteDialogOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full mx-4"
          >
            <h3 className="text-lg font-semibold mb-2">{t('templates.deleteConfirm')}</h3>
            <p className="text-gray-600 mb-6">
              {t('templates.deleteWarning', { name: template.name })}
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => setIsDeleteDialogOpen(false)}
                disabled={isDeleting}
                className="flex-1 btn-secondary"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex-1 btn-danger"
              >
                {isDeleting ? t('common.deleting') : t('common.delete')}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </>
  );
}
