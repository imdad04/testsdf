import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, OrderListItem } from '../api';
import Header from '../components/Header';

export default function Order() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<OrderListItem | null>(null);

  useEffect(() => {
    const load = () => api.myOrders().then((list) => {
      setOrder(list.find((o) => o.id === Number(id)) || null);
    });
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [id]);

  if (!order) return <div className="p-5 text-muted">Загрузка...</div>;

  const isProcessing = order.status === 'paid' || order.status === 'in_progress';
  const isDelivered = order.status === 'delivered';
  const isPending = order.status === 'pending';
  const isRefunded = order.status === 'refunded' || order.status === 'cancelled';

  return (
    <>
      <Header title={`Заказ #${order.id}`} back />
      <div className="px-5 space-y-4">
        <div className="bg-card rounded-2xl p-5">
          <div className="text-muted text-sm">Товар</div>
          <div className="font-semibold mt-1">{order.product_name}</div>
          <div className="text-muted text-sm mt-3">Сумма</div>
          <div className="font-semibold mt-1">{Number(order.amount)} ₽</div>
        </div>

        {isPending && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4 text-sm">
            ⏳ Заказ создан. Ожидает оплаты.
          </div>
        )}
        {isProcessing && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-2xl p-4 text-sm">
            ⏳ <b>Ваш заказ обрабатывается.</b><br />
            Товар придёт в чат с ботом в течение 2 минут.
          </div>
        )}
        {isDelivered && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-2xl p-4 text-sm">
            ✅ <b>Заказ доставлен.</b><br />
            Проверьте чат с ботом — там ваш ключ/код.
            {order.delivered_payload && (
              <div className="mt-3 p-3 bg-black/40 rounded-xl font-mono text-xs break-all">
                {order.delivered_payload}
              </div>
            )}
          </div>
        )}
        {isRefunded && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 text-sm">
            ⚠️ Оформлен возврат средств.
          </div>
        )}
      </div>
    </>
  );
}
