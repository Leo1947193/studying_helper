// src/pages/IntelligentAssistantPage.js
import React, { useState, useEffect, useCallback } from 'react';
import { Layout, notification } from 'antd';
import ChatSider from '../components/Chat/ChatSider'; // 确保路径正确，已重命名为ChatSider
import ChatMainContent from '../components/Chat/ChatMainContent';
import RightPanel from '../components/Chat/RightPanel';
import FilePreviewModal from '../components/Modals/FilePreviewModal';
import CitationDetailModal from '../components/Modals/CitationDetailModal';
import TemplatesMethodsModal from '../components/Modals/TemplatesMethodsModal';

const { Content } = Layout;

const BACKEND_BASE_URL = 'http://localhost:5000/api';

function IntelligentAssistantPage({
  files, // 从App.js传入，因为它可能是全局的文件列表
  fetchFiles, // 从App.js传入，因为文件列表可能在多个页面共享
  chatHistory, // 从App.js传入
  fetchChatHistory, // 从App.js传入
  selectedChatId, // 从App.js传入
  setSelectedChatId, // 从App.js传入
  notification // 从App.js传入
}) {
  // --- 状态管理 (只保留与聊天页面直接相关的状态) ---
  const [messages, setMessages] = useState([]); // 当前对话的消息列表
  const [chatInput, setChatInput] = useState('');

  // 新增：当前对话关联的文件ID列表和文件元数据列表
  const [relatedFileIds, setRelatedFileIds] = useState([]);
  const [relatedFilesMeta, setRelatedFilesMeta] = useState([]);

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
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);

  // 大模型设置
  const [modelSettings, setModelSettings] = useState({
    temperature: 0.7,
    model: 'deepseek-chat',
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


  // --- API 调用函数 (与聊天页面直接相关) ---
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
  }, [notification]);

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
  }, [notification]);

  // --- useEffect 钩子 ---
  useEffect(() => {
    fetchChatMessages(selectedChatId);
  }, [selectedChatId, fetchChatMessages]);

  useEffect(() => {
    if (isTemplatesModalVisible) {
      fetchTemplatesMethods();
    }
  }, [isTemplatesModalVisible, fetchTemplatesMethods]);

  // --- 事件处理函数 ---
  const handleSendMessage = useCallback(async () => { // 标记为useCallback
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
        await fetchChatHistory(); // 刷新App.js中的对话历史
      } else if (selectedChatId) {
        await fetchChatHistory(); // 刷新App.js中的对话历史
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
  }, [chatInput, selectedChatId, modelSettings, relatedFileIds, notification, setSelectedChatId, fetchChatHistory]); // 添加依赖

  const handleExportChat = useCallback(async () => { // 标记为useCallback
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
  }, [selectedChatId, notification]); // 添加依赖


  const handlePreview = useCallback(async (file) => { // 标记为useCallback
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
  }, [notification]); // 添加依赖

  const handlePreviewModalClose = useCallback(() => { // 标记为useCallback
    setIsPreviewModalVisible(false);
    setCurrentPreviewFile(null);
    setPreviewFileContent('');
  }, []); // 无依赖

  const showCitationDetail = useCallback((citation) => { // 标记为useCallback
    setCurrentCitationContent(citation.text);
    setCurrentCitationTitle(`引用 [${citation.id}]：${citation.doc_name}`);
    setIsCitationModalVisible(true);
  }, []); // 无依赖

  const handleExtractTemplatesFromFile = useCallback(async () => { // 标记为useCallback
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
      fetchTemplatesMethods();
    } catch (error) {
      notification.error({
        message: '提取失败',
        description: `无法提取模板和方法: ${error.message}`,
      });
      console.error('Error extracting templates:', error);
    } finally {
      setExtractionLoading(false);
    }
  }, [selectedFileForExtraction, fetchTemplatesMethods, notification]); // 添加依赖

  const handleRewriteAnswer = useCallback(async () => { // 标记为useCallback
    if (!rewriteQuestion.trim() || !originalAnswer.trim() || selectedMethodIndex === null) {
      notification.warn({ message: '请填写题目、原始答案并选择答题方法。' });
      return;
    }
    setRewriteLoading(true);
    setRewrittenAnswer('');
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
  }, [rewriteQuestion, originalAnswer, selectedMethodIndex, notification]); // 添加依赖


  // 文件上传处理 - 需要在 IntelligentAssistantPage 中处理，因为 Sider 会调用它
  const handleUpload = useCallback((info) => { // 标记为useCallback
    if (info.file.status === 'done') {
      notification.success({
        message: '文件上传成功',
        description: `${info.file.name} (类型: other) 已成功上传。`, // 假设这里文件类型固定为other或从上传组件获取
      });
      fetchFiles(); // 刷新App.js中的文件列表
    } else if (info.file.status === 'error') {
      notification.error({
        message: '文件上传失败',
        description: `${info.file.name} 上传失败。` + (info.file.response ? `: ${info.file.response.error}` : ''),
      });
      console.error('Upload error:', info.file.error || info.file.response);
    }
  }, [fetchFiles, notification]); // 添加依赖


  const currentChatTitle = selectedChatId
    ? (chatHistory.find(c => c.id === selectedChatId)?.title || '加载中...')
    : '新的对话';

  const handleNewChat = useCallback(() => { // 标记为useCallback
    setSelectedChatId(null);
    setMessages([]);
    setRelatedFileIds([]);
    setRelatedFilesMeta([]);
    notification.info({ message: '开始新的对话！' });
    // 不需要setActivePane('chat')，因为这是智能助手页面本身
  }, [setSelectedChatId, notification]); // 添加依赖


  return (
    <Layout style={{ flex: 1, minHeight: 'calc(100vh - 64px)' }}>
      {/* 传递文件相关的props给ChatSider */}
      <ChatSider
        files={files}
        loadingFiles={false} // 或根据实际情况传递
        chatHistory={chatHistory}
        loadingChatHistory={false} // 或根据实际情况传递
        selectedChatId={selectedChatId}
        setSelectedChatId={setSelectedChatId}
        notification={notification}
        // 传递文件上传相关的props
        // uploadFileType={'other'} // 暂时硬编码，如果FileUploadForm需要，可以从App.js传递
        // setUploadFileType={() => {}} // 暂时禁用
        handleUpload={handleUpload} // 从IntelligentAssistantPage传递
        relatedFilesMeta={relatedFilesMeta}
        setRelatedFileIds={setRelatedFileIds}
        setRelatedFilesMeta={setRelatedFilesMeta}
        setChatInput={setChatInput}
        handlePreview={handlePreview}
        onNewChat={handleNewChat} // 新建对话函数
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
          activePane={'chat'}
          setIsTemplatesModalVisible={setIsTemplatesModalVisible}
          modelSettings={modelSettings}
          setModelSettings={setModelSettings}
        />
      </Content>

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

export default IntelligentAssistantPage;