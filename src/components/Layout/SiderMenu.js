// src/components/Layout/SiderMenu.js
import React from 'react';
import { Menu } from 'antd';

function SiderMenu({ activePane, setActivePane, siderMenuItems }) {
  return (
    <Menu
      mode="inline"
      selectedKeys={[activePane]}
      onClick={e => setActivePane(e.key)}
      style={{ borderRight: 0, paddingBottom: 16 }}
    >
      {siderMenuItems.map(item => (
        <Menu.Item key={item.key} icon={item.icon}>
          {item.label}
        </Menu.Item>
      ))}
    </Menu>
  );
}

export default SiderMenu;