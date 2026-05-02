import { Link, useNavigate } from 'react-router-dom';

export default function Header({
  title,
  subtitle,
  back,
}: {
  title: string;
  subtitle?: string;
  back?: boolean;
}) {
  const nav = useNavigate();
  return (
    <div className="px-5 pt-4 pb-3 flex items-center gap-3">
      {back ? (
        <button
          onClick={() => nav(-1)}
          className="w-9 h-9 rounded-full bg-card flex items-center justify-center text-xl"
        >
          ‹
        </button>
      ) : (
        <Link
          to="/orders"
          className="w-9 h-9 rounded-full bg-card flex items-center justify-center"
          aria-label="orders"
        >
          📦
        </Link>
      )}
      <div className="flex-1">
        <h1 className="text-2xl font-bold leading-tight">{title}</h1>
        {subtitle && <p className="text-muted text-sm">{subtitle}</p>}
      </div>
    </div>
  );
}
