import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, Catalog, Product as ProductT, PromoCheck } from '../api';
import Header from '../components/Header';
import { haptic, openExternal } from '../telegram';

export default function Product() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [data, setData] = useState<ProductT | null>(null);
  const [qty, setQty] = useState(1);
  const [promo, setPromo] = useState('');
  const [appliedPromo, setAppliedPromo] = useState<PromoCheck | null>(null);
  const [promoChecking, setPromoChecking] = useState(false);
  const [promoError, setPromoError] = useState<string | null>(null);
  const [method, setMethod] = useState<'platega' | 'cryptobot'>('platega');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.catalog().then((c: Catalog) => {
      setData(c.products.find((p) => p.id === Number(id)) || null);
    });
  }, [id]);

  // если меняется кол-во или код — сбрасываем применённый промо
  useEffect(() => {
    setAppliedPromo(null);
    setPromoError(null);
  }, [qty, promo]);

  const checkPromo = async () => {
    if (!data || !promo.trim()) return;
    setPromoChecking(true);
    setPromoError(null);
    try {
      const res = await api.checkPromo({
        code: promo.trim(),
        product_id: data.id,
        quantity: qty,
      });
      setAppliedPromo(res);
      haptic('success');
    } catch (e: any) {
      setAppliedPromo(null);
      setPromoError(e.message || String(e));
      haptic('error');
    } finally {
      setPromoChecking(false);
    }
  };

  const buy = async () => {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const order = await api.createOrder({
        product_id: data.id,
        quantity: qty,
        payment_method: method,
        promo_code: appliedPromo?.code || undefined,
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

        <div>
          <div className="flex gap-2">
            <input
              value={promo}
              onChange={(e) => setPromo(e.target.value.toUpperCase())}
              disabled={!!appliedPromo}
              placeholder="🎟 Промокод"
              className="flex-1 bg-card border border-white/5 rounded-2xl px-4 py-3 text-sm placeholder:text-muted focus:outline-none focus:border-accent uppercase disabled:opacity-50"
            />
            {appliedPromo ? (
              <button
                onClick={() => {
                  setAppliedPromo(null);
                  setPromo('');
                  setPromoError(null);
                }}
                className="px-4 bg-cardSoft rounded-2xl text-sm font-semibold"
              >
                ✕
              </button>
            ) : (
              <button
                onClick={checkPromo}
                disabled={promoChecking || !promo.trim()}
                className="px-4 bg-accent rounded-2xl text-sm font-semibold disabled:opacity-50"
              >
                {promoChecking ? '...' : 'Применить'}
              </button>
            )}
          </div>
          {appliedPromo && (
            <div className="mt-2 bg-green-500/10 border border-green-500/30 rounded-2xl px-4 py-2 text-sm">
              ✅ <b>{appliedPromo.code}</b> применён · скидка{' '}
              {appliedPromo.discount_pct
                ? `${appliedPromo.discount_pct}%`
                : `${appliedPromo.discount_fixed}₽`}{' '}
              <span className="text-muted">(−{Number(appliedPromo.discount).toFixed(2)}₽)</span>
            </div>
          )}
          {promoError && (
            <div className="mt-2 text-red-400 text-sm">{promoError}</div>
          )}
        </div>

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
          {busy ? (
            'Создаю заказ...'
          ) : appliedPromo ? (
            <>
              Оплатить{' '}
              <span className="line-through opacity-60 text-sm">
                {Number(appliedPromo.base).toFixed(0)}₽
              </span>{' '}
              {Number(appliedPromo.amount).toFixed(0)}₽
            </>
          ) : (
            `Оплатить ${Number(data.price) * qty} ₽`
          )}
        </button>
      </div>
    </>
  );
}
