// src/components/Chat/ChatMainContent.js
import React, { useRef, useEffect } from 'react';
import { Spin, Empty } from 'antd';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInputArea from './ChatInputArea';

function ChatMainContent({
  currentChatTitle,
  handleExportChat,
  relatedFilesMeta,
  setRelatedFileIds,
  setRelatedFilesMeta,
  notification,
  loadingMessages,
  messages,
  showCitationDetail,
  chatInput,
  setChatInput,
  handleSendMessage,
  sendingMessage,
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={{
      flex: 1,
      background: '#f9f9f9',
      borderRight: '1px solid #e0e0e0',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      <ChatHeader
        currentChatTitle={currentChatTitle}
        handleExportChat={handleExportChat}
        relatedFilesMeta={relatedFilesMeta}
        setRelatedFileIds={setRelatedFileIds}
        setRelatedFilesMeta={setRelatedFilesMeta}
        notification={notification}
      />

      <div style={{ flex: 1, padding: '24px', overflowY: 'auto', minHeight: 0 }}>
        <Spin spinning={loadingMessages}>
          {messages.length === 0 && !loadingMessages ? (
            <Empty
              description="开始提问或上传文件"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: '50px' }}
            />
          ) : (
            <MessageList messages={messages} showCitationDetail={showCitationDetail} />
          )}
          <div ref={messagesEndRef} />
        </Spin>
      </div>

      <ChatInputArea
        chatInput={chatInput}
        setChatInput={setChatInput}
        handleSendMessage={handleSendMessage}
        sendingMessage={sendingMessage}
      />
    </div>
  );
}

export default ChatMainContent;