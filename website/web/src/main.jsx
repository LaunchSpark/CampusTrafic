import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import App from './App';
import { DateRangeProvider } from './state/DateRangeContext';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <DateRangeProvider>
        <App />
      </DateRangeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
