import os

project_root = r'C:\Users\manth\Desktop\renewsys project\Project\frontend'

files = {
    'tailwind.config.js': '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
''',

    'postcss.config.js': '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
''',

    r'src\index.css': '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900;
  }
}
''',

    r'src\main.tsx': '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { BrowserRouter } from 'react-router-dom'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
''',

    r'src\lib\api.ts': '''import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080/api/v1',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
''',

    r'src\App.tsx': '''import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
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
''',

    r'src\pages\Login.tsx': '''import { useState } from 'react';
import api from '../lib/api';
import { useNavigate } from 'react-router-dom';

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post('/auth/login', { username, password });
      localStorage.setItem('token', res.data.access_token);
      onLogin();
      navigate('/');
    } catch (err) {
      setError('Invalid username or password');
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center text-blue-900">Sign In</h2>
        {error && <div className="bg-red-50 text-red-600 p-3 rounded mb-4 text-sm">{error}</div>}
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>
          <button 
            type="submit" 
            className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700 transition font-medium"
          >
            Login
          </button>
        </form>
        
        <div className="mt-4 text-sm text-gray-500 text-center">
          Default Admin: <strong>admin</strong> / <strong>admin123!</strong>
        </div>
      </div>
    </div>
  );
}
''',

    r'src\pages\Chat.tsx': '''import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import api from '../lib/api';
import KPICardRenderer from '../components/KPICardRenderer';
import TableRenderer from '../components/TableRenderer';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  responseType?: 'text' | 'table' | 'kpi_card' | 'chart' | 'error' | 'clarification';
  kpiData?: any;
  tableData?: any;
  sql?: string;
}

export default function Chat({ user }: { user: any }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.post('/chat/session').then(res => setSessionId(res.data.session_id));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await api.post('/chat/message', { session_id: sessionId, message: userMsg });
      const data = res.data;
      
      setMessages(prev => [...prev, {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        responseType: data.response_type,
        kpiData: data.kpi_card,
        tableData: data.table,
        sql: data.generated_sql
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        id: Date.now().toString(), 
        role: 'assistant', 
        content: 'Failed to connect to the server.', 
        responseType: 'error' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full relative bg-gray-50">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <h3 className="text-xl font-medium mb-2 text-gray-500">How can I help you today?</h3>
              <p className="text-sm">Ask about production, yield, downtime, or specific line data.</p>
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-4 shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200'}`}>
              
              <div className={msg.role === 'user' ? 'text-white' : 'text-gray-800'}>
                {msg.content}
              </div>

              {msg.responseType === 'kpi_card' && msg.kpiData && (
                <div className="mt-4">
                  <KPICardRenderer data={msg.kpiData} />
                </div>
              )}

              {msg.responseType === 'table' && msg.tableData && (
                <div className="mt-4">
                  <TableRenderer data={msg.tableData} />
                </div>
              )}

              {msg.sql && user?.role === 'admin' && (
                <div className="mt-4 bg-gray-100 p-3 rounded-md text-xs font-mono text-gray-600 border border-gray-200 overflow-x-auto">
                  <div className="font-semibold mb-1 text-gray-500">Generated SQL:</div>
                  {msg.sql}
                </div>
              )}

            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex items-center space-x-2 text-gray-500">
              <Loader2 className="animate-spin" size={16} />
              <span>Analyzing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center"
          >
            <Send size={20} />
          </button>
        </form>
        <div className="text-center text-xs text-gray-400 mt-2">
          Phase 1 is strictly Read-Only. Data may be delayed by up to 24 hours.
        </div>
      </div>
    </div>
  );
}
''',

    r'src\components\KPICardRenderer.tsx': '''import { AlertCircle } from 'lucide-react';

export default function KPICardRenderer({ data }: { data: any }) {
  if (!data) return null;

  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 flex flex-col min-w-[200px]">
      <div className="text-sm font-medium text-blue-800 uppercase tracking-wide">
        {data.kpi_name}
      </div>
      <div className="mt-2 flex items-baseline">
        <span className="text-3xl font-bold text-blue-900">
          {data.value !== null ? data.value : 'N/A'}
        </span>
        {data.unit && (
          <span className="ml-1 text-sm font-medium text-blue-700">{data.unit}</span>
        )}
      </div>
      
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-blue-700">
        {data.line && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Line: {data.line}</span>}
        {data.shift && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Shift: {data.shift}</span>}
        {data.period && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Period: {data.period}</span>}
      </div>

      {!data.is_formula_confirmed && (
        <div className="mt-4 flex items-start space-x-2 text-xs text-orange-700 bg-orange-50 p-2 rounded border border-orange-200">
          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
          <span>{data.formula_note}</span>
        </div>
      )}
    </div>
  );
}
''',

    r'src\components\TableRenderer.tsx': '''export default function TableRenderer({ data }: { data: any }) {
  if (!data || !data.columns || !data.rows) return null;

  return (
    <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {data.columns.map((col: string, i: number) => (
              <th key={i} className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.rows.map((row: any[], i: number) => (
            <tr key={i} className="hover:bg-gray-50">
              {row.map((cell: any, j: number) => (
                <td key={j} className="px-4 py-3 text-gray-700 whitespace-nowrap">
                  {cell !== null ? cell.toString() : '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.total_rows > data.rows.length && (
        <div className="p-3 text-center text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
          Showing {data.rows.length} of {data.total_rows} rows.
        </div>
      )}
    </div>
  );
}
'''
}

for path, content in files.items():
    full_path = os.path.join(project_root, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print('All frontend files written successfully.')
