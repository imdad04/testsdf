import { useEffect, useState } from 'react';
import Header from '../components/Header';
import { api, Me } from '../api';
import {
  adminApi,
  AdminCategory,
  AdminOperator,
  AdminOrder,
  AdminProduct,
  AdminPromo,
  AdminStats,
} from '../api/admin';
import { haptic } from '../telegram';

type Tab = 'dash' | 'products' | 'cats' | 'orders' | 'promos' | 'ops' | 'tools';

const TABS: { id: Tab; icon: string; label: string }[] = [
  { id: 'dash', icon: '📊', label: 'Главная' },
  { id: 'products', icon: '🛒', label: 'Товары' },
  { id: 'cats', icon: '🗂', label: 'Категории' },
  { id: 'orders', icon: '📦', label: 'Заказы' },
  { id: 'promos', icon: '🎟', label: 'Промо' },
  { id: 'ops', icon: '👥', label: 'Операторы' },
  { id: 'tools', icon: '⚙️', label: 'Инструменты' },
];

export default function Admin() {
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>('dash');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me().then(setMe).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="p-5 text-red-400">{error}</div>;
  if (!me) return <div className="p-5 text-muted">Загрузка...</div>;
  if (!me.is_admin) return <div className="p-5 text-red-400">⛔ Доступ только для админов.</div>;

  return (
    <>
      <Header title="⚙️ Админка" subtitle="BUTA STORE" back />
      <div className="px-3 mb-3 overflow-x-auto -mx-3 px-3">
        <div className="flex gap-2 pb-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                haptic('light');
                setTab(t.id);
              }}
              className={`shrink-0 px-3 py-2 rounded-xl text-sm font-medium border transition ${
                tab === t.id ? 'bg-accent border-accent' : 'bg-card border-white/5'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-3">
        {tab === 'dash' && <Dashboard />}
        {tab === 'products' && <ProductsTab />}
        {tab === 'cats' && <CategoriesTab />}
        {tab === 'orders' && <OrdersTab />}
        {tab === 'promos' && <PromosTab />}
        {tab === 'ops' && <OperatorsTab />}
        {tab === 'tools' && <ToolsTab />}
      </div>
    </>
  );
}

// ============== Dashboard ==============
function Dashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  useEffect(() => {
    adminApi.stats().then(setStats).catch(() => {});
  }, []);
  if (!stats) return <div className="text-muted">Загрузка...</div>;

  const Card = ({ icon, label, value }: { icon: string; label: string; value: string | number }) => (
    <div className="bg-card rounded-2xl p-4 border border-white/5">
      <div className="text-xs text-muted">
        {icon} {label}
      </div>
      <div className="text-xl font-bold mt-1">{value}</div>
    </div>
  );

  return (
    <div className="grid grid-cols-2 gap-3">
      <Card icon="💰" label="Выручка всего" value={`${stats.revenue.toFixed(0)} ₽`} />
      <Card icon="📅" label="За сегодня" value={`${stats.revenue_today.toFixed(0)} ₽`} />
      <Card icon="📦" label="Всего заказов" value={stats.orders} />
      <Card icon="✅" label="Доставлено" value={stats.delivered} />
      <Card icon="⏳" label="В работе" value={stats.pending} />
      <Card icon="👥" label="Юзеров" value={stats.users} />
    </div>
  );
}

// ============== Products ==============
function ProductsTab() {
  const [items, setItems] = useState<AdminProduct[] | null>(null);
  const [cats, setCats] = useState<AdminCategory[]>([]);
  const [editing, setEditing] = useState<AdminProduct | null>(null);
  const [creating, setCreating] = useState(false);

  const load = () => {
    adminApi.products().then(setItems);
    adminApi.categories().then(setCats);
  };
  useEffect(() => { load(); }, []);

  if (!items) return <div className="text-muted">Загрузка...</div>;

  if (creating || editing) {
    return (
      <ProductForm
        cats={cats}
        initial={editing}
        onCancel={() => {
          setEditing(null);
          setCreating(false);
        }}
        onSaved={() => {
          setEditing(null);
          setCreating(false);
          load();
        }}
      />
    );
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => setCreating(true)}
        className="w-full bg-accent rounded-2xl py-3 font-semibold"
      >
        ➕ Добавить товар
      </button>
      {items.map((p) => (
        <div key={p.id} className="bg-card rounded-2xl p-3 border border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-cardSoft rounded-xl flex items-center justify-center overflow-hidden shrink-0">
              {p.icon_url ? (
                <img src={p.icon_url} className="w-3/4 h-3/4 object-contain" />
              ) : (
                <span className="text-xl">📦</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                {!p.is_active && <span className="text-xs text-red-400">⛔ скрыт</span>}
                {!p.in_stock && <span className="text-xs text-yellow-400">нет в наличии</span>}
                <div className="font-semibold truncate">#{p.id} {p.name}</div>
              </div>
              <div className="text-xs text-muted">{p.subtitle || '—'} · {p.price}₽</div>
              {p.source_url && <div className="text-xs text-blue-400 truncate">🔗 {p.source_url}</div>}
            </div>
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => setEditing(p)}
              className="flex-1 bg-cardSoft rounded-xl py-2 text-sm"
            >
              ✏️ Изменить
            </button>
            <button
              onClick={async () => {
                if (!confirm('Скрыть товар из каталога?')) return;
                await adminApi.deleteProduct(p.id);
                load();
              }}
              className="px-3 bg-red-500/20 text-red-400 rounded-xl py-2 text-sm"
            >
              🗑
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function ProductForm({
  cats,
  initial,
  onCancel,
  onSaved,
}: {
  cats: AdminCategory[];
  initial: AdminProduct | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [f, setF] = useState({
    category_id: initial?.category_id || cats[0]?.id || 1,
    name: initial?.name || '',
    subtitle: initial?.subtitle || '',
    description: initial?.description || '',
    price: initial?.price?.toString() || '',
    icon_url: initial?.icon_url || '',
    source_url: initial?.source_url || '',
    source_note: initial?.source_note || '',
    is_active: initial?.is_active ?? true,
    in_stock: initial?.in_stock ?? true,
    sort_order: initial?.sort_order || 0,
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      const body = { ...f, price: parseFloat(f.price) || 0 } as any;
      if (initial) await adminApi.updateProduct(initial.id, body);
      else await adminApi.createProduct(body);
      haptic('success');
      onSaved();
    } catch (e: any) {
      haptic('error');
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const Field = ({
    label,
    children,
  }: {
    label: string;
    children: React.ReactNode;
  }) => (
    <div className="space-y-1">
      <div className="text-xs text-muted">{label}</div>
      {children}
    </div>
  );

  const inputCls =
    'w-full bg-card border border-white/5 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-accent';

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-lg">{initial ? `✏️ Товар #${initial.id}` : '➕ Новый товар'}</h3>
      <Field label="Название">
        <input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
      </Field>
      <Field label="Категория">
        <select
          className={inputCls}
          value={f.category_id}
          onChange={(e) => setF({ ...f, category_id: Number(e.target.value) })}
        >
          {cats.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon} {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Подзаголовок (например, '1 месяц')">
        <input
          className={inputCls}
          value={f.subtitle}
          onChange={(e) => setF({ ...f, subtitle: e.target.value })}
        />
      </Field>
      <Field label="Цена ₽">
        <input
          type="number"
          inputMode="decimal"
          className={inputCls}
          value={f.price}
          onChange={(e) => setF({ ...f, price: e.target.value })}
        />
      </Field>
      <Field label="URL иконки (https://...)">
        <input
          className={inputCls}
          value={f.icon_url}
          onChange={(e) => setF({ ...f, icon_url: e.target.value })}
        />
      </Field>
      <Field label="Описание (видит клиент)">
        <textarea
          className={inputCls + ' min-h-[80px]'}
          value={f.description}
          onChange={(e) => setF({ ...f, description: e.target.value })}
        />
      </Field>
      <div className="border-t border-white/10 pt-3 mt-3">
        <div className="text-xs text-yellow-400 mb-2">🔒 Только для оператора, клиент не видит:</div>
        <Field label="Ссылка где купить (источник)">
          <input
            className={inputCls}
            value={f.source_url}
            onChange={(e) => setF({ ...f, source_url: e.target.value })}
          />
        </Field>
        <div className="mt-2" />
        <Field label="Заметка для оператора">
          <textarea
            className={inputCls + ' min-h-[60px]'}
            value={f.source_note}
            onChange={(e) => setF({ ...f, source_note: e.target.value })}
          />
        </Field>
      </div>
      <div className="flex gap-3 pt-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={f.is_active}
            onChange={(e) => setF({ ...f, is_active: e.target.checked })}
          />
          активен
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={f.in_stock}
            onChange={(e) => setF({ ...f, in_stock: e.target.checked })}
          />
          в наличии
        </label>
      </div>
      {err && <div className="text-red-400 text-sm">{err}</div>}
      <div className="flex gap-2 pt-2">
        <button onClick={onCancel} className="flex-1 bg-cardSoft rounded-xl py-3">
          Отмена
        </button>
        <button
          onClick={save}
          disabled={busy || !f.name || !f.price}
          className="flex-1 bg-accent rounded-xl py-3 font-semibold disabled:opacity-50"
        >
          {busy ? 'Сохраняю...' : 'Сохранить'}
        </button>
      </div>
    </div>
  );
}

