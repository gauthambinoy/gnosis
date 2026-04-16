'use client';

import { useToastStore } from '@/stores/toastStore';
import { motion, AnimatePresence } from 'framer-motion';

const icons: Record<string, string> = {
  success: '✅',
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
};

const colors: Record<string, string> = {
  success: 'bg-green-900/90 border-green-500/50',
  error: 'bg-red-900/90 border-red-500/50',
  warning: 'bg-yellow-900/90 border-yellow-500/50',
  info: 'bg-blue-900/90 border-blue-500/50',
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            className={`${colors[toast.type]} border rounded-lg p-4 shadow-xl cursor-pointer backdrop-blur-sm`}
            onClick={() => removeToast(toast.id)}
          >
            <div className="flex items-start gap-3">
              <span className="text-lg">{icons[toast.type]}</span>
              <div>
                <p className="font-semibold text-white text-sm">{toast.title}</p>
                {toast.message && (
                  <p className="text-white/70 text-xs mt-1">{toast.message}</p>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
