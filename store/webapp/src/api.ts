import { getInitData } from './telegram';

const API = (import.meta as any).env?.VITE_API_URL || '';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Init-Data': getInitData(),
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) {
    const text = await r.text();
    let msg = text;
    try {
      const j = JSON.parse(text);
      if (typeof j.detail === 'string') msg = j.detail;
      else if (j.detail) msg = JSON.stringify(j.detail);
    } catch {}
    throw new Error(msg);
  }
  return r.json();
}

export type Category = { id: number; slug: string; name: string; icon: string | null };
export type Product = {
  id: number;
  category_id: number;
  name: string;
  subtitle: string | null;
  description: string | null;
  price: string;
  icon_url: string | null;
  in_stock: boolean;
};
export type Catalog = { categories: Category[]; products: Product[] };
export type Me = {
  id: number;
  username: string | null;
  first_name: string | null;
  balance: string;
  cashback: string;
  is_admin: boolean;
};
export type OrderListItem = {
  id: number;
  status: string;
  amount: string;
  product_name: string;
  created_at: string;
  delivered_payload: string | null;
};
export type OrderCreated = {
  id: number;
  status: string;
  amount: string;
  payment_url: string | null;
  payment_method: string;
  created_at: string;
};

export type PromoCheck = {
  code: string;
  discount_pct: number;
  discount_fixed: string;
  discount: string;
  amount: string;
  base: string;
};

export const api = {
  catalog: () => req<Catalog>('/api/catalog'),
  me: () => req<Me>('/api/me'),
  myOrders: () => req<OrderListItem[]>('/api/orders'),
  createOrder: (body: {
    product_id: number;
    quantity: number;
    payment_method: 'platega' | 'cryptobot';
    promo_code?: string;
  }) =>
    req<OrderCreated>('/api/orders', {
      method: 'POST',
      body: JSON.stringify({
        ...body,
        init_data: getInitData(),
      }),
    }),
  checkPromo: (body: { code: string; product_id: number; quantity: number }) =>
    req<PromoCheck>('/api/promos/check', {
      method: 'POST',
      body: JSON.stringify({
        ...body,
        init_data: getInitData(),
      }),
    }),
};
