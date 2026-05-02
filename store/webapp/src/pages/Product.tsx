import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, Catalog, Product as ProductT } from '../api';
import Header from '../components/Header';
import { haptic, openExternal } from '../telegram';

export default function Product() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [data, setData] = useState<ProductT | null>(null);
  const [qty, setQty] = useState(1);
  const [promo, setPromo] = useState('');
  const [method, setMethod] = useState<'platega' | 'cryptobot'>('platega');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.catalog().then((c: Catalog) => {
      setData(c.products.find((p) => p.id === Number(id)) || null);
    });
  }, [id]);

  const buy = async () => {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const order = await api.createOrder({
        product_id: data.id,
        quantity: qty,
        payment_method: method,
        promo_code: promo || undefined,
      });
      haptic('success');
      if (order.payment_url) {
        openExternal(order.payment_url);
        nav(`/orders/${order.id}`);
      } else {
        setError('Платёжка не вернула ссылку');
      }
    } catch (e: any) {
      haptic('error');
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <div className="p-5 text-muted">Загрузка...</div>;

  return (
    <>
      <Header title={data.name} subtitle={data.subtitle || undefined} back />
      <div className="px-5 space-y-5">
        <div className="bg-card rounded-2xl p-6 flex items-center justify-center aspect-square">
          {data.icon_url ? (
            <img src={data.icon_url} className="w-1/2 h-1/2 object-contain" alt="" />
          ) : (
            <span className="text-7xl">📦</span>
          )}
        </div>

        {data.description && (
          <div className="text-sm text-muted whitespace-pre-line">{data.description}</div>
        )}

        <div className="bg-card rounded-2xl p-4 flex items-center justify-between">
          <div className="text-sm text-muted">Цена за шт.</div>
          <div className="text-xl font-bold">{Number(data.price)} ₽</div>
        </div>

        <div className="bg-card rounded-2xl p-4 flex items-center justify-between">
          <div className="text-sm text-muted">Количество</div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setQty((q) => Math.max(1, q - 1))}
              className="w-9 h-9 rounded-full bg-cardSoft text-xl"
            >
              −
            </button>
            <div className="w-6 text-center font-semibold">{qty}</div>
            <button
              onClick={() => setQty((q) => Math.min(10, q + 1))}
              className="w-9 h-9 rounded-full bg-cardSoft text-xl"
            >
              +
            </button>
          </div>
        </div>

        <input
          value={promo}
          onChange={(e) => setPromo(e.target.value.toUpperCase())}
          placeholder="🎟 Промокод (если есть)"
          className="w-full bg-card border border-white/5 rounded-2xl px-4 py-3 text-sm placeholder:text-muted focus:outline-none focus:border-accent uppercase"
        />

        <div>
          <div className="text-sm text-muted mb-2">Способ оплаты</div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setMethod('platega')}
              className={`py-3 rounded-2xl text-sm font-semibold border ${
                method === 'platega' ? 'bg-accent border-accent' : 'bg-card border-white/5'
              }`}
            >
              💳 Карта (Platega)
            </button>
            <button
              onClick={() => setMethod('cryptobot')}
              className={`py-3 rounded-2xl text-sm font-semibold border ${
                method === 'cryptobot' ? 'bg-accent border-accent' : 'bg-card border-white/5'
              }`}
            >
              🪙 CryptoBot
            </button>
          </div>
        </div>

        {error && <div className="text-red-400 text-sm">{error}</div>}

        <button
          disabled={busy}
          onClick={buy}
          className="w-full bg-accent disabled:opacity-50 text-white font-bold py-4 rounded-2xl shadow-glow"
        >
          {busy ? 'Создаю заказ...' : `Оплатить ${Number(data.price) * qty} ₽`}
        </button>
      </div>
    </>
  );
}
