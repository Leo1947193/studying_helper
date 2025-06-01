// src/components/Layout/AppHeader.js
import React from 'react';
import { Layout, Input, Button, Avatar, Dropdown, Space, Menu, Typography } from 'antd';
import { PlusOutlined, UserOutlined } from '@ant-design/icons';

const { Header } = Layout;
const { Title } = Typography;
const { Search } = Input;

function AppHeader({ onNewChat, onGlobalSearch }) {
  const userDropdownMenu = (
    <Menu>
      <Menu.Item key="profile">个人资料</Menu.Item>
      <Menu.Item key="logout">退出</Menu.Item>
    </Menu>
  );

  return (
    <Header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 20px',
      background: '#fff',
      borderBottom: '1px solid #f0f0f0',
      zIndex: 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0, marginRight: 30 }}>AI智能助手</Title>
        <Search
          placeholder="全局搜索"
          onSearch={onGlobalSearch}
          style={{ width: 300 }}
          allowClear
        />
      </div>
      <Space>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onNewChat}
        >
          新建对话
        </Button>
        <Dropdown
          overlay={userDropdownMenu}
          placement="bottomRight"
        >
          <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
        </Dropdown>
      </Space>
    </Header>
  );
}

export default AppHeader;