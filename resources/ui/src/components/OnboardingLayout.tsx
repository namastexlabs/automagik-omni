import { ReactNode } from 'react';
import { Sparkles } from 'lucide-react';

interface OnboardingLayoutProps {
  children: ReactNode;
  currentStep: number;
  totalSteps: number;
  title: string;
}

export default function OnboardingLayout({ children, currentStep, totalSteps, title }: OnboardingLayoutProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated gradient background (matching Login.tsx) */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4xIj48cGF0aCBkPSJNMzYgMzRjMC0yIDItNCAyLTRzMiAyIDIgNHYxMGMwIDItMiA0LTIgNHMtMi0yLTItNHYtMTB6Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-20"></div>
      </div>

      {/* Floating orbs for depth */}
      <div className="absolute top-20 left-20 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse"></div>
      <div className="absolute bottom-20 right-20 w-72 h-72 bg-cyan-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse"></div>
      <div className="absolute top-40 right-40 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse"></div>

      {/* Content container */}
      <div className="w-full max-w-2xl relative z-10">
        {/* Header with logo and title */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="relative">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center shadow-lg">
                <Sparkles className="h-8 w-8 text-white" />
              </div>
            </div>
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">{title}</h1>

          {/* Progress indicator */}
          <div className="flex items-center justify-center gap-2 mt-6">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div
                key={i}
                className={`h-2 transition-all duration-300 rounded-full ${
                  i < currentStep ? 'bg-white w-12' : 'bg-white/30 w-8'
                }`}
              />
            ))}
          </div>
          <p className="text-white/80 text-sm mt-2">
            Step {currentStep} of {totalSteps}
          </p>
        </div>

        {/* Content card */}
        <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl">{children}</div>
      </div>
    </div>
  );
}
