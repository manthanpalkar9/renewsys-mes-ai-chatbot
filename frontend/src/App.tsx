import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from './lib/api';
import Login from './pages/Login';
import Chat from './pages/Chat';
import { LogOut, Settings } from 'lucide-react';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!localStorage.getItem('token'));
  const [user, setUser] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      api.get('/auth/me')
        .then(res => setUser(res.data))
        .catch(() => handleLogout());
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {isAuthenticated && (
        <header className="bg-white shadow-sm border-b px-6 py-3 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-blue-900">Renewsys MES AI Chatbot</h1>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              {user?.username} ({user?.role})
            </span>
            {user?.role === 'admin' && (
              <button className="p-2 text-gray-500 hover:text-gray-900" title="Admin Settings">
                <Settings size={20} />
              </button>
            )}
            <button onClick={handleLogout} className="p-2 text-gray-500 hover:text-red-600" title="Logout">
              <LogOut size={20} />
            </button>
          </div>
        </header>
      )}

      <main className="flex-1 overflow-hidden flex flex-col">
        <Routes>
          <Route path="/login" element={
            !isAuthenticated ? <Login onLogin={() => setIsAuthenticated(true)} /> : <Navigate to="/" />
          } />
          <Route path="/" element={
            isAuthenticated ? <Chat user={user} /> : <Navigate to="/login" />
          } />
        </Routes>
      </main>
    </div>
  );
}