// ============== Categories ==============
function CategoriesTab() {
  const [items, setItems] = useState<AdminCategory[] | null>(null);
  const [form, setForm] = useState({ slug: '', name: '', icon: '', sort_order: 0 });

  const load = () => adminApi.categories().then(setItems);
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.slug || !form.name) return;
    await adminApi.createCategory(form);
    setForm({ slug: '', name: '', icon: '', sort_order: 0 });
    load();
  };

  if (!items) return <div className="text-muted">Загрузка...</div>;

  return (
    <div className="space-y-3">
      <div className="bg-card rounded-2xl p-3 border border-white/5 space-y-2">
        <div className="text-sm font-semibold">➕ Добавить категорию</div>
        <input
          className="w-full bg-cardSoft border border-white/5 rounded-xl px-3 py-2 text-sm"
          placeholder="slug (например games)"
          value={form.slug}
          onChange={(e) => setForm({ ...form, slug: e.target.value })}
        />
        <input
          className="w-full bg-cardSoft border border-white/5 rounded-xl px-3 py-2 text-sm"
          placeholder="Имя (например Игры)"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          className="w-full bg-cardSoft border border-white/5 rounded-xl px-3 py-2 text-sm"
          placeholder="Иконка (эмодзи)"
          value={form.icon}
          onChange={(e) => setForm({ ...form, icon: e.target.value })}
        />
        <button onClick={create} className="w-full bg-accent rounded-xl py-2 text-sm font-semibold">
          Создать
        </button>
      </div>
      {items.map((c) => (
        <div
          key={c.id}
          className="bg-card rounded-2xl p-3 border border-white/5 flex items-center justify-between"
        >
          <div>
            <div className="font-semibold">
              {c.icon} {c.name} {!c.is_active && <span className="text-xs text-red-400">⛔</span>}
            </div>
            <div className="text-xs text-muted">slug: {c.slug}</div>
          </div>
          <button
            onClick={async () => {
              if (!confirm('Скрыть категорию?')) return;
              await adminApi.deleteCategory(c.id);
              load();
            }}
            className="bg-red-500/20 text-red-400 rounded-xl px-3 py-2 text-sm"
          >
            🗑
          </button>
        </div>
      ))}
    </div>
  );
}

