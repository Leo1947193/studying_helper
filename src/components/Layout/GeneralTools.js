// src/components/Layout/GeneralTools.js
import React from 'react';
import { Button, Space } from 'antd';
import { RobotOutlined } from '@ant-design/icons';

function GeneralTools({ setIsTemplatesModalVisible }) {
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Button
        block
        icon={<RobotOutlined />}
        onClick={() => setIsTemplatesModalVisible(true)}
      >
        答题方法与模板
      </Button>
      {/* 这里可以添加其他通用工具按钮 */}
    </Space>
  );
}

export default GeneralTools;