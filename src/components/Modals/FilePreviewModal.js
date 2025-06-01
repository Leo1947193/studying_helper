// src/components/Modals/FilePreviewModal.js
import React from 'react';
import { Modal, Button, Spin, Empty, Input, Typography } from 'antd';

const { Text } = Typography;

// 注意：BACKEND_BASE_URL 需要从外部传递或通过 Context 获取
const BACKEND_BASE_URL = 'http://localhost:5000/api';

function FilePreviewModal({
  isPreviewModalVisible,
  handlePreviewModalClose,
  currentPreviewFile,
  previewFileContent,
  loadingPreviewContent,
}) {
  return (
    <Modal
      title={currentPreviewFile ? `预览: ${currentPreviewFile.name}` : '文件预览'}
      visible={isPreviewModalVisible}
      onCancel={handlePreviewModalClose}
      footer={[
        currentPreviewFile && previewFileContent === 'UNSUPPORTED_PREVIEW' && (
          <Button
            key="download"
            type="primary"
            href={`${BACKEND_BASE_URL.replace('/api', '')}/uploads/${currentPreviewFile.name}`}
            target="_blank"
            download={currentPreviewFile.name}
          >
            下载文件
          </Button>
        ),
        <Button key="close" onClick={handlePreviewModalClose}>关闭</Button>,
      ]}
      width={800}
      bodyStyle={{ minHeight: '400px', maxHeight: '70vh', overflowY: 'auto' }}
    >
      <Spin spinning={loadingPreviewContent}>
        {!currentPreviewFile ? (
          <Empty description="选择一个文件进行预览" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div>
            {loadingPreviewContent ? (
              <Empty description="加载中..." image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : previewFileContent === 'UNSUPPORTED_PREVIEW' ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_FILE}
                description={
                  <Text>
                    该文件类型（<Text strong>.{currentPreviewFile.type || '未知'}</Text>）暂不支持在线预览。
                    <br />
                    您可以点击下方的"下载文件"按钮。
                  </Text>
                }
              />
            ) : previewFileContent === 'ERROR_LOADING_PREVIEW' ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_DEFAULT}
                description={
                  <Text type="danger">
                    加载文件内容失败。请检查后端服务和文件是否存在于服务器。
                  </Text>
                }
              />
            ) : currentPreviewFile.type.startsWith('image') ? (
              <img src={previewFileContent} alt="文件预览" style={{ maxWidth: '100%', display: 'block', margin: '0 auto' }} />
            ) : currentPreviewFile.type === 'pdf' ? (
              <iframe
                src={previewFileContent}
                title="PDF 文件预览"
                width="100%"
                height="500px"
                frameBorder="0"
                style={{ border: '1px solid #e0e0e0', minHeight: '400px' }}
              />
            ) : (
              <Input.TextArea
                value={previewFileContent}
                readOnly
                autoSize={{ minRows: 15, maxRows: 30 }}
                style={{ width: '100%', border: 'none', background: '#f8f8f8' }}
              />
            )}
          </div>
        )}
      </Spin>
    </Modal>
  );
}

export default FilePreviewModal;