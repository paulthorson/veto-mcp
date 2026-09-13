import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Theme } from '@astryxdesign/core';
import '@veto/tokens/dist/tokens.css';
import '@veto/web/dist/veto-web.css';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import './site.css';
import App from './App.tsx';
import { jobApplyTheme } from './theme.ts';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Theme theme={jobApplyTheme} mode="dark">
      <App />
    </Theme>
  </StrictMode>,
);
