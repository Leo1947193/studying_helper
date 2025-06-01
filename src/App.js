// notebook-frontend/src/App.js
//TODO: 1. 拆分组件
//TODO: 2. 设计homepage
//TODO: 3. 优化样式
//TODO: 4. 给其他人列TODO

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Layout, notification } from 'antd'; // 仅保留Ant Design的布局和通知
import './App.css';

import AppHeader from './components/Layout/AppHeader'; // 引入自定义的AppHeader组件
import AppSider from './components/Layout/AppSider'; // 引入自定义的AppSider组件
import SiderMenu from './components/Layout/SiderMenu'; // 引入自定义的SiderMenu组件
import FileUploadForm from './components/Layout/FileUploadForm'; // 引入自定义的FileUploadForm组件
import FilesPanel from './components/Layout/FilesPanel'; // 引入自定义的FilesPanel组件
import ChatHistoryPanel from './components/Layout/ChatHistoryPanel'; // 引入自定义的ChatHistoryPanel组件
import ChatMainContent from './components/Chat/ChatMainContent'; // 引入自定义的ChatMainContent组件
import ChatHeader from './components/Chat/ChatHeader';
import MessageList from './components/Chat/MessageList'; // 引入自定义的MessageList组件
import ChatInputArea from './components/Chat/ChatInputArea';
import GeneralTools from './components/Layout/GeneralTools'; // 引入通用工具组件
import RightPanel from './components/Layout/RightPanel'; // 引入右侧面板组件
import ChatSettingsForm from './components/Layout/ChatSettingsForm'; // 引入聊天设置表单组件
import FilePreviewModal from './components/Modals/FilePreviewModal';// 引入文件预览模态框组件
import CitationDetailModal from './components/Modals/CitationDetailModal'; // 引入引用详情模态框组件
import TemplatesMethodsModal from './components/Modals/TemplatesMethodsModal'; // 引入答题方法和模板模态框组件


const { Content } = Layout;

// --- 后端 API 地址配置 ---
const BACKEND_BASE_URL = 'http://localhost:5000/api';

