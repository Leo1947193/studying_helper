// src/components/Layout/ChatHistoryPanel.js
import React from 'react';
import { List, Spin, Empty, Typography, Button, notification } from 'antd'; // 导入 Button 和 notification
import { MessageOutlined, PlusOutlined } from '@ant-design/icons'; // 导入 PlusOutlined

const { Title, Text } = Typography;

function ChatHistoryPanel({ chatHistory, loadingChatHistory, selectedChatId, setSelectedChatId }) {

  // 新建对话逻辑
  const handleNewChat = () => {
    setSelectedChatId(null); // 清空当前选中的对话
    // TODO: 在这里可能还需要清空父组件（IntelligentAssistantPage）中的 messages 状态
    // TODO: 并且可能需要触发父组件的 fetchChatHistory 来刷新历史列表，以便显示新对话
    // 由于ChatHistoryPanel不直接管理messages，这里发出通知，并提示父组件处理
    notification.info({
      message: '开始新的对话！',
      description: '已清除当前对话状态，请开始输入您的新问题。',
      duration: 2
    });
  };

  return (
    <Spin spinning={loadingChatHistory}>
      {/* 对话历史标题和新建对话按钮容器 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Title level={5} style={{ margin: 0 }}>对话历史</Title>
        <Button
          type="primary" // 设置按钮类型为主要按钮
          icon={<PlusOutlined />} // 添加加号图标
          size="small" // 设置按钮大小为小
          onClick={handleNewChat} // 绑定新建对话的逻辑
        >
          新建对话
        </Button>
      </div>
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