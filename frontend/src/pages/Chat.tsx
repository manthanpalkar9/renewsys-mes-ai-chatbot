import { useState, useRef, useEffect } from 'react';
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
