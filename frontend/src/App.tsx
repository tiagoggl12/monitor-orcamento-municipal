import { useState } from 'react';
import Layout from './components/Layout';
import ChatPage from './components/ChatPage';
import UploadPage from './components/UploadPage';
import PortalIngestPage from './components/PortalIngestPage';
import DashboardPage from './components/dashboard/DashboardPage';
import LDOPage from './components/ldo/LDOPage';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'ldo':
        return <LDOPage />;
      case 'chat':
        return <ChatPage />;
      case 'documents':
        return (
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">Documentos</h2>
            <p className="text-gray-600">
              Lista de documentos LOA e LDO processados.
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Em desenvolvimento...
            </p>
          </div>
        );
      case 'upload':
        return <UploadPage />;
      case 'portal':
        return <PortalIngestPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <Layout currentPage={currentPage} onPageChange={setCurrentPage}>
      {renderPage()}
    </Layout>
  );
}

export default App;
