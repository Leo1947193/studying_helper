// src/components/Layout/ChatHistoryPanel.js
import React from 'react';
import { List, Spin, Empty, Typography } from 'antd';
import { MessageOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

function ChatHistoryPanel({ chatHistory, loadingChatHistory, selectedChatId, setSelectedChatId }) {
  return (
    <Spin spinning={loadingChatHistory}>
      <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>对话历史</Title>
      <List
        dataSource={chatHistory}
        renderItem={chat => (
          <List.Item
            key={chat.id}
            onClick={() => setSelectedChatId(chat.id)}
            style={{
              padding: '8px 12px',
              cursor: 'pointer',
              borderRadius: 4,
              background: selectedChatId === chat.id ? '#e6f7ff' : 'transparent',
              transition: 'background-color 0.2s',
              marginBottom: 4,
            }}
          >
            <List.Item.Meta
              avatar={<MessageOutlined />}
              title={<Text strong>{chat.title}</Text>}
              description={<Text type="secondary" style={{ fontSize: 12 }}>上次活跃: {chat.lastActive}</Text>}
            />
          </List.Item>
        )}
      />
      {!chatHistory.length && !loadingChatHistory && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对话历史" style={{ marginTop: 50 }} />}
    </Spin>
  );
}

export default ChatHistoryPanel;