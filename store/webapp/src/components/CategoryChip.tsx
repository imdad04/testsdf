import type { Category } from '../api';

export default function CategoryChip({
  cat,
  active,
  onClick,
}: {
  cat: Category | { id: number | null; name: string; icon: string };
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center justify-center gap-2 rounded-2xl py-4 px-2 border transition shrink-0 w-24 ${
        active
          ? 'bg-accent border-accent shadow-glow'
          : 'bg-card border-white/5'
      }`}
    >
      <span className="text-2xl">{cat.icon || '✨'}</span>
      <span className="text-xs font-medium">{cat.name}</span>
    </button>
  );
}
