// notebook-frontend/src/App.js

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Layout, Menu, Input, Button, Avatar, Dropdown, Space, List, Typography, Divider, Empty,
  Upload, Card, Form, Select, Slider, Switch, notification, Tooltip, Spin, Modal, Tag, // 引入 Tag
} from 'antd';
import {
  SearchOutlined, PlusOutlined, UserOutlined, MessageOutlined, FileOutlined, UploadOutlined,
  SendOutlined, SettingOutlined, RobotOutlined,
} from '@ant-design/icons';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { TextArea, Search } = Input;
const { Option } = Select;

// --- 后端 API 地址配置 ---
const BACKEND_BASE_URL = 'http://localhost:5000/api';

function App() {
  // --- 状态管理 ---
  const [activePane, setActivePane] = useState('chat'); // 'chat', 'files', 'settings'
  const [selectedChatId, setSelectedChatId] = useState(null); // 当前选中的对话ID
  const [messages, setMessages] = useState([]); // 当前对话的消息列表

  const [files, setFiles] = useState([]); // 文件列表
  const [chatHistory, setChatHistory] = useState([]); // 对话历史列表

  const [chatInput, setChatInput] = useState(''); // 用户输入框的内容

  // 新增：当前对话关联的文件ID列表和文件元数据列表
  const [relatedFileIds, setRelatedFileIds] = useState([]);
  const [relatedFilesMeta, setRelatedFilesMeta] = useState([]);

  // 加载状态
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingChatHistory, setLoadingChatHistory] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);

  // 大模型设置
  const [modelSettings, setModelSettings] = useState({
    temperature: 0.7,
    model: 'deepseek-chat', // 默认使用 DeepSeek 的模型
    persona: 'default',
    enableStreaming: false,
  });

  // 文件预览相关状态
  const [isPreviewModalVisible, setIsPreviewModalVisible] = useState(false);
  const [currentPreviewFile, setCurrentPreviewFile] = useState(null);
  const [previewFileContent, setPreviewFileContent] = useState(''); // 预览内容 (文本或图片URL或PDF URL)
  const [loadingPreviewContent, setLoadingPreviewContent] = useState(false);

  // 引用详情Modal相关状态
  const [isCitationModalVisible, setIsCitationModalVisible] = useState(false);
  const [currentCitationContent, setCurrentCitationContent] = useState('');
  const [currentCitationTitle, setCurrentCitationTitle] = useState('');

  const messagesEndRef = useRef(null); // 用于自动滚动到底部

  // --- API 调用函数 ---

  // 获取文件列表
  const fetchFiles = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/files`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setFiles(data);
    } catch (error) {
      notification.error({
        message: '加载文件失败',
        description: `无法从后端获取文件列表: ${error.message}`,
      });
      console.error('Error fetching files:', error);
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  // 获取对话历史列表（只负责获取数据，不自动选择）
  const fetchChatHistory = useCallback(async () => {
    setLoadingChatHistory(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/chat-history`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setChatHistory(data);
      return data; // 返回数据供调用者决定是否选择
    } catch (error) {
      notification.error({
        message: '加载对话历史失败',
        description: `无法从后端获取对话历史: ${error.message}`,
      });
      console.error('Error fetching chat history:', error);
      return [];
    } finally {
      setLoadingChatHistory(false);
    }
  }, []);

  // 获取特定对话的消息 (并加载关联的文件信息)
  const fetchChatMessages = useCallback(async (chatId) => {
    if (!chatId) {
      setMessages([]);
      setRelatedFileIds([]); // 清空关联文件
      setRelatedFilesMeta([]); // 清空关联文件元数据
      return;
    }
    setLoadingMessages(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/chat/${chatId}/messages`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json(); // 后端现在返回 {messages, related_files_meta}
      setMessages(data.messages);
      setRelatedFileIds(data.related_files_meta.map(f => f.id)); // 设置关联文件ID
      setRelatedFilesMeta(data.related_files_meta); // 设置关联文件元数据
    } catch (error) {
      notification.error({
        message: '加载消息失败',
        description: `无法获取对话消息: ${error.message}`,
      });
      console.error('Error fetching chat messages:', error);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // --- useEffect 钩子，在组件加载时或状态变化时调用 API ---
  useEffect(() => {
    fetchFiles();
    const loadAndSelectInitialChatHistory = async () => {
      const history = await fetchChatHistory();
      if (history.length > 0 && selectedChatId === null) {
        setSelectedChatId(history[0].id);
      }
    };
    loadAndSelectInitialChatHistory();
  }, [fetchFiles, fetchChatHistory]);

  useEffect(() => {
    fetchChatMessages(selectedChatId);
  }, [selectedChatId, fetchChatMessages]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // --- 事件处理函数 ---

  // 文件上传处理
  const handleUpload = (info) => {
    if (info.file.status === 'done') {
      notification.success({
        message: '文件上传成功',
        description: `${info.file.name} 已成功上传到您的文件库。`,
      });
      fetchFiles();
    } else if (info.file.status === 'error') {
      notification.error({
        message: '文件上传失败',
        description: `${info.file.name} 上传失败。` + (info.file.response ? `: ${info.file.response.error}` : ''),
      });
      console.error('Upload error:', info.file.error || info.file.response);
    }
  };

  // 发送消息
  const handleSendMessage = async () => {
    if (chatInput.trim() === '') return;
    setSendingMessage(true);

    const userMessage = {
      id: `m_user_${Date.now()}`,
      sender: 'user',
      content: chatInput.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setChatInput('');

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          chatId: selectedChatId,
          modelSettings: modelSettings,
          relatedFileIds: relatedFileIds, // <--- 新增：发送关联文件ID
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      // 关键修改：从 data.aiResponse 中获取 text 和 citations
      const aiText = data.aiResponse.text || data.aiResponse; // 兼容旧的纯文本响应
      const aiCitations = data.aiResponse.citations || []; // 获取引用数据

      const aiResponse = {
        id: `m_ai_${Date.now() + 1}`,
        sender: 'ai',
        content: aiText,
        timestamp: new Date().toLocaleTimeString(),
        citations_data: aiCitations, // <--- 将引用数据存储到消息对象中
        isError: data.aiResponse.text && data.aiResponse.text.includes("错误") // 如果后端返回错误，也标记
      };

      setMessages(prev => [...prev, aiResponse]);

      if (data.newChatId) { // 如果后端返回了新的对话ID，则更新前端的选中ID，并刷新对话历史列表
        setSelectedChatId(data.newChatId);
        await fetchChatHistory();
      } else if (selectedChatId) { // 如果是已有对话，刷新对话历史以更新 lastActive 时间
        await fetchChatHistory();
      }

    } catch (error) {
      notification.error({
        message: '发送消息失败',
        description: `无法连接到AI助手或服务器错误: ${error.message}`,
      });
      console.error('Error sending message:', error);
      setMessages(prevMessages => [...prevMessages, {
        id: `m_error_${Date.now()}`,
        sender: 'system',
        content: `AI助手暂时无法响应或发生错误: ${error.message}`,
        timestamp: new Date().toLocaleTimeString(),
        isError: true,
      }]);
    } finally {
      setSendingMessage(false);
    }
  };

  // 处理文件预览请求
  const handlePreview = async (file) => {
    setCurrentPreviewFile(file);
    setIsPreviewModalVisible(true);
    setPreviewFileContent('');
    setLoadingPreviewContent(true);

    const fileUrl = `${BACKEND_BASE_URL.replace('/api', '')}/uploads/${file.name}`;
    console.log('Attempting to preview file from URL:', fileUrl);

    try {
      if (file.type.startsWith('image')) {
        setPreviewFileContent(fileUrl);
      } else if (file.type === 'pdf') {
        setPreviewFileContent(fileUrl);
      } else if (['txt', 'md', 'json', 'log', 'py', 'js', 'css', 'html', 'xml'].includes(file.type)) {
        const response = await fetch(fileUrl);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to fetch file content: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const textContent = await response.text();
        setPreviewFileContent(textContent);
      } else {
        setPreviewFileContent('UNSUPPORTED_PREVIEW');
        notification.info({
          message: '无法在线预览',
          description: `该文件类型（.${file.type || '未知'}）暂不支持在线预览。您可以尝试下载。`,
          duration: 4,
        });
      }
    } catch (error) {
      notification.error({
        message: '加载预览失败',
        description: `无法加载文件内容: ${error.message}。请检查文件是否存在于服务器或后端服务是否正常。`,
      });
      console.error('Error loading preview:', error);
      setPreviewFileContent('ERROR_LOADING_PREVIEW');
    } finally {
      setLoadingPreviewContent(false);
    }
  };

  // 关闭文件预览弹窗
  const handlePreviewModalClose = () => {
    setIsPreviewModalVisible(false);
    setCurrentPreviewFile(null);
    setPreviewFileContent('');
  };

  // 显示引用详情Modal
  const showCitationDetail = (citation) => {
    setCurrentCitationContent(citation.text);
    setCurrentCitationTitle(`引用 [${citation.id}]：${citation.doc_name}`);
    setIsCitationModalVisible(true);
  };

  // --- UI 渲染数据 ---
  const siderMenuItems = [
    { key: 'chat', icon: <MessageOutlined />, label: '对话历史' },
    { key: 'files', icon: <FileOutlined />, label: '我的文件' },
    { key: 'settings', icon: <SettingOutlined />, label: '应用设置' },
  ];

  const currentChatTitle = selectedChatId
    ? (chatHistory.find(c => c.id === selectedChatId)?.title || '加载中...')
    : '新的对话';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 顶部 Header */}
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        zIndex: 1,
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Title level={3} style={{ margin: 0, marginRight: 30 }}>AI智能助手</Title>
          <Search
            placeholder="全局搜索"
            onSearch={value => console.log('全局搜索:', value)}
            style={{ width: 300 }}
            allowClear
          />
        </div>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelectedChatId(null); // 设置为 null，表示要新建对话
              setMessages([]); // 清空当前消息显示
              setRelatedFileIds([]); // 新增：清空关联文件ID
              setRelatedFilesMeta([]); // 新增：清空关联文件元数据
              notification.info({ message: '开始新的对话！' });
              setActivePane('chat'); // 确保在对话面板
            }}
          >
            新建对话
          </Button>
          <Dropdown
            overlay={<Menu><Menu.Item key="profile">个人资料</Menu.Item><Menu.Item key="logout">退出</Menu.Item></Menu>}
            placement="bottomRight"
          >
            <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
          </Dropdown>
        </Space>
      </Header>

      {/* 主布局：左侧 Sider + 中间/右侧 Content */}
      <Layout style={{ flex: 1, minHeight: 0 }}>
        {/* 左侧 Sider */}
        <Sider
          width={280}
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            overflowY: 'auto',
            minHeight: 0,
          }}
        >
          {/* 主要导航菜单 */}
          <Menu
            mode="inline"
            selectedKeys={[activePane]}
            onClick={e => setActivePane(e.key)}
            style={{ borderRight: 0, paddingBottom: 16 }}
          >
            {siderMenuItems.map(item => (
              <Menu.Item key={item.key} icon={item.icon}>
                {item.label}
              </Menu.Item>
            ))}
          </Menu>

          <Divider style={{ margin: '0 0 16px 0' }} />

          {/* 文件上传区 */}
          <div style={{ padding: '0 16px 16px', textAlign: 'center' }}>
            <Upload
              name="file"
              action={`${BACKEND_BASE_URL}/upload`}
              headers={{
                // 'Authorization': `Bearer ${yourAuthToken}`
              }}
              onChange={handleUpload}
              showUploadList={false}
              multiple={false}
            >
              <Button icon={<UploadOutlined />} block>上传新文件</Button>
            </Upload>
            <Text type="secondary" style={{ fontSize: '12px', marginTop: 8, display: 'block' }}>支持PDF, DOCX, TXT等格式</Text>
          </div>

          <Divider style={{ margin: '0 0 16px 0' }} />

          {/* 文件列表或对话历史或设置内容 */}
          <div style={{ padding: '0 16px 16px' }}>
            {activePane === 'files' && (
              <Spin spinning={loadingFiles}>
                <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>我的文件</Title>
                <List
                  dataSource={files}
                  renderItem={file => (
                    <List.Item
                      key={file.id}
                      actions={[
                        // 新增：添加到当前对话按钮
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
                        description={<Text type="secondary">{file.size} - {file.uploadDate}</Text>}
                      />
                    </List.Item>
                  )}
                />
                {!files.length && !loadingFiles && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文件" style={{ marginTop: 50 }} />}
              </Spin>
            )}
            {activePane === 'chat' && (
              <Spin spinning={loadingChatHistory}>
                <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>对话历史</Title>
                <List
                  dataSource={chatHistory}
                  renderItem={chat => (
                    <List.Item
                      key={chat.id}
                      onClick={() => setSelectedChatId(chat.id)}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        borderRadius: 4,
                        background: selectedChatId === chat.id ? '#e6f7ff' : 'transparent',
                        transition: 'background-color 0.2s',
                        marginBottom: 4,
                      }}
                    >
                      <List.Item.Meta
                        avatar={<MessageOutlined />}
                        title={<Text strong>{chat.title}</Text>}
                        description={<Text type="secondary" style={{ fontSize: 12 }}>上次活跃: {chat.lastActive}</Text>}
                      />
                    </List.Item>
                  )}
                />
                 {!chatHistory.length && !loadingChatHistory && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对话历史" style={{ marginTop: 50 }} />}
              </Spin>
            )}
            {activePane === 'settings' && (
              <div style={{ padding: '16px' }}>
                 <Title level={5}>应用设置</Title>
                 <Text type="secondary">这里将显示应用的全局设置，例如账户设置、隐私设置等。</Text>
                 <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无更多设置项" style={{ marginTop: 50 }} />
              </div>
            )}
          </div>
        </Sider>

        {/* 中间和右侧内容区（Content） */}
        <Content style={{ display: 'flex', flexGrow: 1 }}>
          <div style={{
            flex: 1,
            background: '#f9f9f9',
            borderRight: '1px solid #e0e0e0',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}>
            {/* 对话标题和关联文档显示 */}
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e0e0e0', background: '#fff' }}>
              <Title level={4} style={{ margin: 0 }}>
                {currentChatTitle}
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
            {/* 消息显示区域 - 确保它内部滚动 */}
            <div style={{ flex: 1, padding: '24px', overflowY: 'auto', minHeight: 0 }}>
              <Spin spinning={loadingMessages}>
                {messages.length === 0 && !loadingMessages ? (
                  <Empty
                    description="开始提问或上传文件"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    style={{ marginTop: '50px' }}
                  />
                ) : (
                  messages.map((msg, index) => (
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
                          {/* 仅为 AI 消息处理引用 */}
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
                  ))
                )}
                <div ref={messagesEndRef} /> {/* 滚动锚点 */}
              </Spin>
            </div>

            {/* 输入区 */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid #e0e0e0', background: '#fff' }}>
              <TextArea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="输入您的问题..."
                autoSize={{ minRows: 2, maxRows: 6 }}
                onPressEnter={(e) => {
                  if (e.shiftKey) {
                    // 不做任何操作，让默认行为处理换行
                  } else {
                    e.preventDefault(); // 阻止默认的Enter换行
                    handleSendMessage();
                  }
                }}
                style={{ marginBottom: 10 }}
                disabled={sendingMessage}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSendMessage}
                disabled={chatInput.trim() === '' || sendingMessage}
                loading={sendingMessage}
              >
                发送
              </Button>
            </div>
          </div>

          {/* 右侧功能/工具区 - 确保它内部滚动 */}
          <div style={{
            flex: '0 0 350px',
            background: '#fff',
            padding: '24px',
            overflowY: 'auto',
            borderLeft: '1px solid #e0e0e0',
            minHeight: 0,
          }}>
            <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>对话设置与工具</Title>

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

              <Divider />
              <Title level={5}>常用提示词</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button block onClick={() => setChatInput(prev => prev + '总结上述对话内容。')}>总结对话</Button>
                <Button block onClick={() => setChatInput(prev => prev + '请用英文翻译以下句子：')}>翻译</Button>
                <Button block onClick={() => setChatInput(prev => prev + '生成一个关于[主题]的营销方案。')}>营销方案</Button>
              </Space>

              <Divider />
              <Title level={5}>文件操作 (当前对话无文件)</Title>
              <Empty
                description="请在对话中提及文件或从左侧文件库选择"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                imageStyle={{ height: 60 }}
                style={{ padding: '20px 0' }}
              />
            </Form>
          </div>
        </Content>
      </Layout>

      {/* 文件预览 Modal */}
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

      {/* 引用详情 Modal */}
      <Modal
          title={currentCitationTitle}
          visible={isCitationModalVisible}
          onCancel={() => setIsCitationModalVisible(false)}
          footer={[
              <Button key="close" onClick={() => setIsCitationModalVisible(false)}>关闭</Button>,
          ]}
          width={700}
          bodyStyle={{ maxHeight: '70vh', overflowY: 'auto' }}
      >
          <Input.TextArea
              value={currentCitationContent}
              readOnly
              autoSize={{ minRows: 10, maxRows: 25 }}
              style={{ width: '100%', border: 'none', background: '#f8f8f8' }}
          />
      </Modal>
    </Layout>
  );
}

export default App;
