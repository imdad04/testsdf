import { Link } from 'react-router-dom';
import type { Product } from '../api';

export default function ProductCard({ p }: { p: Product }) {
  return (
    <Link
      to={`/product/${p.id}`}
      className="bg-card rounded-2xl p-3 flex flex-col gap-2 border border-white/5 active:scale-[0.98] transition"
    >
      <div className="aspect-square w-full bg-cardSoft rounded-xl flex items-center justify-center overflow-hidden">
        {p.icon_url ? (
          <img src={p.icon_url} className="w-2/3 h-2/3 object-contain" alt="" />
        ) : (
          <span className="text-3xl">📦</span>
        )}
      </div>
      <div>
        <div className="text-sm font-semibold leading-tight">{p.name}</div>
        {p.subtitle && <div className="text-xs text-muted">{p.subtitle}</div>}
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className="font-semibold">{Number(p.price)} ₽</span>
      </div>
      <button className="bg-accent text-white text-sm font-semibold py-2 rounded-xl">
        Купить
      </button>
    </Link>
  );
}
