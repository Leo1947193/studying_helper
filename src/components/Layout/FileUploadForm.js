// src/components/Layout/FileUploadForm.js
import React from 'react';
import { Form, Select, Upload, Button, Typography } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

// 注意：BACKEND_BASE_URL 需要从外部传递或通过 Context 获取
const BACKEND_BASE_URL = 'http://localhost:5000/api'; // 这里重复一下，实际应用中可以统一管理

function FileUploadForm({ uploadFileType, setUploadFileType, handleUpload }) {
  return (
    <div style={{ padding: '0 16px 16px' }}>
      <Title level={5} style={{ marginTop: 0, marginBottom: 12, textAlign: 'center' }}>上传新文件</Title>
      <Form layout="vertical">
        <Form.Item label="文件类型">
          <Select
            value={uploadFileType}
            onChange={setUploadFileType}
            style={{ width: '100%' }}
          >
            <Option value="textbook">课本</Option>
            <Option value="past_paper">往年卷</Option>
            <Option value="answer_key">答案</Option>
            <Option value="other">其他</Option>
          </Select>
        </Form.Item>
        <Form.Item>
          <Upload
            name="file"
            action={`${BACKEND_BASE_URL}/upload`}
            data={{ file_type_tag: uploadFileType }}
            onChange={handleUpload}
            showUploadList={false}
            multiple={false}
          >
            <Button icon={<UploadOutlined />} block>选择并上传文件</Button>
          </Upload>
        </Form.Item>
      </Form>
      <Text type="secondary" style={{ fontSize: '12px', marginTop: 0, display: 'block', textAlign: 'center' }}>支持PDF, DOCX, TXT等格式</Text>
    </div>
  );
}

export default FileUploadForm;