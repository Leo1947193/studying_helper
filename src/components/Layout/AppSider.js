// src/components/Layout/AppSider.js
import React from 'react';
import { Layout, Divider, Empty, Spin, Typography } from 'antd';
import SiderMenu from './SiderMenu';
import FileUploadForm from './FileUploadForm';
import FilesPanel from './FilesPanel';
import ChatHistoryPanel from './ChatHistoryPanel';

const { Sider } = Layout;
const { Title } = Typography;

function AppSider({
  activePane,
  setActivePane,
  siderMenuItems,
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
  notification // Ant Design 的 notification 实例
}) {
  return (
    <Sider
      width={280}
      style={{
        background: '#fff',
        borderRight: '1px solid #f0f0f0',
        overflowY: 'auto',
        minHeight: 0,
      }}
    >
      <SiderMenu
        activePane={activePane}
        setActivePane={setActivePane}
        siderMenuItems={siderMenuItems}
      />

      <Divider style={{ margin: '0 0 16px 0' }} />

      <FileUploadForm
        uploadFileType={uploadFileType}
        setUploadFileType={setUploadFileType}
        handleUpload={handleUpload}
      />

      <Divider style={{ margin: '0 0 16px 0' }} />

      <div style={{ padding: '0 16px 16px' }}>
        {activePane === 'files' && (
          <FilesPanel
            files={files}
            loadingFiles={loadingFiles}
            relatedFilesMeta={relatedFilesMeta}
            setRelatedFileIds={setRelatedFileIds}
            setRelatedFilesMeta={setRelatedFilesMeta}
            setChatInput={setChatInput}
            setActivePane={setActivePane}
            handlePreview={handlePreview}
            notification={notification}
          />
        )}
        {activePane === 'chat' && (
          <ChatHistoryPanel
            chatHistory={chatHistory}
            loadingChatHistory={loadingChatHistory}
            selectedChatId={selectedChatId}
            setSelectedChatId={setSelectedChatId}
          />
        )}
        {activePane === 'settings' && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="在右侧管理应用设置" style={{ marginTop: 50 }} />
        )}
      </div>
    </Sider>
  );
}

export default AppSider;