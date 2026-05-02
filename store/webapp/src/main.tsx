import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData: string;
        initDataUnsafe: any;
        themeParams: any;
        colorScheme: 'light' | 'dark';
        BackButton: { show: () => void; hide: () => void; onClick: (cb: () => void) => void };
        MainButton: { show: () => void; hide: () => void; setText: (t: string) => void; onClick: (cb: () => void) => void };
        HapticFeedback: { impactOccurred: (s: string) => void; notificationOccurred: (s: string) => void };
        openTelegramLink: (url: string) => void;
        openLink: (url: string) => void;
        close: () => void;
      };
    };
  }
}

window.Telegram?.WebApp?.ready();
window.Telegram?.WebApp?.expand();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
