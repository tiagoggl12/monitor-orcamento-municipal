import { useState, useEffect, useRef } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { chatApi, municipalitiesApi } from '../services/api';
import type { ChatSession, Municipality, Component } from '../types';
import ComponentRenderer from './ComponentRenderer';

export default function ChatPage() {
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [selectedMunicipality, setSelectedMunicipality] = useState<string>('');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; components?: Component[]; content?: string }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadMunicipalities();
  }, []);

  useEffect(() => {
    if (selectedMunicipality) {
      loadSessions();
    }
  }, [selectedMunicipality]);

  useEffect(() => {
    if (currentSession) {
      loadMessages();
    }
  }, [currentSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadMunicipalities = async () => {
    try {
      const data = await municipalitiesApi.list();
      setMunicipalities(data);
      
      // Selecionar Fortaleza-CE por padrão
      if (data.length > 0 && !selectedMunicipality) {
        const fortaleza = data.find(m => 
          m.name.toLowerCase().includes('fortaleza') && 
          m.state.toUpperCase() === 'CE'
        );
        setSelectedMunicipality(fortaleza ? fortaleza.id : data[0].id);
      }
    } catch (error) {
      console.error('Erro ao carregar municípios:', error);
    }
  };

  const loadSessions = async () => {
    if (!selectedMunicipality) return;
    try {
      const data = await chatApi.listSessions(selectedMunicipality);
      setSessions(data);
    } catch (error) {
      console.error('Erro ao carregar sessões:', error);
    }
  };

  const loadMessages = async () => {
    if (!currentSession) return;
    try {
      const data = await chatApi.getMessages(currentSession.id);
      const formattedMessages = data.map((msg) => ({
        role: msg.role,
        content: msg.role === 'user' ? msg.content : undefined,
        components: msg.role === 'assistant' ? JSON.parse(msg.content).response.components : undefined,
      }));
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error);
    }
  };

  const createNewSession = async () => {
    if (!selectedMunicipality) return;
    try {
      const session = await chatApi.createSession({
        municipality_id: selectedMunicipality,
        title: `Chat - ${new Date().toLocaleString('pt-BR')}`,
      });
      setSessions([session, ...sessions]);
      setCurrentSession(session);
      setMessages([]);
    } catch (error) {
      console.error('Erro ao criar sessão:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !currentSession || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatApi.sendMessage(currentSession.id, input);
      const assistantMessage = {
        role: 'assistant',
        components: response.response.components,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          components: [{
            type: 'alert' as const,
            level: 'error' as const,
            message: 'Erro ao processar mensagem. Tente novamente.',
          }],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* Sidebar */}
      <div className="w-80 bg-white rounded-lg shadow p-4 flex flex-col">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Município
          </label>
          <select
            value={selectedMunicipality}
            onChange={(e) => setSelectedMunicipality(e.target.value)}
            className="input-field"
          >
            <option value="">Selecione um município</option>
            {municipalities.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} - {m.state} ({m.year})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={createNewSession}
          className="btn-primary mb-4"
          disabled={!selectedMunicipality}
        >
          Nova Conversa
        </button>

        <div className="flex-1 overflow-y-auto">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Conversas</h3>
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setCurrentSession(session)}
              className={`w-full text-left p-3 rounded-lg mb-2 transition-colors ${
                currentSession?.id === session.id
                  ? 'bg-primary-100 text-primary-700'
                  : 'hover:bg-gray-100'
              }`}
            >
              <div className="text-sm font-medium truncate">{session.title}</div>
              <div className="text-xs text-gray-500">{session.message_count} mensagens</div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 bg-white rounded-lg shadow flex flex-col">
        {currentSession ? (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'user' ? (
                    <div className="bg-primary-600 text-white rounded-lg px-4 py-2 max-w-2xl">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="max-w-4xl w-full space-y-4">
                      {msg.components?.map((component, cidx) => (
                        <ComponentRenderer key={cidx} component={component} />
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-2">
                    <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-gray-200 p-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                  placeholder="Digite sua pergunta..."
                  className="input-field"
                  disabled={loading}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  className="btn-primary"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Selecione ou crie uma conversa para começar
          </div>
        )}
      </div>
    </div>
  );
}

