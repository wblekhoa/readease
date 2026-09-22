import React from 'react';
import { hydrateRoot } from 'react-dom/client';
import { App } from './src/App.jsx';
import './style.css';

hydrateRoot(document.getElementById('root'), React.createElement(App, { locale: document.documentElement.lang }));
