// src/components/Layout/FilesPanel.js
import React from 'react';
import { List, Button, Tooltip, Empty, Spin, Typography } from 'antd';
import { PlusOutlined, SendOutlined, SearchOutlined, FileOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

function FilesPanel({
  files,
  loadingFiles,
  relatedFilesMeta,
  setRelatedFileIds,
  setRelatedFilesMeta,
  setChatInput,
  setActivePane,
  handlePreview,
  notification
}) {
  return (
    <Spin spinning={loadingFiles}>
      <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>我的文件</Title>
      <List
        dataSource={files}
        renderItem={file => (
          <List.Item
            key={file.id}
            actions={[
              <Tooltip title="添加到当前对话">
                <Button
                  type="text"
                  icon={<PlusOutlined />}
                  size="small"
                  onClick={() => {
                    if (!relatedFilesMeta.some(f => f.id === file.id)) {
                      setRelatedFileIds(prev => [...prev, file.id]);
                      setRelatedFilesMeta(prev => [...prev, file]);
                      notification.success({ message: `文件 '${file.name}' 已添加到当前对话。` });
                    } else {
                      notification.info({ message: `文件 '${file.name}' 已在此对话中。` });
                    }
                  }}
                />
              </Tooltip>,
              <Tooltip title="将文件内容发送到对话">
                <Button type="text" icon={<SendOutlined />} size="small" onClick={() => {
                  setChatInput(prev => `${prev} 请分析文件：${file.name} `);
                  setActivePane('chat');
                }} />
              </Tooltip>,
              <Tooltip title="查看文件">
                <Button type="text" icon={<SearchOutlined />} size="small" onClick={() => handlePreview(file)} />
              </Tooltip>
            ]}
            style={{ padding: '8px 0' }}
          >
            <List.Item.Meta
              avatar={<FileOutlined />}
              title={<a onClick={() => console.log('点击文件:', file.name)}>{file.name}</a>}
              description={<Text type="secondary">{file.size} - {file.uploadDate} (类型: {file.file_type_tag || '未知'})</Text>}
            />
          </List.Item>
        )}
      />
      {!files.length && !loadingFiles && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文件" style={{ marginTop: 50 }} />}
    </Spin>
  );
}

export default FilesPanel;