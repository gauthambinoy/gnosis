'use client';

import { useEffect } from 'react';

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Gnosis] Unhandled error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] p-6">
      <div className="max-w-md w-full bg-[#111] border border-white/10 rounded-2xl p-8 text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
        <p className="text-gray-400 text-sm mb-6">
          {error.message || 'An unexpected error occurred. Please try again.'}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="px-5 py-2 bg-[#C8FF00] text-black font-medium rounded-lg hover:bg-[#C8FF00]/90 transition-colors"
          >
            Try again
          </button>
          <button
            onClick={() => (window.location.href = '/')}
            className="px-5 py-2 bg-white/5 text-white/70 font-medium rounded-lg hover:bg-white/10 transition-colors border border-white/10"
          >
            Go home
          </button>
        </div>
        {error.digest && (
          <p className="text-gray-600 text-xs mt-4 font-mono">Error ID: {error.digest}</p>
        )}
      </div>
    </div>
  );
}
