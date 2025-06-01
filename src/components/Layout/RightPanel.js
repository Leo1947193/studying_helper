// src/components/Layout/RightPanel.js
import React from 'react';
import { Divider, Empty, Typography } from 'antd';
import GeneralTools from './GeneralTools';
import ChatSettingsForm from './ChatSettingsForm';

const { Title } = Typography;

function RightPanel({
  activePane,
  setIsTemplatesModalVisible,
  modelSettings,
  setModelSettings,
}) {
  return (
    <div style={{
      flex: '0 0 350px',
      background: '#fff',
      padding: '24px',
      overflowY: 'auto',
      borderLeft: '1px solid #e0e0e0',
      minHeight: 0,
    }}>
      <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>通用工具</Title>
      <GeneralTools
        setIsTemplatesModalVisible={setIsTemplatesModalVisible}
      />
      <Divider />

      {activePane === 'chat' && (
        <ChatSettingsForm
          modelSettings={modelSettings}
          setModelSettings={setModelSettings}
        />
      )}

      {(activePane === 'files' || activePane === 'settings') && (
        <>
          <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>辅助信息</Title>
          <Empty description="请在左侧选择对应功能菜单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </>
      )}
    </div>
  );
}

export default RightPanel;