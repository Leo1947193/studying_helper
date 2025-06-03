// notebook-frontend/src/index.js

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom'; // <--- 关键修改：导入 BrowserRouter
import { App as AntdApp } from 'antd';
import './index.css';
import App from './App'; // 导入你的 App.js 组件

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter> {/* <--- 关键修改：用 BrowserRouter 包裹 AntdApp */}
      <AntdApp>
        <App />
      </AntdApp>
    </BrowserRouter>
  </React.StrictMode>
);
