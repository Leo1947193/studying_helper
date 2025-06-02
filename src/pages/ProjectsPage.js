// src/pages/ProjectsPage.js
import React from 'react';
import { Layout, Typography } from 'antd';

const { Content } = Layout;
const { Title } = Typography;

function ProjectsPage() {
  return (
    <Content style={{ padding: '20px', minHeight: 'calc(100vh - 64px)' }}>
      <Title level={2}>项目管理</Title>
      <p>在这里管理你的所有项目。</p>
      {/* 项目的实际内容 */}
    </Content>
  );
}

export default ProjectsPage;