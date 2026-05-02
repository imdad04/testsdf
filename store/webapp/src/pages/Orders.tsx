import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, OrderListItem } from '../api';
import Header from '../components/Header';

const STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: 'Ожидает оплаты', color: 'text-yellow-400' },
  paid: { label: 'Обрабатывается', color: 'text-blue-400' },
  in_progress: { label: 'Обрабатывается', color: 'text-blue-400' },
  delivered: { label: 'Доставлен', color: 'text-green-400' },
  cancelled: { label: 'Отменён', color: 'text-muted' },
  refunded: { label: 'Возврат', color: 'text-red-400' },
};

export default function Orders() {
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);

  useEffect(() => {
    api.myOrders().then(setOrders).catch(() => setOrders([]));
  }, []);

  if (!orders) return <div className="p-5 text-muted">Загрузка...</div>;

  return (
    <>
      <Header title="Мои заказы" back />
      <div className="px-5 space-y-3">
        {orders.length === 0 ? (
          <div className="text-muted text-sm py-10 text-center">Пока нет заказов</div>
        ) : (
          orders.map((o) => {
            const s = STATUS[o.status] || { label: o.status, color: 'text-muted' };
            return (
              <Link
                key={o.id}
                to={`/orders/${o.id}`}
                className="block bg-card rounded-2xl p-4 border border-white/5"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold">#{o.id} · {o.product_name}</div>
                  <div className="text-sm font-semibold">{Number(o.amount)} ₽</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className={s.color}>{s.label}</span>
                  <span className="text-muted">{new Date(o.created_at).toLocaleString()}</span>
                </div>
              </Link>
            );
          })
        )}
      </div>
    </>
  );
}
