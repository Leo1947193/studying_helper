// src/components/Layout/AppHeader.js
import React, { useState, useEffect } from 'react'; // 导入 useEffect
import { Layout, Input, Button, Avatar, Dropdown, Space, Menu, Typography, List } from 'antd';
import { UserOutlined, BellOutlined, SearchOutlined } from '@ant-design/icons'; // 导入 SearchOutlined
import logo from '../../assets/images/logo.png'; // 假设你有一个logo图片

const { Header } = Layout;
const { Title, Text } = Typography;
const { Search } = Input;

function AppHeader({ onGlobalSearch, onMenuItemClick }) {
  const [isSearchCollapsed, setIsSearchCollapsed] = useState(false); // 控制搜索框是否收缩为按钮

  // 监听窗口大小变化，决定是否收缩搜索框
  useEffect(() => {
    const handleResize = () => {
      // 这里的阈值需要根据实际内容和布局进行调整
      // 经验值：当窗口宽度小于约 992px 或 768px 时考虑收缩搜索框
      setIsSearchCollapsed(window.innerWidth < 900); // 你可以调整这个数值
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // 组件挂载时执行一次
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const userDropdownMenu = (
    <Menu>
      <Menu.Item key="profile">个人资料</Menu.Item>
      <Menu.Item key="logout">退出</Menu.Item>
    </Menu>
  );

  // 通知数据
  const notifications = [
    {
      id: '1',
      title: '欢迎使用EduMind！',
      description: '来自EduMind团队',
      time: '刚刚',
    },
    {
      id: '2',
      title: '新功能上线通知',
      description: '项目看板增加了新的视图模式。',
      time: '1小时前',
    },
  ];

  // 通知下拉菜单的内容
  const notificationOverlay = (
    <div style={{
      width: 300,
      maxHeight: 400,
      overflowY: 'auto',
      backgroundColor: '#fff',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
      borderRadius: 4,
      padding: '10px 0',
    }}>
      <List
        itemLayout="horizontal"
        dataSource={notifications}
        renderItem={item => (
          <List.Item style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <List.Item.Meta
              title={<Text strong>{item.title}</Text>}
              description={
                <>
                  <Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Text>
                  <div style={{ fontSize: 11, color: '#999' }}>{item.time}</div>
                </>
              }
            />
          </List.Item>
        )}
      />
      <div style={{ textAlign: 'center', padding: '10px', borderTop: '1px solid #f0f0f0' }}>
        <Button type="link">查看所有通知</Button>
      </div>
    </div>
  );

  // 导航菜单项 - 顺序：项目、智能助手、仪表盘
  const navMenuItems = [
    {
      key: 'projects',
      label: '项目',
    },
    {
      key: 'intelligentAssistant',
      label: '智能助手',
    },
    {
      key: 'dashboard',
      label: '仪表盘',
    },
  ];

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
      {/* 左侧区域：Logo 和 EduMind 标题 (固定宽度) */}
      <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}> {/* flexShrink:0 防止 Logo/Title 收缩 */}
        <img src={logo} alt="EduMind Logo" style={{ height: '48px', marginRight: '10px' }} />
        <Title level={3} style={{ margin: 0, marginRight: 30, whiteSpace: 'nowrap' }}>EduMind</Title>
      </div>

      {/* 中间弹性区域：导航菜单 (当空间不足时收缩) */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', minWidth: 0 }}> {/* minWidth:0 允许Flex项收缩 */}
        <Menu
          mode="horizontal"
          items={navMenuItems}
          onClick={onMenuItemClick}
          defaultSelectedKeys={['intelligentAssistant']}
          style={{ borderBottom: 'none', backgroundColor: 'transparent', minWidth: 0, flex: 1, justifyContent: 'center' }}
          overflowedIndicator={<span>...</span>} // 菜单项收缩为省略号
        />
      </div>

      {/* 右侧区域：全局搜索、通知、用户头像 */}
      {/* 这个 div 应该具有优先级更高的收缩能力，因此 Search 组件放在其内部并控制其宽度 */}
      <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, marginLeft: 20 }}> {/* 添加marginLeft与导航分隔 */}
        {isSearchCollapsed ? (
          // 当搜索框收缩时显示一个按钮
          <Button
            type="text"
            icon={<SearchOutlined />}
            onClick={() => { /* 点击后可以展开搜索框或弹出搜索Modal */ console.log('搜索按钮被点击'); }}
            style={{ marginRight: 8 }} // 保持与通知图标的间距
          />
        ) : (
          // 否则显示完整的搜索框
          <Search
            placeholder="全局搜索"
            onSearch={onGlobalSearch}
            style={{ width: 300, minWidth: 150, marginRight: 20 }} // 搜索框优先收缩宽度
            allowClear
          />
        )}

        <Space size="middle">
          <Dropdown
            overlay={notificationOverlay}
            placement="bottomRight"
            trigger={['hover']}
          >
            <Button type="text" icon={<BellOutlined />} />
          </Dropdown>

          <Dropdown
            overlay={userDropdownMenu}
            placement="bottomRight"
          >
            <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
          </Dropdown>
        </Space>
      </div>
    </Header>
  );
}

export default AppHeader;