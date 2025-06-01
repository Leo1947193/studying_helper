// src/components/Chat/MessageList.js
import React from 'react';
import { Card, Typography, Tooltip } from 'antd';

const { Text, Paragraph } = Typography;

function MessageList({ messages, showCitationDetail }) {
  return (
    <>
      {messages.map((msg, index) => (
        <div
          key={msg.id || index}
          style={{
            display: 'flex',
            justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: 16,
          }}
        >
          <Card
            size="small"
            style={{
              maxWidth: '70%',
              background: msg.sender === 'user' ? '#e6f7ff' : '#fff',
              borderColor: msg.sender === 'user' ? '#91d5ff' : '#d9d9d9',
              borderRadius: 8,
            }}
          >
            <Text strong>{msg.sender === 'user' ? '您' : 'AI助手'}</Text>
            <Paragraph style={{ marginBottom: 0, marginTop: 8, color: msg.isError ? 'red' : 'inherit' }}>
              {msg.content}
              {msg.sender === 'ai' && msg.citations_data && msg.citations_data.length > 0 && (
                <span style={{ marginLeft: 8 }}>
                  {msg.citations_data.map((citation, idx) => {
                    if (msg.content.includes(`[${citation.id}]`)) {
                      return (
                        <Tooltip key={idx} title={`查看文档：${citation.doc_name}，片段 ${citation.id}`}>
                          <a
                            onClick={() => showCitationDetail(citation)}
                            style={{ marginLeft: 4, fontWeight: 'bold', color: '#1890ff', cursor: 'pointer' }}
                          >
                            [{citation.id}]
                          </a>
                        </Tooltip>
                      );
                    }
                    return null;
                  })}
                </span>
              )}
            </Paragraph>
            <Text type="secondary" style={{ fontSize: 10, textAlign: msg.sender === 'user' ? 'right' : 'left', display: 'block', marginTop: 4 }}>
              {msg.timestamp}
            </Text>
          </Card>
        </div>
      ))}
    </>
  );
}

export default MessageList;