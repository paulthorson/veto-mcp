import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Analytics } from '@vercel/analytics/react';
import { Theme } from '@astryxdesign/core';
import './fonts.css';
import './vendor/tokens.css';
import './vendor/veto-web.css';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import './site.css';
import App from './App.tsx';
import { vetoTheme } from './theme.ts';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Theme theme={vetoTheme} mode="dark">
      <App />
      <Analytics />
    </Theme>
  </StrictMode>,
);
