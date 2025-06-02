// src/pages/DashboardPage.js
import React from 'react';
import { Layout, Typography } from 'antd';

const { Content } = Layout;
const { Title } = Typography;

function DashboardPage() {
  return (
    <Content style={{ padding: '20px', minHeight: 'calc(100vh - 64px)' }}>
      <Title level={2}>仪表盘</Title>
      <p>这里是你的项目仪表盘，展示关键数据和概览。</p>
      {/* 仪表盘的实际内容 */}
    </Content>
  );
}

export default DashboardPage;