function App() {
  // --- 状态管理 ---
  const [activePane, setActivePane] = useState('chat'); // 'chat', 'files', 'settings' (templates now in modal)
  const [selectedChatId, setSelectedChatId] = useState(null); // 当前选中的对话ID
  const [messages, setMessages] = useState([]); // 当前对话的消息列表

  const [files, setFiles] = useState([]); // 文件列表
  const [chatHistory, setChatHistory] = useState([]); // 对话历史列表

  const [chatInput, setChatInput] = useState('');

  // 新增：当前对话关联的文件ID列表和文件元数据列表
  const [relatedFileIds, setRelatedFileIds] = useState([]);
  const [relatedFilesMeta, setRelatedFilesMeta] = useState([]);

  // 新增：文件上传类型
  const [uploadFileType, setUploadFileType] = useState('other'); // '课本', '往年卷', '答案', '其他'

  // 新增：模板与方法管理相关状态
  const [templatesMethods, setTemplatesMethods] = useState([]);
  const [loadingTemplatesMethods, setLoadingTemplatesMethods] = useState(false);
  const [isTemplatesModalVisible, setIsTemplatesModalVisible] = useState(false); // 控制答题方法Modal的可见性
  const [selectedFileForExtraction, setSelectedFileForExtraction] = useState(null); // 选中的用于提取模板的文件ID
  const [extractionLoading, setExtractionLoading] = useState(false);
  const [rewriteQuestion, setRewriteQuestion] = useState('');
  const [originalAnswer, setOriginalAnswer] = useState('');
  const [selectedMethodIndex, setSelectedMethodIndex] = useState(null);
  const [rewrittenAnswer, setRewrittenAnswer] = useState('');
  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null); // 用于复制按钮的复制状态

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
  const [previewFileContent, setPreviewFileContent] = useState('');
  const [loadingPreviewContent, setLoadingPreviewContent] = useState(false);

  // 引用详情Modal相关状态
  const [isCitationModalVisible, setIsCitationModalVisible] = useState(false);
  const [currentCitationContent, setCurrentCitationContent] = useState('');
  const [currentCitationTitle, setCurrentCitationTitle] = useState('');

  // messagesEndRef 不再需要在这里，它应该在 MessageList 或 ChatMainContent 内部使用
  // const messagesEndRef = useRef(null);

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
      setRelatedFileIds([]);
      setRelatedFilesMeta([]);
      return;
    }
    setLoadingMessages(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/chat/${chatId}/messages`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setMessages(data.messages);
      setRelatedFileIds(data.related_files_meta.map(f => f.id));
      setRelatedFilesMeta(data.related_files_meta);
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

  // 获取模板和方法列表
  const fetchTemplatesMethods = useCallback(async () => {
    setLoadingTemplatesMethods(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/templates/list`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setTemplatesMethods(data);
    } catch (error) {
      notification.error({
        message: '加载模板失败',
        description: `无法从后端获取模板和方法列表: ${error.message}`,
      });
      console.error('Error fetching templates/methods:', error);
    } finally {
      setLoadingTemplatesMethods(false);
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

  // 当答题方法Modal可见时，加载模板数据
  useEffect(() => {
    if (isTemplatesModalVisible) {
      fetchTemplatesMethods();
    }
  }, [isTemplatesModalVisible, fetchTemplatesMethods]); // 依赖于 isTemplatesModalVisible

  // messagesEndRef 逻辑现在在 ChatMainContent.js
  // useEffect(() => {
  //   messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  // }, [messages]);


  // --- 事件处理函数 ---

  // 文件上传处理
  const handleUpload = (info) => {
    if (info.file.status === 'done') {
      notification.success({
        message: '文件上传成功',
        description: `${info.file.name} (类型: ${uploadFileType}) 已成功上传。`,
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
          relatedFileIds: relatedFileIds,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      const aiText = data.aiResponse.text || data.aiResponse;
      const aiCitations = data.aiResponse.citations || [];

      const aiResponse = {
        id: `m_ai_${Date.now() + 1}`,
        sender: 'ai',
        content: aiText,
        timestamp: new Date().toLocaleTimeString(),
        citations_data: aiCitations,
        isError: data.aiResponse.text && data.aiResponse.text.includes("错误")
      };

      setMessages(prev => [...prev, aiResponse]);

      if (data.newChatId) {
        setSelectedChatId(data.newChatId);
        await fetchChatHistory();
      } else if (selectedChatId) {
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

  // 导出对话为 DOCX
  const handleExportChat = async () => {
    if (!selectedChatId) {
      notification.warn({ message: '请先选择一个对话再导出。' });
      return;
    }
    notification.info({ message: '正在生成对话文档...' });
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/export-chat/${selectedChatId}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'chat_history.docx';
      if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
        filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
      }
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      notification.success({ message: '对话文档已导出成功！' });
    } catch (error) {
      notification.error({
        message: '导出失败',
        description: `无法导出对话文档: ${error.message}`,
      });
      console.error('Error exporting chat:', error);
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

  // --- 新功能：答题方法和模板提取相关操作 ---
  const handleExtractTemplatesFromFile = async () => {
    if (!selectedFileForExtraction) {
      notification.warn({ message: '请选择一个文件进行提取。' });
      return;
    }
    setExtractionLoading(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/templates/extract-from-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileId: selectedFileForExtraction }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      notification.success({
        message: '提取成功',
        description: data.message,
      });
      fetchTemplatesMethods(); // 刷新列表
    } catch (error) {
      notification.error({
        message: '提取失败',
        description: `无法提取模板和方法: ${error.message}`,
      });
      console.error('Error extracting templates:', error);
    } finally {
      setExtractionLoading(false);
    }
  };

  const handleRewriteAnswer = async () => {
    if (!rewriteQuestion.trim() || !originalAnswer.trim() || selectedMethodIndex === null) {
      notification.warn({ message: '请填写题目、原始答案并选择答题方法。' });
      return;
    }
    setRewriteLoading(true);
    setRewrittenAnswer(''); // 清空上次结果
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/templates/rewrite-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: rewriteQuestion,
          originalAnswer: originalAnswer,
          methodIndex: selectedMethodIndex,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setRewrittenAnswer(data.rewrittenAnswer);
      notification.success({ message: '答案重写成功！' });
    } catch (error) {
      notification.error({
        message: '重写失败',
        description: `无法重写答案: ${error.message}`,
      });
      console.error('Error rewriting answer:', error);
    } finally {
      setRewriteLoading(false);
    }
  };

  // handleCopy 不再需要在这里，它现在在TemplatesMethodsModal.js 内部处理
  // const handleCopy = (text, index) => {
  //   navigator.clipboard.writeText(text).then(() => {
  //     setCopiedIndex(index);
  //     setTimeout(() => setCopiedIndex(null), 2000); // 2秒后恢复
  //     notification.success({message: "已复制到剪贴板！"});
  //   }).catch(err => {
  //     notification.error({message: "复制失败，请手动复制！"});
  //     console.error('Failed to copy text: ', err);
  //   });
  // };


  // --- UI 渲染数据 ---
  // 从antd导入Icons
  const { MessageOutlined, FileOutlined, SettingOutlined } = require('@ant-design/icons');

  const siderMenuItems = [
    { key: 'chat', icon: <MessageOutlined />, label: '对话历史' },
    { key: 'files', icon: <FileOutlined />, label: '我的文件' },
    { key: 'settings', icon: <SettingOutlined />, label: '应用设置' },
    // 移除了 'templates' 菜单项，因为它现在由右侧的按钮触发Modal
  ];

  
  const currentChatTitle = selectedChatId
    ? (chatHistory.find(c => c.id === selectedChatId)?.title || '加载中...')
    : '新的对话';

    const handleNewChat = () => {
    setSelectedChatId(null);
    setMessages([]);
    setRelatedFileIds([]);
    setRelatedFilesMeta([]);
    notification.info({ message: '开始新的对话！' });
    setActivePane('chat');
  };

  const handleGlobalSearch = (value) => {
    console.log('全局搜索:', value);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader
        onNewChat={handleNewChat}
        onGlobalSearch={handleGlobalSearch}
      />

      <Layout style={{ flex: 1, minHeight: 0 }}>
        <AppSider
          activePane={activePane}
          setActivePane={setActivePane}
          siderMenuItems={siderMenuItems}
          uploadFileType={uploadFileType}
          setUploadFileType={setUploadFileType}
          handleUpload={handleUpload}
          files={files}
          loadingFiles={loadingFiles}
          relatedFilesMeta={relatedFilesMeta}
          setRelatedFileIds={setRelatedFileIds}
          setRelatedFilesMeta={setRelatedFilesMeta}
          setChatInput={setChatInput}
          handlePreview={handlePreview}
          chatHistory={chatHistory}
          loadingChatHistory={loadingChatHistory}
          selectedChatId={selectedChatId}
          setSelectedChatId={setSelectedChatId}
          notification={notification}
        />

        <Content style={{ display: 'flex', flexGrow: 1 }}>
          <ChatMainContent
            currentChatTitle={currentChatTitle}
            handleExportChat={handleExportChat}
            relatedFilesMeta={relatedFilesMeta}
            setRelatedFileIds={setRelatedFileIds}
            setRelatedFilesMeta={setRelatedFilesMeta}
            notification={notification}
            loadingMessages={loadingMessages}
            messages={messages}
            showCitationDetail={showCitationDetail}
            chatInput={chatInput}
            setChatInput={setChatInput}
            handleSendMessage={handleSendMessage}
            sendingMessage={sendingMessage}
          />

          <RightPanel
            activePane={activePane}
            setIsTemplatesModalVisible={setIsTemplatesModalVisible}
            modelSettings={modelSettings}
            setModelSettings={setModelSettings}
          />
        </Content>
      </Layout>

      <FilePreviewModal
        isPreviewModalVisible={isPreviewModalVisible}
        handlePreviewModalClose={handlePreviewModalClose}
        currentPreviewFile={currentPreviewFile}
        previewFileContent={previewFileContent}
        loadingPreviewContent={loadingPreviewContent}
      />

      <CitationDetailModal
        isCitationModalVisible={isCitationModalVisible}
        setIsCitationModalVisible={setIsCitationModalVisible}
        currentCitationContent={currentCitationContent}
        currentCitationTitle={currentCitationTitle}
      />

      <TemplatesMethodsModal
        isTemplatesModalVisible={isTemplatesModalVisible}
        setIsTemplatesModalVisible={setIsTemplatesModalVisible}
        loadingTemplatesMethods={loadingTemplatesMethods}
        templatesMethods={templatesMethods}
        files={files}
        selectedFileForExtraction={selectedFileForExtraction}
        setSelectedFileForExtraction={setSelectedFileForExtraction}
        handleExtractTemplatesFromFile={handleExtractTemplatesFromFile}
        extractionLoading={extractionLoading}
        rewriteQuestion={rewriteQuestion}
        setRewriteQuestion={setRewriteQuestion}
        originalAnswer={originalAnswer}
        setOriginalAnswer={setOriginalAnswer}
        selectedMethodIndex={selectedMethodIndex}
        setSelectedMethodIndex={setSelectedMethodIndex}
        handleRewriteAnswer={handleRewriteAnswer}
        rewriteLoading={rewriteLoading}
        rewrittenAnswer={rewrittenAnswer}
        copiedIndex={copiedIndex}
        setCopiedIndex={setCopiedIndex}
      />
    </Layout>
  );
}

export default App;
