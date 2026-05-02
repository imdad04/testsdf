import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Catalog, Me } from '../api';
import CategoryChip from '../components/CategoryChip';
import Header from '../components/Header';
import ProductCard from '../components/ProductCard';

const ALL_CHIP = { id: null, name: 'Все', icon: '⚡' } as const;

export default function Home() {
  const [data, setData] = useState<Catalog | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [activeCat, setActiveCat] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.catalog().then(setData).catch((e) => setError(String(e)));
    api.me().then(setMe).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.products.filter((p) => {
      if (activeCat !== null && p.category_id !== activeCat) return false;
      if (q && !(p.name + ' ' + (p.subtitle || '')).toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, activeCat, search]);

  if (error) {
    return (
      <div className="p-5 text-red-400">
        Не удалось загрузить каталог: {error}
        <div className="text-muted mt-2 text-sm">Открой WebApp из бота — без initData API не пустит.</div>
      </div>
    );
  }
  if (!data) return <div className="p-5 text-muted">Загрузка...</div>;

  return (
    <>
      <Header title="Маркетплейс" subtitle="Выбери свой товар" />

      {me?.is_admin && (
        <div className="px-5 mb-2">
          <Link
            to="/admin"
            className="block bg-gradient-to-r from-accent to-accentSoft rounded-2xl px-4 py-3 text-sm font-semibold shadow-glow"
          >
            ⚙️ Открыть админку
          </Link>
        </div>
      )}

      <div className="px-5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="🔍 Поиск товаров..."
          className="w-full bg-card border border-white/5 rounded-2xl px-4 py-3 text-sm placeholder:text-muted focus:outline-none focus:border-accent"
        />
      </div>

      <div className="px-5 mt-5">
        <h2 className="text-sm text-muted mb-3">Популярные категории</h2>
        <div className="flex gap-3 overflow-x-auto -mx-5 px-5">
          <CategoryChip
            cat={ALL_CHIP}
            active={activeCat === null}
            onClick={() => setActiveCat(null)}
          />
          {data.categories.map((c) => (
            <CategoryChip
              key={c.id}
              cat={c}
              active={activeCat === c.id}
              onClick={() => setActiveCat(c.id)}
            />
          ))}
        </div>
      </div>

      <div className="px-5 mt-6">
        <h2 className="text-sm text-muted mb-3">Популярные товары</h2>
        {filtered.length === 0 ? (
          <div className="text-muted text-sm py-10 text-center">Ничего не найдено</div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {filtered.map((p) => (
              <ProductCard key={p.id} p={p} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
