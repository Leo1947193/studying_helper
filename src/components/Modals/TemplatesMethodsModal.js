// src/components/Modals/TemplatesMethodsModal.js
import React from 'react';
import { Modal, Button, Form, Select, Input, Divider, List, Tooltip, Spin, Empty, Typography, notification } from 'antd';
import { CopyOutlined, CheckOutlined } from '@ant-design/icons';

const { Option } = Select;
const { Text } = Typography;

function TemplatesMethodsModal({
  isTemplatesModalVisible,
  setIsTemplatesModalVisible,
  loadingTemplatesMethods,
  templatesMethods,
  files, // 需要文件列表来选择进行提取
  selectedFileForExtraction,
  setSelectedFileForExtraction,
  handleExtractTemplatesFromFile,
  extractionLoading,
  rewriteQuestion,
  setRewriteQuestion,
  originalAnswer,
  setOriginalAnswer,
  selectedMethodIndex,
  setSelectedMethodIndex,
  handleRewriteAnswer,
  rewriteLoading,
  rewrittenAnswer,
  copiedIndex,
  setCopiedIndex,
}) {
  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000); // 2秒后恢复
      notification.success({message: "已复制到剪贴板！"});
    }).catch(err => {
      notification.error({message: "复制失败，请手动复制！"});
      console.error('Failed to copy text: ', err);
    });
  };

  return (
    <Modal
      title="答题方法与出题模板"
      visible={isTemplatesModalVisible}
      onCancel={() => setIsTemplatesModalVisible(false)}
      footer={null}
      width={800}
      bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
    >
      <Spin spinning={loadingTemplatesMethods || extractionLoading || rewriteLoading}>
        <Divider orientation="left" style={{ margin: '16px 0' }}>从文件提取</Divider>
        <Form layout="vertical">
          <Form.Item label="选择文件">
            <Select
              placeholder="选择要分析的文件"
              value={selectedFileForExtraction}
              onChange={setSelectedFileForExtraction}
              style={{ width: '100%' }}
            >
              {files.map(file => (
                <Option key={file.id} value={file.id}>
                  {file.name} (类型: {file.file_type_tag || '未知'})
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              onClick={handleExtractTemplatesFromFile}
              loading={extractionLoading}
              block
              disabled={!selectedFileForExtraction}
            >
              从文件中提取出题模板与答题方法
            </Button>
          </Form.Item>
        </Form>

        <Divider orientation="left" style={{ margin: '16px 0' }}>已保存的模板与方法</Divider>
        <List
          dataSource={templatesMethods}
          renderItem={(item, index) => (
            <List.Item
              actions={[
                <Tooltip title="复制答题方法">
                  <Button
                    type="text"
                    icon={copiedIndex === index ? <CheckOutlined style={{ color: 'green' }} /> : <CopyOutlined />}
                    size="small"
                    onClick={() => handleCopy(item.answer_method, index)}
                  />
                </Tooltip>
              ]}
            >
              <List.Item.Meta
                title={<Text strong>出题模板: {item.question_template}</Text>}
                description={<Text type="secondary">答题方法: {item.answer_method}</Text>}
              />
            </List.Item>
          )}
        />
        {!templatesMethods.length && !loadingTemplatesMethods && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无保存的模板和方法" style={{ marginTop: 50 }} />}

        <Divider orientation="left" style={{ margin: '16px 0' }}>根据方法重写答案</Divider>
        <Form layout="vertical">
          <Form.Item label="选择答题方法">
            <Select
              placeholder="选择一个已提取的答题方法"
              value={selectedMethodIndex}
              onChange={setSelectedMethodIndex}
              style={{ width: '100%' }}
            >
              {templatesMethods.map((item, index) => (
                <Option key={index} value={index}>
                  模板: {item.question_template} | 方法: {item.answer_method}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="原始题目">
            <Input.TextArea
              value={rewriteQuestion}
              onChange={(e) => setRewriteQuestion(e.target.value)}
              placeholder="请输入原始题目"
              autoSize={{ minRows: 1, maxRows: 3 }}
            />
          </Form.Item>
          <Form.Item label="原始答案">
            <Input.TextArea
              value={originalAnswer}
              onChange={(e) => setOriginalAnswer(e.target.value)}
              placeholder="请输入原始答案"
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              onClick={handleRewriteAnswer}
              loading={rewriteLoading}
              block
              disabled={!rewriteQuestion.trim() || !originalAnswer.trim() || selectedMethodIndex === null}
            >
              重写答案
            </Button>
          </Form.Item>
          {rewrittenAnswer && (
            <Form.Item label="重写后的答案">
              <Input.TextArea
                value={rewrittenAnswer}
                readOnly
                autoSize={{ minRows: 3, maxRows: 8 }}
                style={{ background: '#f0f2f5' }}
              />
            </Form.Item>
          )}
        </Form>
      </Spin>
    </Modal>
  );
}

export default TemplatesMethodsModal;