// ============== Orders ==============
function OrdersTab() {
  const [items, setItems] = useState<AdminOrder[] | null>(null);
  const [filter, setFilter] = useState<string>('');
  const load = () => adminApi.orders(filter || undefined).then(setItems);
  useEffect(() => { load(); }, [filter]);

  const STATUS_LABEL: Record<string, { color: string; label: string }> = {
    pending: { color: 'text-yellow-400', label: '⏳ Ожидает оплаты' },
    paid: { color: 'text-blue-400', label: '💰 Оплачен' },
    in_progress: { color: 'text-blue-400', label: '🔧 В работе' },
    delivered: { color: 'text-green-400', label: '✅ Доставлен' },
    refunded: { color: 'text-red-400', label: '↩️ Возврат' },
    cancelled: { color: 'text-muted', label: '❌ Отменён' },
  };

  if (!items) return <div className="text-muted">Загрузка...</div>;

  return (
    <div className="space-y-3">
      <div className="flex gap-2 overflow-x-auto -mx-3 px-3">
        {[
          { v: '', l: 'Все' },
          { v: 'paid', l: '💰 Оплаченные' },
          { v: 'in_progress', l: '🔧 В работе' },
          { v: 'delivered', l: '✅ Доставлены' },
          { v: 'refunded', l: '↩️ Возврат' },
        ].map((f) => (
          <button
            key={f.v}
            onClick={() => setFilter(f.v)}
            className={`shrink-0 px-3 py-1.5 rounded-xl text-xs ${
              filter === f.v ? 'bg-accent' : 'bg-card border border-white/5'
            }`}
          >
            {f.l}
          </button>
        ))}
      </div>
      {items.length === 0 && <div className="text-muted text-center py-10">Пока нет заказов</div>}
      {items.map((o) => {
        const s = STATUS_LABEL[o.status] || { color: 'text-muted', label: o.status };
        return (
          <div key={o.id} className="bg-card rounded-2xl p-3 border border-white/5">
            <div className="flex items-center justify-between">
              <div className="font-semibold">#{o.id} · {o.product_name}</div>
              <div className="font-semibold">{o.amount}₽</div>
            </div>
            <div className={`text-xs ${s.color} mt-1`}>{s.label}</div>
            <div className="text-xs text-muted mt-1">
              user <code>{o.user_id}</code> · {o.payment_method} ·{' '}
              {new Date(o.created_at).toLocaleString()}
            </div>
            {o.delivered_payload && (
              <div className="mt-2 p-2 bg-black/40 rounded-xl font-mono text-xs break-all">
                {o.delivered_payload}
              </div>
            )}
            {(o.status === 'paid' || o.status === 'in_progress') && (
              <button
                onClick={async () => {
                  if (!confirm('Оформить возврат?')) return;
                  await adminApi.refundOrder(o.id);
                  load();
                }}
                className="mt-2 bg-red-500/20 text-red-400 rounded-xl py-2 px-3 text-sm w-full"
              >
                ↩️ Возврат
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============== Promos ==============
function PromosTab() {
  const [items, setItems] = useState<AdminPromo[] | null>(null);
  const [form, setForm] = useState({ code: '', discount_pct: '', discount_fixed: '', max_uses: '', days: '' });
  const load = () => adminApi.promos().then(setItems);
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.code) return;
    try {
      await adminApi.createPromo({
        code: form.code,
        discount_pct: parseInt(form.discount_pct) || 0,
        discount_fixed: parseFloat(form.discount_fixed) || 0,
        max_uses: form.max_uses ? parseInt(form.max_uses) : null,
        days: form.days ? parseInt(form.days) : null,
      });
      setForm({ code: '', discount_pct: '', discount_fixed: '', max_uses: '', days: '' });
      load();
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (!items) return <div className="text-muted">Загрузка...</div>;

  return (
    <div className="space-y-3">
      <div className="bg-card rounded-2xl p-3 border border-white/5 space-y-2">
        <div className="text-sm font-semibold">➕ Создать промокод</div>
        <input
          className="w-full bg-cardSoft rounded-xl px-3 py-2 text-sm"
          placeholder="КОД (например NEWBIE)"
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            className="bg-cardSoft rounded-xl px-3 py-2 text-sm"
            placeholder="скидка %"
            type="number"
            value={form.discount_pct}
            onChange={(e) => setForm({ ...form, discount_pct: e.target.value })}
          />
          <input
            className="bg-cardSoft rounded-xl px-3 py-2 text-sm"
            placeholder="или ₽"
            type="number"
            value={form.discount_fixed}
            onChange={(e) => setForm({ ...form, discount_fixed: e.target.value })}
          />
          <input
            className="bg-cardSoft rounded-xl px-3 py-2 text-sm"
            placeholder="лимит активаций"
            type="number"
            value={form.max_uses}
            onChange={(e) => setForm({ ...form, max_uses: e.target.value })}
          />
          <input
            className="bg-cardSoft rounded-xl px-3 py-2 text-sm"
            placeholder="срок (дней)"
            type="number"
            value={form.days}
            onChange={(e) => setForm({ ...form, days: e.target.value })}
          />
        </div>
        <button onClick={create} className="w-full bg-accent rounded-xl py-2 text-sm font-semibold">
          Создать
        </button>
      </div>
      {items.map((p) => (
        <div key={p.id} className="bg-card rounded-2xl p-3 border border-white/5">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono font-semibold">{p.code} {!p.is_active && <span className="text-xs text-red-400">⛔</span>}</div>
              <div className="text-xs text-muted">
                -{p.discount_pct ? `${p.discount_pct}%` : `${p.discount_fixed}₽`} · {p.used_count}/
                {p.max_uses || '∞'} {p.expires_at && `· до ${new Date(p.expires_at).toLocaleDateString()}`}
              </div>
            </div>
            <button
              onClick={async () => {
                await adminApi.deletePromo(p.id);
                load();
              }}
              className="bg-red-500/20 text-red-400 rounded-xl px-3 py-2 text-sm"
            >
              🗑
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============== Operators ==============
function OperatorsTab() {
  const [items, setItems] = useState<AdminOperator[] | null>(null);
  const [form, setForm] = useState({ id: '', name: '' });
  const load = () => adminApi.operators().then(setItems);
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.id) return;
    await adminApi.upsertOperator({ id: parseInt(form.id), name: form.name || null, is_active: true });
    setForm({ id: '', name: '' });
    load();
  };

  if (!items) return <div className="text-muted">Загрузка...</div>;

  return (
    <div className="space-y-3">
      <div className="bg-card rounded-2xl p-3 border border-white/5 space-y-2">
        <div className="text-sm font-semibold">➕ Добавить оператора</div>
        <input
          className="w-full bg-cardSoft rounded-xl px-3 py-2 text-sm"
          placeholder="Telegram ID"
          type="number"
          value={form.id}
          onChange={(e) => setForm({ ...form, id: e.target.value })}
        />
        <input
          className="w-full bg-cardSoft rounded-xl px-3 py-2 text-sm"
          placeholder="Имя (необязательно)"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <button onClick={add} className="w-full bg-accent rounded-xl py-2 text-sm font-semibold">
          Сохранить
        </button>
      </div>
      {items.length === 0 && (
        <div className="text-muted text-center py-6 text-sm">
          Главный оператор берётся из <code>OPERATOR_CHAT_ID</code>. Здесь — дополнительные.
        </div>
      )}
      {items.map((o) => (
        <div key={o.id} className="bg-card rounded-2xl p-3 border border-white/5 flex justify-between items-center">
          <div>
            <div className="font-semibold">{o.name || `Оператор ${o.id}`}</div>
            <div className="text-xs text-muted">
              <code>{o.id}</code> {!o.is_active && '⛔'}
            </div>
          </div>
          <button
            onClick={async () => {
              await adminApi.deleteOperator(o.id);
              load();
            }}
            className="bg-red-500/20 text-red-400 rounded-xl px-3 py-2 text-sm"
          >
            🗑
          </button>
        </div>
      ))}
    </div>
  );
}

// ============== Tools ==============
function ToolsTab() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const sendBroadcast = async () => {
    if (!text.trim()) return;
    if (!confirm(`Отправить рассылку всем юзерам?\n\n${text}`)) return;
    setBusy(true);
    try {
      const r = await adminApi.broadcast(text);
      setResult(`✅ Отправлено: ${r.sent}, ❌ Ошибок: ${r.failed}`);
      setText('');
    } catch (e: any) {
      setResult(`Ошибка: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const doBackup = async () => {
    setBusy(true);
    setResult(null);
    try {
      const r = await adminApi.triggerBackup();
      setResult(`💾 Бэкап создан: ${r.path}`);
    } catch (e: any) {
      setResult(`Ошибка: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-2xl p-3 border border-white/5 space-y-2">
        <div className="text-sm font-semibold">📣 Рассылка</div>
        <textarea
          className="w-full bg-cardSoft rounded-xl px-3 py-2 text-sm min-h-[100px]"
          placeholder="Текст рассылки (HTML поддерживается)"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          onClick={sendBroadcast}
          disabled={busy || !text.trim()}
          className="w-full bg-accent rounded-xl py-2 text-sm font-semibold disabled:opacity-50"
        >
          Отправить всем
        </button>
      </div>

      <div className="bg-card rounded-2xl p-3 border border-white/5 space-y-2">
        <div className="text-sm font-semibold">💾 Бэкап БД</div>
        <div className="text-xs text-muted">
          Зашифрованный архив будет отправлен в твой приватный канал (BACKUP_CHAT_ID).
        </div>
        <button
          onClick={doBackup}
          disabled={busy}
          className="w-full bg-cardSoft rounded-xl py-2 text-sm font-semibold disabled:opacity-50"
        >
          Сделать бэкап сейчас
        </button>
      </div>

      {result && <div className="bg-card rounded-2xl p-3 border border-white/5 text-sm">{result}</div>}
    </div>
  );
}
