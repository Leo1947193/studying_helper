// src/pages/ProjectIntroPage.js
import React, { useState } from 'react'; // 导入 useState
import { Layout, Typography, Button, Space, Card, Row, Col, Divider, Flex, Modal } from 'antd'; // 导入 Modal
import { GithubOutlined, PlayCircleOutlined, StarOutlined, UsergroupAddOutlined } from '@ant-design/icons';
import './ProjectIntroPage.css';

const { Content } = Layout;
const { Title, Paragraph, Text } = Typography;

const ProjectIntroPage = () => {
  const [isModalVisible, setIsModalVisible] = useState(false); // 控制模态框可见性的状态

  const showModal = () => {
    setIsModalVisible(true);
  };

  const handleOk = () => {
    setIsModalVisible(false);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
  };

  // 假设你的报名链接
  const registrationLink = 'https://ocn15vvrvzl0.feishu.cn/share/base/form/shrcnKHnpgnlEQ33920tOnmB82c';

  return (
    <Layout className="project-intro-layout">
      <Content className="project-intro-content">
        {/* 头部区域 - 项目名称与Slogan */}
        <div className="hero-section">
          <Title level={1} className="project-title">智学引擎（EduMind）</Title>
          <Paragraph className="project-slogan">AI驱动的教育知识图谱与自适应学习平台</Paragraph>
          <Space size="large" className="hero-buttons">
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              href="https://example.com/demo-video" // 替换为你的演示视频链接
              target="_blank"
            >
              观看演示
            </Button>
            <Button
              size="large"
              icon={<UsergroupAddOutlined />}
              onClick={showModal} // 点击后显示模态框
              // 移除 href="#"
            >
              招募用户
            </Button>
            <Button
              size="large"
              icon={<GithubOutlined />}
              href="https://github.com/your-repo" // 替换为你的GitHub仓库链接
              target="_blank"
            >
              GitHub
            </Button>
            <Button
              size="large"
              icon={<StarOutlined />}
              href="https://github.com/your-repo/star" // 替换为你的GitHub Star链接
              target="_blank"
            >
              Star Us!
            </Button>
          </Space>
        </div>

        <Divider />

        {/* 核心亮点 */}
        <div className="section">
          <Title level={2} className="section-title">核心亮点</Title>
          <Row gutter={[32, 32]} justify="center">
            <Col xs={24} md={8}>
              <Card
                hoverable
                className="feature-card"
                title={<Title level={4}>知识图谱与思维导图</Title>}
              >
                <Paragraph>
                  将教材内容转化为网状知识结构，支持交互式浏览，助力学生构建完整知识体系，实现从宏观到微观的探索式学习。
                </Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                hoverable
                className="feature-card"
                title={<Title level={4}>智能出题与批改</Title>}
              >
                <Paragraph>
                  基于AI生成个性化试卷，并对学生答案进行语义批改，提供精准反馈，大幅提升教师备课效率，减轻学生无效刷题负担。
                </Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                hoverable
                className="feature-card"
                title={<Title level={4}>RAG 智能问答</Title>}
              >
                <Paragraph>
                  结合检索增强生成（RAG）技术，提供可追溯、有依据的智能问答服务，解答学生疑问并链接至原始知识点。
                </Paragraph>
              </Card>
            </Col>
          </Row>
        </div>

        <Divider />

        {/* 创新与价值 */}
        <div className="section">
          <Title level={2} className="section-title">创新与价值</Title>
          <Flex wrap="wrap" justify="space-around" align="flex-start" className="value-props">
            <Card hoverable className="value-card">
              <Title level={5}>推动教育公平</Title>
              <Paragraph>弥合地域鸿沟，让偏远地区学生也能获取优质教学资源与命题逻辑分析。</Paragraph>
            </Card>
            <Card hoverable className="value-card">
              <Title level={5}>革新学习模式</Title>
              <Paragraph>从“机械刷题”转向“深度学习”，培养学生的批判性思维与元认知能力。</Paragraph>
            </Card>
            <Card hoverable className="value-card">
              <Title level={5}>升级教师角色</Title>
              <Paragraph>教师从“知识传授”转型为“学习设计师”，聚焦设计项目式学习与跨学科教学。</Paragraph>
            </Card>
            <Card hoverable className="value-card">
              <Title level={5}>四维能力培养</Title>
              <Paragraph>学、练、考、创一体化闭环，鼓励用户从使用者升级为内容生产者。</Paragraph>
            </Card>
          </Flex>
        </div>

        <Divider />

        {/* 项目团队 */}
        <div className="section">
          <Title level={2} className="section-title">项目团队</Title>
          <Row justify="center" gutter={[16, 16]}>
            <Col>
              <Text strong>EduMind 项目组</Text>
            </Col>
            <Col>
              <Text>李俊尧</Text> <Text type="secondary">(大数据与新闻传播 - OCR分段翻译，Embedding)</Text>
            </Col>
            <Col>
              <Text>蔡子奇</Text> <Text type="secondary">(数字经济 - 项目规划，Prompt)</Text>
            </Col>
            <Col>
              <Text>方丁龙</Text> <Text type="secondary">(智能科学与技术 - 项目策划，题目相似度搜索)</Text>
            </Col>
          </Row>
        </div>

        <Divider />

        {/* Beta 招募提示 */}
        <div className="beta-section">
          <Title level={3}>加入我们，共创未来！</Title>
          <Paragraph>
            EduMind 项目目前处于 <Text strong>Beta</Text> 阶段，我们正在积极招募用户，期待您的加入！
          </Paragraph>
          <Button
            type="primary"
            size="large"
            icon={<UsergroupAddOutlined />}
            onClick={showModal} // 点击后显示模态框
            // 移除 href="#"
          >
            立即报名 Beta 体验
          </Button>
        </div>

        {/* 报名链接模态框 */}
        <Modal
          title="Beta 用户招募"
          open={isModalVisible} // 使用 open 属性控制可见性
          onOk={handleOk}
          onCancel={handleCancel}
          footer={[
            <Button key="close" onClick={handleCancel}>关闭</Button>,
            <Button key="register" type="primary" href={registrationLink} target="_blank">
              前往报名
            </Button>,
          ]}
        >
          <Paragraph>感谢您对 EduMind 的兴趣！</Paragraph>
          <Paragraph>请点击下方链接进行 Beta 用户报名：</Paragraph>
          <Paragraph strong>
            <a href={registrationLink} target="_blank" rel="noopener noreferrer">
              {registrationLink}
            </a>
          </Paragraph>
          <Paragraph type="secondary">复制链接到浏览器打开，或点击“前往报名”按钮。</Paragraph>
        </Modal>
      </Content>
    </Layout>
  );
};

export default ProjectIntroPage;