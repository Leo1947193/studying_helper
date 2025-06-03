// notebook-frontend/src/App.js

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Layout, Menu, Input, Button, Avatar, Dropdown, Space, List, Typography, Divider, Empty,
  Upload, Card, Form, Select, Slider, Switch, notification, Tooltip, Spin, Modal, Tag, Radio, Alert
} from 'antd';
import {
  SearchOutlined, PlusOutlined, UserOutlined, MessageOutlined, FileOutlined, UploadOutlined,
  SendOutlined, SettingOutlined, RobotOutlined, CopyOutlined, CheckOutlined, DownloadOutlined,
  LoadingOutlined, FolderOutlined, HomeOutlined, DeleteOutlined, MoreOutlined, BarChartOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Routes, Route } from 'react-router-dom'; // 导入 Routes 和 Route
import ProjectIntroPage from './ProjectIntroPage';
import './App.css'; // 确保你的 CSS 文件被正确导入
import './ProjectIntroPage.css'; // 确保项目介绍页面的样式被正确导入

const { Header, Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { TextArea, Search } = Input;
const { Option } = Select;

// --- Backend API Base URL ---
const BACKEND_BASE_URL = 'http://localhost:5000/api';

// --- 定义思维导图图片路径 ---
const COMPLETE_MINDMAP_IMAGE_PATH = '/1.png'; // 对应选择“否 (完整)”
const FILTERED_MINDMAP_IMAGE_PATH = '/2.png'; // 对应选择“是 (重点)”


function App() {
  // --- Routing Hooks ---
  const { projectId: urlProjectId } = useParams(); // Get project ID from URL
  const navigate = useNavigate(); // For navigation

  // --- Global State Management ---
  const [currentProjectId, setCurrentProjectId] = useState(() => {
    const savedProjectId = localStorage.getItem('currentProjectId');
    return urlProjectId || savedProjectId || null;
  });
  const [projects, setProjects] = useState([]); // List of projects

  // --- In-Project State Management (These states need to be reset or reloaded when switching projects) ---
  const [activePane, setActivePane] = useState('chat'); // 'chat', 'files', 'settings'
  const [selectedChatId, setSelectedChatId] = useState(null); // Current selected chat ID
  const [messages, setMessages] = useState([]); // Messages for the current chat

  const [files, setFiles] = useState([]); // List of files for the current project
  const [chatHistory, setChatHistory] = useState([]); // Chat history for the current project

  const [chatInput, setChatInput] = useState('');

  // Current chat's associated file IDs and their metadata
  const [relatedFileIds, setRelatedFileIds] = useState([]);
  const [relatedFilesMeta, setRelatedFilesMeta] = useState([]);

  // File upload type
  const [uploadFileType, setUploadFileType] = useState('textbook');

  // Template & Method management states
  const [templatesMethods, setTemplatesMethods] = useState([]);
  const [loadingTemplatesMethods, setLoadingTemplatesMethods] = useState(false);
  const [isTemplatesModalVisible, setIsTemplatesModalVisible] = useState(false);
  const [selectedFileForExtraction, setSelectedFileForExtraction] = useState(null);
  const [extractionLoading, setExtractionLoading] = useState(false);
  const [rewriteQuestion, setRewriteQuestion] = useState('');
  const [originalAnswer, setOriginalAnswer] = useState(''); // 修正：这里少了一个 useState
  const [selectedMethodIndex, setSelectedMethodIndex] = useState(null);
  const [rewrittenAnswer, setRewrittenAnswer] = useState('');
  const [rewriteLoading, setLoadingRewrite] = useState(false);

  const [copiedIndex, setCopiedIndex] = useState(null); // State for copy feedback

  // Dashboard/Mind Map states
  const [isDashboardModalVisible, setIsDashboardModalVisible] = useState(false);
  const [selectedFileForMindMap, setSelectedFileForMindMap] = useState(null);
  // mindMapImageSrc 存储要显示的图片路径，null表示未显示
  const [mindMapImageSrc, setMindMapImageSrc] = useState(null);
  const [loadingMindMap, setLoadingMindMap] = useState(false);
  const [mindMapError, setMindMapError] = useState(null);

  // Loading states
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingChatHistory, setLoadingChatHistory] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);

  // LLM settings
  const [modelSettings, setModelSettings] = useState({
    temperature: 0.7,
    model: 'deepseek-chat',
    persona: 'default',
    enableStreaming: false,
  });

  // File preview states
  const [isPreviewModalVisible, setIsPreviewModalVisible] = useState(false);
  const [currentPreviewFile, setCurrentPreviewFile] = useState(null);
  const [previewFileContent, setPreviewFileContent] = useState('');
  const [loadingPreviewContent, setLoadingPreviewContent] = useState(false);

  // Citation detail Modal states
  const [isCitationModalVisible, setIsCitationModalVisible] = useState(false);
  const [currentCitationContent, setCurrentCitationContent] = useState('');
  const [currentCitationTitle, setCurrentCitationTitle] = useState('');

  const messagesEndRef = useRef(null);

  // --- API Call Functions ---

  // Fetch list of projects (保持不变)
  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      const data = await response.json();
      setProjects(data);

      let projectToLoadId = null;
      if (urlProjectId) {
        projectToLoadId = urlProjectId;
      } else if (currentProjectId === null) {
          // Stay on project list if explicitly navigated back
      } else if (localStorage.getItem('currentProjectId')) {
        projectToLoadId = localStorage.getItem('currentProjectId');
      } else if (data.length > 0) {
        projectToLoadId = data[0].id;
      }

      const projectExistsInFetchedData = projectToLoadId ? data.some(p => p.id === projectToLoadId) : false;

      if (projectToLoadId && projectExistsInFetchedData) {
        if (projectToLoadId !== currentProjectId) {
          setCurrentProjectId(projectToLoadId);
          navigate(`/projects/${projectToLoadId}`);
        }
      } else if (projectToLoadId && !projectExistsInFetchedData) {
        notification.warn({ message: '指定的项目不存在或已删除，已返回项目列表。' });
        setCurrentProjectId(null);
        navigate('/');
      } else if (data.length === 0 && currentProjectId !== null) {
        notification.info({ message: '当前没有可用的项目，请创建新项目。' });
        setCurrentProjectId(null);
        navigate('/');
      }
    } catch (error) {
      notification.error({
        message: '加载项目失败',
        description: `无法从后端获取项目列表: ${error.message}`,
      });
      console.error('Error fetching projects:', error);
    } finally {
      setLoadingProjects(false);
    }
  }, [urlProjectId, currentProjectId, navigate]);


  // Fetch files for the current project (保持不变)
  const fetchFiles = useCallback(async () => {
    if (!currentProjectId) return;
    setLoadingFiles(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/files`);
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
  }, [currentProjectId]);

  // Fetch chat history for the current project (保持不变)
  const fetchChatHistory = useCallback(async () => {
    if (!currentProjectId) return [];
    setLoadingChatHistory(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/chat-history`);
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
  }, [currentProjectId]);

  // Fetch messages for a specific chat within the current project (保持不变)
  const fetchChatMessages = useCallback(async (chatId) => {
    if (!currentProjectId || !chatId) {
      setMessages([]);
      setRelatedFileIds([]);
      setRelatedFilesMeta([]);
      return;
    }
    setLoadingMessages(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/chat/${chatId}/messages`);
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
  }, [currentProjectId]);

  // Fetch templates and methods (保持不变)
  const fetchTemplatesMethods = useCallback(async () => {
    if (!currentProjectId) {
      console.warn("No project selected, cannot fetch templates.");
      return;
    }

    setLoadingTemplatesMethods(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/templates/list`);
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
  }, [currentProjectId]);


  // --- useEffect Hooks ---

  // Fetch projects on initial load (保持不变)
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Load project-specific data (files, chat history) when currentProjectId changes (保持不变)
  useEffect(() => {
    if (currentProjectId) {
      fetchFiles();
      const loadAndSelectInitialChatHistory = async () => {
        const history = await fetchChatHistory();
        if (history.length > 0 && selectedChatId === null) {
          setSelectedChatId(history[0].id);
        } else if (history.length === 0) {
            setSelectedChatId(null);
            setMessages([]);
            setRelatedFileIds([]);
            setRelatedFilesMeta([]);
        }
      };
      loadAndSelectInitialChatHistory();
    } else {
        setFiles([]);
        setChatHistory([]);
        setSelectedChatId(null);
        setMessages([]);
        setRelatedFileIds([]);
        setRelatedFilesMeta([]);
    }
  }, [currentProjectId, fetchFiles, fetchChatHistory, selectedChatId]);

  // Load chat messages when selectedChatId changes (保持不变)
  useEffect(() => {
    fetchChatMessages(selectedChatId);
  }, [selectedChatId, fetchChatMessages]);

  // Load templates when the templates modal is visible and a project is selected (保持不变)
  useEffect(() => {
    if (isTemplatesModalVisible && currentProjectId) {
      fetchTemplatesMethods();
    }
  }, [isTemplatesModalVisible, currentProjectId, fetchTemplatesMethods]);

  // Auto-scroll chat to bottom when messages change (保持不变)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Persist currentProjectId to localStorage (保持不变)
  useEffect(() => {
    if (currentProjectId) {
      localStorage.setItem('currentProjectId', currentProjectId);
    } else {
      localStorage.removeItem('currentProjectId');
    }
  }, [currentProjectId]);

  // --- 移除 OrgChart 渲染的 useEffect ---


  // --- Event Handlers ---

  // File upload handler (关键修改：通知消息更准确)
  const handleUpload = async (options) => {
    const { file, onSuccess, onError } = options;
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再上传文件。' });
      onError(new Error('No project selected.'));
      return;
    }

    setUploadingFile(true);
    notification.info({
      message: '文件上传中...',
      description: `${file.name} 正在上传，并将在后台进行处理。这可能需要一些时间。`,
      duration: 0,
      key: 'upload_processing',
      icon: <LoadingOutlined />,
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type_tag', uploadFileType); // <--- 关键修改：发送文件类型标签

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      notification.success({
        message: '文件上传成功',
        description: `${file.name} 已成功上传。${uploadFileType === 'textbook' ? '作为教材，后端应跳过部分AI处理；' : uploadFileType === 'question' ? '作为题目，后端将不做额外处理。' : '后台处理已启动。'} 请稍后刷新文件列表查看处理结果。`,
        duration: 5,
        key: 'upload_processing',
      });
      onSuccess(data, file);
      // 延时刷新文件列表，给后端处理时间
      setTimeout(() => fetchFiles(), 3000);
    } catch (error) {
      notification.error({
        message: '文件上传失败',
        description: `${file.name} 上传失败。` + error.message,
        duration: 0,
        key: 'upload_processing',
      });
      console.error('Upload error:', error);
      onError(error);
    } finally {
      setUploadingFile(false);
    }
  };

  // Send message to LLM (保持不变)
  const handleSendMessage = async () => {
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再进行对话。' });
      return;
    }
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
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/chat`, {
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
        throw new Error(errorData.aiResponse.text || `HTTP error! status: ${response.status} - ${response.statusText}`);
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

  // Export chat to DOCX (保持不变)
  const handleExportChat = async () => {
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再导出对话。' });
      return;
    }
    if (!selectedChatId) {
      notification.warn({ message: '请先选择一个对话再导出。' });
      return;
    }
    notification.info({ message: '正在生成对话文档...' });
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/export-chat/${selectedChatId}`);
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


  // Handle file preview request (保持不变)
  const handlePreview = async (file) => {
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再预览文件。' });
      return;
    }
    setCurrentPreviewFile(file);
    setIsPreviewModalVisible(true);
    setPreviewFileContent('');
    setLoadingPreviewContent(true);

    const previewFileRelativePath = `${file.processed_dir_name}/${file.name}`;
    const fileUrl = `${BACKEND_BASE_URL.replace('/api', '')}/uploads/${currentProjectId}/${previewFileRelativePath}`;
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
      setPreviewFileContent('ERROR_LOADING_PREVIEW');
      console.error('Error loading preview:', error);
    } finally {
      setLoadingPreviewContent(false);
    }
  };

  // Close file preview modal (保持不变)
  const handlePreviewModalClose = () => {
    setIsPreviewModalVisible(false);
    setCurrentPreviewFile(null);
    setPreviewFileContent('');
  };

  // Show citation detail modal (保持不变)
  const showCitationDetail = (citation) => {
    setCurrentCitationContent(citation.text);
    setCurrentCitationTitle(`引用 [${citation.id}]：${citation.doc_name}`);
    setIsCitationModalVisible(true);
  };

  // --- Template & Method Extraction Operations --- (保持不变)
  const handleExtractTemplatesFromFile = async () => {
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再提取模板。' });
      return;
    }
    if (!selectedFileForExtraction) {
      notification.warn({ message: '请选择一个文件进行提取。' });
      return;
    }
    const fileToExtract = files.find(f => f.id === selectedFileForExtraction);
    if (!fileToExtract || !fileToExtract.is_processed) {
      notification.warn({
        message: '文件尚未完全处理',
        description: '请选择一个已处理完成的文件（绿色“已处理”标签）来提取模板和方法。',
        duration: 5,
      });
      return;
    }

    setExtractionLoading(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/templates/extract-from-file`, {
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
  };

  const handleRewriteAnswer = async () => {
    if (!currentProjectId) {
      notification.error({ message: '请先选择或创建一个项目再重写答案。' });
      return;
    }
    if (!rewriteQuestion.trim() || !originalAnswer.trim() || selectedMethodIndex === null) {
      notification.warn({ message: '请填写题目、原始答案并选择答题方法。' });
      return;
    }
    setLoadingRewrite(true);
    setRewrittenAnswer('');
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects/${currentProjectId}/templates/rewrite-answer`, {
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
      setLoadingRewrite(false);
    }
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
      notification.success({message: "已复制到剪贴板！"});
    }).catch(err => {
      notification.error({message: "复制失败，请手动复制！"});
      console.error('Failed to copy text: ', err);
    });
  };

  // --- Project List & Creation Functions --- (保持不变)
  const handleCreateProject = () => {
    console.log('Create new project button clicked!');
    Modal.confirm({
      title: '创建新项目',
      content: (
        <Input
          placeholder="请输入项目名称"
          id="new_project_name_input"
          onPressEnter={(e) => {
            const name = e.target.value.trim();
            if (name) {
              Modal.destroyAll();
              confirmCreateProject(name);
            } else {
              notification.warn({ message: '项目名称不能为空。' });
            }
          }}
        />
      ),
      okText: '创建',
      cancelText: '取消',
      onOk: () => {
        const projectName = document.getElementById('new_project_name_input').value.trim();
        if (projectName) {
          return confirmCreateProject(projectName);
        } else {
          notification.warn({ message: '项目名称不能为空。' });
          return Promise.reject('Project name empty');
        }
      },
    });
  };

  const confirmCreateProject = async (projectName) => {
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectName }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      notification.success({ message: `项目 '${data.project.name}' 创建成功！` });
      setProjects(prev => [...prev, data.project]);
      setCurrentProjectId(data.project.id);
      navigate(`/projects/${data.project.id}`);
    } catch (error) {
      notification.error({
        message: '创建项目失败',
        description: `无法创建项目: ${error.message}`,
      });
      console.error('Error creating project:', error);
      throw error;
    }
  };

  const handleSelectProject = (projectId) => {
    setCurrentProjectId(projectId);
    const projectName = projects.find(p => p.id === projectId)?.name || projectId;
    notification.success({ message: `已进入项目：${projectName}` });
    navigate(`/projects/${projectId}`);
  };

  const handleDeleteProject = (projectId, projectName) => {
    Modal.confirm({
      title: `确认删除项目 "${projectName}" ?`,
      content: '此操作将永久删除项目及其所有文件和对话记录，不可恢复！',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${BACKEND_BASE_URL}/projects/${projectId}`, {
            method: 'DELETE',
          });
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
          }
          notification.success({ message: `项目 "${projectName}" 已成功删除。` });
          setProjects(prev => prev.filter(p => p.id !== projectId));
          if (currentProjectId === projectId) {
            setCurrentProjectId(null);
            navigate('/');
          }
        } catch (error) {
          notification.error({
            message: '删除项目失败',
            description: `无法删除项目: ${error.message}`,
          });
          console.error('Error deleting project:', error);
        }
      },
    });
  };

  // --- Dashboard/Mind Map Functions ---
  const handleGenerateMindMapTrigger = () => {
    if (!selectedFileForMindMap) {
      notification.warn({ message: '请选择一个文件来生成思维导图。' });
      return;
    }

    // 筛选：只允许选择“教材”类型的文件来触发图片显示
    const fileToProcess = files.find(f => f.id === selectedFileForMindMap);
    if (!fileToProcess || fileToProcess.file_type_tag !== 'textbook') {
      notification.warn({
        message: '文件类型不符',
        description: '请选择一个“教材”文件来生成思维导图。',
        duration: 5,
      });
      return;
    }

    // --- 恢复询问逻辑 ---
    Modal.confirm({
      title: '生成思维导图',
      content: '您希望根据往年卷提取的重点来生成思维导图吗？\n（选择“是”将显示重点版图片，选择“否”将显示完整版图片。）',
      okText: '是 (重点)',
      cancelText: '否 (完整)',
      onOk: () => handleGenerateMindMapClick(FILTERED_MINDMAP_IMAGE_PATH), // 点击“是”，显示 2.png
      onCancel: () => handleGenerateMindMapClick(COMPLETE_MINDMAP_IMAGE_PATH), // 点击“否”，显示 1.png
    });
  };


  // 关键修改：此函数现在接收图片路径作为参数
  const handleGenerateMindMapClick = async (imagePath) => {
    setLoadingMindMap(true);
    setMindMapError(null);
    setMindMapImageSrc(null); // 先清空当前图片，避免闪烁

    try {
      // 模拟加载时间
      await new Promise(resolve => setTimeout(resolve, 500));

      // 设置 mindMapImageSrc 为接收到的图片路径
      setMindMapImageSrc(imagePath);
      notification.success({ message: `思维导图已加载` });

    } catch (error) {
      setMindMapError(`加载思维导图图片失败: ${error.message}`);
      notification.error({
        message: '加载失败',
        description: `无法加载思维导图图片: ${error.message}`,
      });
      console.error('Error loading mind map image:', error);
    } finally {
      setLoadingMindMap(false);
    }
  };


  const currentProject = currentProjectId ? projects.find(p => p.id === currentProjectId) : null;
  const currentChatTitle = selectedChatId
    ? (chatHistory.find(c => c.id === selectedChatId)?.title || '加载中...')
    : '新的对话';

  // --- Main Render Logic ---
  // If no project is selected, show the project selection/creation interface
  if (!currentProjectId) {
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
        <Header style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          zIndex: 1,
        }}>
          {/* 这里是项目选择界面的标题，可以保留文本或也替换为图片 */}
          <Title level={3} style={{ margin: 0 }}>EduMind - 我的项目</Title>
        </Header>
        <Content
          style={{
            padding: '50px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: 'radial-gradient(circle at center, #e3f2fd 0%, #bbdefb 50%, #90caf9 100%)',
            overflowY: 'auto',
          }}
        >
          <div style={{
            background: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(5px)',
            borderRadius: 16,
            padding: '40px 60px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.15)',
            maxWidth: '1200px',
            width: '100%',
            marginBottom: '40px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}>
            <Title level={2} style={{ marginBottom: 20, color: '#212121', fontWeight: 600 }}>
              欢迎来到 EduMind
            </Title>
            <Paragraph type="secondary" style={{ marginBottom: 40, fontSize: 16, textAlign: 'center', maxWidth: '600px' }}>
              智学引擎（EduMind）—— 基于大模型与 RAG 技术的 AI 教育平台，构建动态知识图谱，提供智能出题、个性化学习路径规划及多模态智能批改服务，助力师生突破资源壁垒，高效实现‘学练考评’闭环，让教育更智能、更公平！
            </Paragraph>

            <Button
              type="primary"
              size="large"
              icon={<PlusOutlined />}
              onClick={handleCreateProject}
              style={{ marginBottom: 30, padding: '10px 30px', height: 'auto', fontSize: 18 }}
            >
              创建新项目
            </Button>
            <Divider style={{ margin: '30px 0', borderColor: '#ccc', width: '80%' }}>或选择已有项目</Divider>
          </div>

          <Spin spinning={loadingProjects} style={{ width: '100%', maxWidth: '1200px' }}>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '24px',
              justifyContent: 'flex-start',
              alignItems: 'flex-start',
              width: '100%',
              padding: '0 12px',
            }}>
              {Array.isArray(projects) && projects.length > 0 ? (
                projects.map(project => (
                  <Card
                    key={project.id}
                    hoverable
                    onClick={() => handleSelectProject(project.id)}
                    style={{
                      textAlign: 'center',
                      padding: '20px 0',
                      borderRadius: 12,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                      width: 220,
                      height: 180,
                      flexShrink: 0,
                      flexGrow: 0,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.3s ease',
                      border: '1px solid #f0f0f0',
                      position: 'relative',
                    }}
                    onMouseEnter={e => e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.2)'}
                    onMouseLeave={e => e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)'}
                    bodyStyle={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        padding: '10px 15px',
                    }}
                  >
                    <div style={{ position: 'absolute', top: 8, right: 8 }}>
                      <Dropdown
                        overlay={
                          <Menu>
                            <Menu.Item
                              key="delete"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={(info) => {
                                info.domEvent.stopPropagation();
                                handleDeleteProject(project.id, project.name);
                              }}
                            >
                              删除项目
                            </Menu.Item>
                          </Menu>
                        }
                        trigger={['click']}
                        placement="bottomRight"
                      >
                        <div onClick={e => e.stopPropagation()}>
                          <Button
                            icon={<MoreOutlined />}
                            type="text"
                            size="small"
                          />
                        </div>
                      </Dropdown>
                    </div>
                    <FolderOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: 10 }} />
                    <Tooltip title={project.name}>
                      <Title
                        level={4}
                        style={{
                          margin: 0,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          width: '100%',
                          padding: '0 5px',
                          color: '#424242'
                        }}
                      >
                        {project.name}
                      </Title>
                    </Tooltip>
                    <Text type="secondary" style={{ fontSize: 12, marginTop: 5 }}>创建于: {project.created_at}</Text>
                  </Card>
                ))
              ) : (
                (!Array.isArray(projects) || projects.length === 0) && !loadingProjects && (
                  <Empty description="暂无项目，快来创建第一个项目吧！" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )
              )}
            </div>
          </Spin>
        </Content>
      </Layout>
    );
  }

  // If a project is selected, display the main application interface
  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Top Header */}
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
          {/* --- 关键修改：将 Title 替换为 Image 并添加 onClick 事件 --- */}
          <img
            src="/edumind_logo.svg" // 图片路径，相对于 public 文件夹
            alt="EduMind Logo"
            style={{ height: '40px', marginRight: '20px', verticalAlign: 'middle', cursor: 'pointer' }} // 调整图片大小和位置，添加 pointer 样式
            onClick={() => navigate('/intro')} // 添加点击事件，导航到 ProjectIntroPage
          />
          {currentProject && (
            <Text strong style={{ fontSize: 18, marginRight: 20 }}>项目: {currentProject.name}</Text>
          )}
          <Search
            placeholder="全局搜索"
            onSearch={value => console.log('全局搜索:', value)}
            style={{ width: 300 }}
            allowClear
          />
        </div>
        <Space>
          <Button
            type="default"
            icon={<HomeOutlined />}
            onClick={() => {
              setCurrentProjectId(null);
              navigate('/');
            }}
          >
            返回项目列表
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelectedChatId(null);
              setMessages([]);
              setRelatedFileIds([]);
              setRelatedFilesMeta([]);
              notification.info({ message: '开始新的对话！' });
              setActivePane('chat');
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

      {/* Main Layout: Left Sider + Middle/Right Content */}
      <Layout style={{ flex: 1, minHeight: 0 }}>
        {/* Left Sider */}
        <Sider
          width={280}
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            overflowY: 'auto',
            minHeight: 0,
          }}
        >
          {/* Main Navigation Menu */}
          <Menu
            mode="inline"
            selectedKeys={[activePane]}
            onClick={e => setActivePane(e.key)}
            style={{ borderRight: 0, paddingBottom: 16 }}
          >
            <Menu.Item key="chat" icon={<MessageOutlined />}>对话历史</Menu.Item>
            <Menu.Item key="files" icon={<FileOutlined />}>我的文件</Menu.Item>
            <Menu.Item key="settings" icon={<SettingOutlined />}>应用设置</Menu.Item>
          </Menu>

          <Divider style={{ margin: '0 0 16px 0' }} />

          {/* File Upload Area */}
          <div style={{ padding: '0 16px 16px' }}>
            <Title level={5} style={{ marginTop: 0, marginBottom: 12, textAlign: 'center' }}>上传新文件</Title>
            <Form layout="vertical">
              <Form.Item label="文件类型">
                <Radio.Group
                  onChange={(e) => setUploadFileType(e.target.value)}
                  value={uploadFileType}
                  buttonStyle="solid"
                  style={{ width: '100%', marginBottom: 8 }}
                >
                  <Radio.Button value="textbook" style={{ flex: 1, textAlign: 'center' }}>教材</Radio.Button>
                  <Radio.Button value="question" style={{ flex: 1, textAlign: 'center' }}>题目</Radio.Button>
                </Radio.Group>
              </Form.Item>
              <Form.Item>
                <Upload
                  name="file"
                  action={`${BACKEND_BASE_URL}/projects/${currentProjectId}/upload`}
                  customRequest={handleUpload}
                  showUploadList={false}
                  multiple={false}
                  disabled={uploadingFile}
                >
                  <Button icon={<UploadOutlined />} block loading={uploadingFile}>
                    {uploadingFile ? '正在上传并处理...' : '选择并上传文件'}
                  </Button>
                </Upload>
              </Form.Item>
            </Form>
            <Text type="secondary" style={{ fontSize: '12px', marginTop: 0, display: 'block', textAlign: 'center' }}>当前主要支持PDF文件（进行结构化处理）</Text>
          </div>

          <Divider style={{ margin: '0 0 16px 0' }} />

          {/* Left Sider bottom content based on activePane */}
          <div style={{ padding: '0 16px 16px' }}>
            {activePane === 'files' && (
              <Spin spinning={loadingFiles}>
                <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>我的文件</Title>
                <Button block onClick={fetchFiles} style={{ marginBottom: 10 }}>刷新文件列表</Button>
                <List
                  dataSource={Array.isArray(files) ? files : []}
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
                        title={<Text onClick={() => console.log('Click file:', file.name)}>{file.name}</Text>}
                        description={
                          <Text type="secondary">
                            {file.size} - {file.uploadDate} (类型: {file.type || '未知'})
                            {file.file_type_tag === 'textbook' && (
                              file.is_processed ? <Tag color="green" style={{ marginLeft: 8 }}>已处理</Tag> : <Tag color="orange" style={{ marginLeft: 8 }}>处理中</Tag>
                            )}
                            {file.file_type_tag === 'question' && (
                              <Tag color="blue" style={{ marginLeft: 8 }}>题目</Tag>
                            )}
                          </Text>
                        }
                      />
                    </List.Item>
                  )}
                />
                {(!Array.isArray(files) || files.length === 0) && !loadingFiles && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文件" style={{ marginTop: 50 }} />}
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
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="在右侧管理应用设置" style={{ marginTop: 50 }} />
            )}
          </div>
        </Sider>

        {/* Middle Main Content Area (LLM Chat) */}
        <Content style={{ display: 'flex', flexGrow: 1 }}>
          <div style={{
            flex: 1,
            background: '#f9f9f9',
            borderRight: '1px solid #e0e0e0',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}>
            {/* Chat Title and Linked Documents Display */}
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e0e0e0', background: '#fff' }}>
              <Title level={4} style={{ margin: 0 }}>
                {currentChatTitle}
                <Tooltip title="导出当前对话为DOCX文件">
                  <Button
                    icon={<DownloadOutlined />}
                    type="text"
                    style={{ marginLeft: 10 }}
                    onClick={handleExportChat}
                  />
                </Tooltip>
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
                                  {file.is_processed ? <Tag color="green" style={{ marginLeft: 4 }} size="small">已处理</Tag> : <Tag color="orange" style={{ marginLeft: 4 }} size="small">处理中</Tag>}
                                  {file.file_type_tag === 'question' && <Tag color="blue" style={{ marginLeft: 4 }} size="small">题目</Tag>}
                              </Tag>
                          ))}
                      </Space>
                  </div>
              )}
            </div>
            {/* Message Display Area - ensure it scrolls internally */}
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
                <div ref={messagesEndRef} />
              </Spin>
            </div>

            {/* Input Area */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid #e0e0e0', background: '#fff' }}>
              <TextArea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="输入您的问题..."
                autoSize={{ minRows: 2, maxRows: 6 }}
                onPressEnter={(e) => {
                  if (e.shiftKey) {
                    // Do nothing, let default behavior handle newline
                  } else {
                    e.preventDefault();
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

          {/* Right Function/Tool Area - renders different content based on activePane, always shows templates button */}
          <div style={{
            flex: '0 0 350px',
            background: '#fff',
            padding: '24px',
            overflowY: 'auto',
            borderLeft: '1px solid #e0e0e0',
            minHeight: 0,
          }}>
            {/* Always visible General Tools Button */}
            <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>通用工具</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<RobotOutlined />}
                onClick={() => setIsTemplatesModalVisible(true)}
              >
                答题方法与模板
              </Button>
              <Button
                block
                icon={<BarChartOutlined />}
                onClick={() => {
                  setIsDashboardModalVisible(true);
                  setMindMapImageSrc(null); // 清除旧的图片路径，以便在打开模态框时先显示Empty
                  setSelectedFileForMindMap(null);
                  setMindMapError(null);
                }}
              >
                仪表盘
              </Button>
            </Space>
            <Divider />

            {/* Chat Mode Settings */}
            {activePane === 'chat' && (
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
            )}

            {/* File Mode and Settings Mode General Hints */}
            {(activePane === 'files' || activePane === 'settings') && (
              <>
                <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>辅助信息</Title>
                <Empty description="请在左侧选择对应功能菜单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </>
            )}
          </div>
        </Content>
      </Layout>

      {/* File Preview Modal */}
      <Modal
        title={currentPreviewFile ? `预览: ${currentPreviewFile.name}` : '文件预览'}
        open={isPreviewModalVisible}
        onCancel={handlePreviewModalClose}
        footer={[
          currentPreviewFile && (previewFileContent === 'UNSUPPORTED_PREVIEW' || previewFileContent === 'ERROR_LOADING_PREVIEW') && (
            <Button
              key="download"
              type="primary"
              href={`${BACKEND_BASE_URL.replace('/api', '')}/uploads/${currentProjectId}/${currentPreviewFile.processed_dir_name}/${currentPreviewFile.name}`}
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
                <img src={previewFileContent} alt="File preview" style={{ maxWidth: '100%', display: 'block', margin: '0 auto' }} />
              ) : currentPreviewFile.type === 'pdf' ? (
                <iframe
                  src={previewFileContent}
                  title="PDF File Preview"
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

      {/* Citation Detail Modal */}
      <Modal
          title={currentCitationTitle}
          open={isCitationModalVisible}
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

      {/* Answer Method & Template Modal */}
      <Modal
        title="答题方法与出题模板"
        open={isTemplatesModalVisible}
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
                {Array.isArray(files) && files.map(file => (
                  <Option key={file.id} value={file.id}>
                    {file.name} (类型: {file.file_type_tag || '未知'})
                    {file.is_processed ? <Tag color="green" style={{ marginLeft: 8 }} size="small">已处理</Tag> : <Tag color="orange" style={{ marginLeft: 8 }} size="small">处理中</Tag>}
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
                      icon={copiedIndex === item.id || copiedIndex === index ? <CheckOutlined style={{ color: 'green' }} /> : <CopyOutlined />}
                      size="small"
                      onClick={() => handleCopy(item.answer_method, item.id || index)}
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
                {Array.isArray(templatesMethods) && templatesMethods.map((item, index) => (
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

      {/* New: Dashboard/Mind Map Modal */}
      <Modal
        title="仪表盘 - 思维导图"
        open={isDashboardModalVisible}
        onCancel={() => setIsDashboardModalVisible(false)}
        footer={null}
        width={900}
        bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
      >
        <Spin spinning={loadingMindMap}>
          <Form layout="vertical">
            <Form.Item label="选择文件 (仅教材):">
              <Select
                placeholder="选择一个教材文件（仅用于触发显示）"
                value={selectedFileForMindMap}
                onChange={setSelectedFileForMindMap}
                style={{ width: '100%' }}
              >
                {files.filter(f => f.file_type_tag === 'textbook').map(file => (
                  <Option key={file.id} value={file.id}>
                    {file.name} {file.is_processed ? '(已处理)' : '(未处理)'}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                onClick={handleGenerateMindMapTrigger} // 触发显示图片
                loading={loadingMindMap}
                block
                disabled={!selectedFileForMindMap}
              >
                生成思维导图
              </Button>
            </Form.Item>
          </Form>

          <Divider orientation="left" style={{ margin: '16px 0' }}>生成的思维导图</Divider>
          {mindMapError && (
            <Alert message="错误" description={mindMapError} type="error" showIcon style={{ marginBottom: 15 }} />
          )}
          {/* 关键修改：根据 mindMapImageSrc 状态渲染图片 */}
          {mindMapImageSrc ? ( // 如果 mindMapImageSrc 不为 null，则显示图片
            <div style={{
              height: '500px',
              width: '100%',
              overflow: 'auto',
              display: 'flex', /* 使图片居中 */
              justifyContent: 'center', /* 使图片水平居中 */
              alignItems: 'center', /* 使图片垂直居中 */
              border: '1px solid #d9d9d9',
              background: '#f8f8f8', /* 设置一个背景色，防止图片是透明的 */
            }}>
              <img
                src={mindMapImageSrc} // 使用 mindMapImageSrc 动态加载图片
                alt="思维导图"
                style={{
                  maxWidth: '100%',   // 确保图片宽度不超过容器
                  maxHeight: '100%',  // 确保图片高度不超过容器
                  objectFit: 'contain' // 保持图片比例，适应容器
                }}
              />
            </div>
          ) : (
            // 否则显示 Empty 提示
            !loadingMindMap && !mindMapError && <Empty description="选择文件以生成思维导图。" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Modal>
    </Layout>
  );
}

export default App;