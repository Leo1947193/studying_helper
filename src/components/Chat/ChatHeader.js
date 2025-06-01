// src/components/Chat/ChatHeader.js
import React from 'react';
import { Typography, Button, Tooltip, Tag, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

function ChatHeader({ currentChatTitle, handleExportChat, relatedFilesMeta, setRelatedFileIds, setRelatedFilesMeta, notification }) {
  return (
    <div style={{ padding: '16px 24px', borderBottom: '1px solid #e0e0e0', background: '#fff' }}>
      <Title level={4} style={{ margin: 0 }}>
        {currentChatTitle}
        <Tooltip title="导出当前对话为DOCX文件">
          <Button
            icon={<DownloadOutlined />}
            type="text"
            style={{ marginLeft: 10 }}
            onClick={handleExportChat}
          />
        </Tooltip>
      </Title>
      {relatedFilesMeta.length > 0 && (
        <div style={{ marginTop: 10, marginBottom: -8 }}>
          <Text strong>本次对话依据：</Text>
          <Space wrap size={[0, 8]}>
            {relatedFilesMeta.map(file => (
              <Tag
                key={file.id}
                closable
                onClose={(e) => {
                  e.preventDefault();
                  setRelatedFileIds(prev => prev.filter(id => id !== file.id));
                  setRelatedFilesMeta(prev => prev.filter(f => f.id !== file.id));
                  notification.info({ message: `文件 '${file.name}' 已从当前对话移除。` });
                }}
              >
                {file.name}
              </Tag>
            ))}
          </Space>
        </div>
      )}
    </div>
  );
}

export default ChatHeader;