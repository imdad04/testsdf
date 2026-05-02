export const tg = () => window.Telegram?.WebApp;

export function getInitData(): string {
  return tg()?.initData || '';
}

export function haptic(kind: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'light') {
  const h = tg()?.HapticFeedback;
  if (!h) return;
  if (['success', 'error', 'warning'].includes(kind)) {
    h.notificationOccurred(kind);
  } else {
    h.impactOccurred(kind);
  }
}

export function openExternal(url: string) {
  if (tg()?.openLink) tg()!.openLink(url);
  else window.open(url, '_blank');
}
