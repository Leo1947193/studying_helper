// src/components/Chat/ChatSider.js
import React from 'react';
import { Layout, Divider, Empty, Spin, Typography } from 'antd';
import FileUploadForm from '../Chat/FileUploadForm'; 
import FilesPanel from '../Chat/FilesPanel'; 
import ChatHistoryPanel from '../Chat/ChatHistoryPanel'; 

const { Sider } = Layout;
const { Title } = Typography;

function ChatSider({
  uploadFileType,
  setUploadFileType,
  handleUpload,
  files,
  loadingFiles,
  relatedFilesMeta,
  setRelatedFileIds,
  setRelatedFilesMeta,
  setChatInput,
  handlePreview,
  chatHistory,
  loadingChatHistory,
  selectedChatId,
  setSelectedChatId,
  notification
}) {

  return (
    <Sider
      width={280}
      style={{
        background: '#fff',
        borderRight: '1px solid #f0f0f0',
        overflowY: 'auto',
        minHeight: 0,
        // 这里添加 padding-top 来使内容整体下移
        // 假设 ChatMainContent 的 padding-top 是 20px，并且标题自身有一定高度，
        // 你可能需要调整这个值来精确对齐
        paddingTop: 20, // 初始值，你可以根据实际渲染效果微调
      }}
    >
      <FileUploadForm
        uploadFileType={uploadFileType}
        setUploadFileType={setUploadFileType}
        handleUpload={handleUpload}
      />
      {/* 调整 Divider 的 margin，使其更紧凑，或者根据需要保留 */}
      <Divider style={{ margin: '0 0 16px 0' }} />

      <div style={{ padding: '0 16px 16px' }}> {/* 保持这个div的padding，避免内容贴边 */}
        <ChatHistoryPanel
          chatHistory={chatHistory}
          loadingChatHistory={loadingChatHistory}
          selectedChatId={selectedChatId}
          setSelectedChatId={setSelectedChatId}
        />

        <Divider style={{ margin: '16px 0' }} />

        <FilesPanel
          files={files}
          loadingFiles={loadingFiles}
          relatedFilesMeta={relatedFilesMeta}
          setRelatedFileIds={setRelatedFileIds}
          setRelatedFilesMeta={setRelatedFilesMeta}
          setChatInput={setChatInput}
          setActivePane={() => {}}
          handlePreview={handlePreview}
          notification={notification}
        />
      </div>
    </Sider>
  );
}

export default ChatSider;