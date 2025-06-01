// src/components/Layout/ChatSettingsForm.js
import React from 'react';
import { Form, Select, Slider, Switch, Typography } from 'antd';

const { Title, Text } = Typography;
const { Option } = Select;

function ChatSettingsForm({ modelSettings, setModelSettings }) {
  return (
    <>
      <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>对话设置</Title>
      <Form layout="vertical">
        <Form.Item label="选择模型">
          <Select
            value={modelSettings.model}
            onChange={(value) => setModelSettings({ ...modelSettings, model: value })}
          >
            <Option value="deepseek-chat">DeepSeek Chat</Option>
            <Option value="deepseek-coder">DeepSeek Coder</Option>
          </Select>
        </Form.Item>

        <Form.Item label="温度 (Temperature)" tooltip="控制生成文本的随机性，值越高越有创意，越低越保守。">
          <Slider
            min={0}
            max={1}
            step={0.1}
            value={modelSettings.temperature}
            onChange={(value) => setModelSettings({ ...modelSettings, temperature: value })}
          />
          <Text type="secondary">{modelSettings.temperature.toFixed(1)}</Text>
        </Form.Item>

        <Form.Item label="模型人格">
          <Select
            value={modelSettings.persona}
            onChange={(value) => setModelSettings({ ...modelSettings, persona: value })}
          >
            <Option value="default">默认</Option>
            <Option value="professional">专业</Option>
            <Option value="creative">创意</Option>
            <Option value="friendly">友好</Option>
          </Select>
        </Form.Item>

        <Form.Item label="启用流式输出" valuePropName="checked">
          <Switch
            checked={modelSettings.enableStreaming}
            onChange={(checked) => setModelSettings({ ...modelSettings, enableStreaming: checked })}
          />
        </Form.Item>
      </Form>
    </>
  );
}

export default ChatSettingsForm;