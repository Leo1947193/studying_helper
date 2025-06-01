// src/components/Modals/CitationDetailModal.js
import React from 'react';
import { Modal, Button, Input } from 'antd';

function CitationDetailModal({
  isCitationModalVisible,
  setIsCitationModalVisible,
  currentCitationContent,
  currentCitationTitle,
}) {
  return (
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
  );
}

export default CitationDetailModal;