import { getInitData } from '../telegram';

const API = (import.meta as any).env?.VITE_API_URL || '';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}/api/admin${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Init-Data': getInitData(),
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  if (r.status === 204) return undefined as T;
  return r.json();
}

export type AdminStats = {
  revenue: number;
  revenue_today: number;
  orders: number;
  delivered: number;
  pending: number;
  users: number;
};

export type AdminProduct = {
  id: number;
  category_id: number;
  name: string;
  subtitle: string | null;
  description: string | null;
  price: number;
  icon_url: string | null;
  source_url: string | null;
  source_note: string | null;
  is_active: boolean;
  in_stock: boolean;
  sort_order: number;
};

export type AdminCategory = {
  id: number;
  slug: string;
  name: string;
  icon: string | null;
  sort_order: number;
  is_active: boolean;
};

export type AdminOrder = {
  id: number;
  user_id: number;
  product_name: string;
  amount: number;
  status: string;
  payment_method: string;
  created_at: string;
  paid_at: string | null;
  delivered_at: string | null;
  delivered_payload: string | null;
  operator_id: number | null;
};

export type AdminPromo = {
  id: number;
  code: string;
  discount_pct: number;
  discount_fixed: number;
  max_uses: number | null;
  used_count: number;
  expires_at: string | null;
  is_active: boolean;
};

export type AdminOperator = { id: number; name: string | null; is_active: boolean };

export const adminApi = {
  stats: () => req<AdminStats>('/stats'),

  products: () => req<AdminProduct[]>('/products'),
  createProduct: (b: Partial<AdminProduct>) =>
    req<{ id: number }>('/products', { method: 'POST', body: JSON.stringify(b) }),
  updateProduct: (id: number, b: Partial<AdminProduct>) =>
    req<{ ok: true }>(`/products/${id}`, { method: 'PUT', body: JSON.stringify(b) }),
  deleteProduct: (id: number) =>
    req<{ ok: true }>(`/products/${id}`, { method: 'DELETE' }),

  categories: () => req<AdminCategory[]>('/categories'),
  createCategory: (b: Partial<AdminCategory>) =>
    req<{ id: number }>('/categories', { method: 'POST', body: JSON.stringify(b) }),
  updateCategory: (id: number, b: Partial<AdminCategory>) =>
    req<{ ok: true }>(`/categories/${id}`, { method: 'PUT', body: JSON.stringify(b) }),
  deleteCategory: (id: number) =>
    req<{ ok: true }>(`/categories/${id}`, { method: 'DELETE' }),

  orders: (status?: string) =>
    req<AdminOrder[]>(`/orders${status ? `?status=${status}` : ''}`),
  refundOrder: (id: number) =>
    req<{ ok: true }>(`/orders/${id}/refund`, { method: 'POST' }),

  promos: () => req<AdminPromo[]>('/promos'),
  createPromo: (b: {
    code: string;
    discount_pct?: number;
    discount_fixed?: number;
    max_uses?: number | null;
    days?: number | null;
  }) => req<{ id: number }>('/promos', { method: 'POST', body: JSON.stringify(b) }),
  deletePromo: (id: number) => req<{ ok: true }>(`/promos/${id}`, { method: 'DELETE' }),

  operators: () => req<AdminOperator[]>('/operators'),
  upsertOperator: (b: AdminOperator) =>
    req<{ ok: true }>('/operators', { method: 'POST', body: JSON.stringify(b) }),
  deleteOperator: (id: number) =>
    req<{ ok: true }>(`/operators/${id}`, { method: 'DELETE' }),

  broadcast: (text: string) =>
    req<{ sent: number; failed: number }>('/broadcast', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  triggerBackup: () =>
    req<{ path: string }>('/backup', { method: 'POST' }),
};
