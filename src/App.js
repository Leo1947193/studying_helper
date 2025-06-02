// src/App.js
import React, { useState, useEffect, useCallback } from 'react';
import { Layout, notification } from 'antd';
import './App.css';

// 引入路由组件
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';

// 引入自定义组件
import AppHeader from './components/Layout/AppHeader'; // 引入自定义的AppHeader组件
// 不再直接引入AppSider, ChatMainContent, RightPanel等，它们会在页面组件中引入
// import AppSider from './components/Layout/AppSider';
// import SiderMenu from './components/Layout/SiderMenu';
// import FileUploadForm from './components/Layout/FileUploadForm';
// import FilesPanel from './components/Layout/FilesPanel';
// import ChatHistoryPanel from './components/Layout/ChatHistoryPanel';
// import ChatMainContent from './components/Chat/ChatMainContent';
// import ChatHeader from './components/Chat/ChatHeader';
// import MessageList from './components/Chat/MessageList';
// import ChatInputArea from './components/Chat/ChatInputArea';
// import GeneralTools from './components/Layout/GeneralTools';
// import RightPanel from './components/Layout/RightPanel';
// import ChatSettingsForm from './components/Layout/ChatSettingsForm';
// import FilePreviewModal from './components/Modals/FilePreviewModal';
// import CitationDetailModal from './components/Modals/CitationDetailModal';
// import TemplatesMethodsModal from './components/Modals/TemplatesMethodsModal';

// 引入页面组件
import IntelligentAssistantPage from './pages/IntelligentAssistantPage';
import DashboardPage from './pages/DashboardPage';
import ProjectsPage from './pages/ProjectsPage';

const { Content } = Layout;

// --- 后端 API 地址配置 ---
const BACKEND_BASE_URL = 'http://localhost:5000/api';

// AppContent 组件，使用 useNavigate Hook
function AppContent() {
  const navigate = useNavigate();

  // --- 全局共享状态管理 ---
  const [files, setFiles] = useState([]); // 文件列表 (全局共享)
  const [loadingFiles, setLoadingFiles] = useState(false); // 文件加载状态
  const [chatHistory, setChatHistory] = useState([]); // 对话历史列表 (全局共享)
  const [loadingChatHistory, setLoadingChatHistory] = useState(false); // 对话历史加载状态
  const [selectedChatId, setSelectedChatId] = useState(null); // 当前选中的对话ID (全局共享)

  // --- API 调用函数 (全局共享) ---
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

  const fetchChatHistory = useCallback(async () => {
    setLoadingChatHistory(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/chat-history`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setChatHistory(data);
      return data;
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

  // --- useEffect 钩子 (全局共享数据初始化) ---
  useEffect(() => {
    fetchFiles();
    const loadAndSelectInitialChatHistory = async () => {
      const history = await fetchChatHistory();
      if (history.length > 0 && selectedChatId === null) {
        setSelectedChatId(history[0].id);
      }
    };
    loadAndSelectInitialChatHistory();
  }, [fetchFiles, fetchChatHistory, selectedChatId]);


  // --- 事件处理函数 (全局 Header 导航) ---
  const handleMenuItemClick = (e) => {
    // 根据点击的 key 进行路由跳转
    switch (e.key) {
      case 'dashboard':
        navigate('/dashboard');
        break;
      case 'intelligentAssistant':
        navigate('/intelligent-assistant');
        break;
      case 'projects':
        navigate('/projects');
        break;
      default:
        navigate('/'); // 默认跳转到智能助手页面
        break;
    }
  };

  const handleGlobalSearch = (value) => {
    console.log('全局搜索:', value);
    // 这里可以实现全局搜索逻辑，例如跳转到搜索结果页面
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader
        onGlobalSearch={handleGlobalSearch}
        onMenuItemClick={handleMenuItemClick} // 传入导航点击事件处理器
      />

      <Content style={{ flex: 1 }}> {/* Content作为路由内容的容器 */}
        <Routes>
          {/* 默认路由或主页 */}
          <Route path="/" element={<IntelligentAssistantPage
            files={files}
            fetchFiles={fetchFiles}
            chatHistory={chatHistory}
            fetchChatHistory={fetchChatHistory}
            selectedChatId={selectedChatId}
            setSelectedChatId={setSelectedChatId}
            notification={notification}
          />} />
          {/* 智能助手页面路由 */}
          <Route path="/intelligent-assistant" element={<IntelligentAssistantPage
            files={files}
            fetchFiles={fetchFiles}
            chatHistory={chatHistory}
            fetchChatHistory={fetchChatHistory}
            selectedChatId={selectedChatId}
            setSelectedChatId={setSelectedChatId}
            notification={notification}
          />} />
          {/* 仪表盘页面路由 */}
          <Route path="/dashboard" element={<DashboardPage />} />
          {/* 项目页面路由 */}
          <Route path="/projects" element={<ProjectsPage />} />
          {/* TODO: 其他页面路由 */}
        </Routes>
      </Content>
    </Layout>
  );
}

// 根组件，包裹在 BrowserRouter 中
function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;