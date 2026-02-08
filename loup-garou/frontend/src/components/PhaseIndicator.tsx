import { Sun, Moon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PhaseIndicatorProps {
  phase: 'jour' | 'nuit';
  dayNumber: number;
}

const PhaseIndicator = ({ phase, dayNumber }: PhaseIndicatorProps) => {
  const isNight = phase === 'nuit';

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-black/40 rounded-full border border-amber-500/20 backdrop-blur-sm">
      <div className={cn(
        "flex items-center justify-center w-8 h-8 rounded-full shadow-inner transition-colors duration-500",
        isNight ? "bg-blue-950 text-blue-200" : "bg-amber-500 text-amber-950"
      )}>
        {isNight ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
      </div>
      
      <div className="flex flex-col">
        <span className={cn(
          "text-xs font-bold uppercase tracking-widest",
          isNight ? "text-blue-300" : "text-amber-400"
        )}>
          {isNight ? "Nuit Profonde" : "Plein Jour"}
        </span>
        <span className="text-[10px] text-amber-100/60 font-serif">
          Tour {dayNumber}
        </span>
      </div>
    </div>
  );
};

export default PhaseIndicator;