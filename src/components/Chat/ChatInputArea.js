// src/components/Chat/ChatInputArea.js
import React from 'react';
import { Input, Button } from 'antd';
import { SendOutlined } from '@ant-design/icons';

const { TextArea } = Input;

function ChatInputArea({ chatInput, setChatInput, handleSendMessage, sendingMessage }) {
  return (
    <div style={{ padding: '16px 24px', borderTop: '1px solid #e0e0e0', background: '#fff' }}>
      <TextArea
        value={chatInput}
        onChange={(e) => setChatInput(e.target.value)}
        placeholder="Ask EduMind..."
        autoSize={{ minRows: 2, maxRows: 6 }}
        onPressEnter={(e) => {
          if (e.shiftKey) {
            // 不做任何操作，让默认行为处理换行
          } else {
            e.preventDefault(); // 阻止默认的Enter换行
            handleSendMessage();
          }
        }}
        style={{ marginBottom: 10 }}
        disabled={sendingMessage}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSendMessage}
        disabled={chatInput.trim() === '' || sendingMessage}
        loading={sendingMessage}
      >
        发送
      </Button>
    </div>
  );
}

export default ChatInputArea;