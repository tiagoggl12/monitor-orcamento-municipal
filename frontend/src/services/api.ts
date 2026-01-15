// ====================================
// API Service - Cliente HTTP
// ====================================

import axios from 'axios';
import type {
  Municipality,
  ChatSession,
  Message,
  GeminiResponse,
  Document,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4001/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutos (para uploads grandes)
  maxRedirects: 5, // Seguir redirects automaticamente
});

// Interceptor para logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data || config.params || '');
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.config.url}:`, response.status, response.data);
    return response;
  },
  (error) => {
    console.error('[API] Response error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data
    });
    return Promise.reject(error);
  }
);

// ====================================
// Municipalities
// ====================================

export const municipalitiesApi = {
  listStates: async (): Promise<string[]> => {
    const response = await api.get('/municipalities/states');
    return response.data;
  },

  list: async (state?: string): Promise<Municipality[]> => {
    const params = state ? { state } : {};
    const response = await api.get('/municipalities/', { params });
    return response.data;
  },

  get: async (id: number): Promise<Municipality> => {
    const response = await api.get(`/municipalities/${id}`);
    return response.data;
  },

  create: async (data: {
    name: string;
    state: string;
    year: number;
  }): Promise<Municipality> => {
    const response = await api.post('/municipalities', data);
    return response.data;
  },

  search: async (query: string): Promise<Municipality[]> => {
    const response = await api.get('/municipalities/search', {
      params: { q: query },
    });
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/municipalities/${id}`);
  },
};

// ====================================
// Chat Sessions
// ====================================

export const chatApi = {
  createSession: async (data: {
    municipality_id: string; // UUID
    title?: string;
  }): Promise<ChatSession> => {
    const response = await api.post('/chat/sessions', data);
    return response.data;
  },

  listSessions: async (municipalityId?: string): Promise<ChatSession[]> => {
    const params = municipalityId ? { municipality_id: municipalityId } : {};
    const response = await api.get('/chat/sessions', { params });
    return response.data;
  },

  getSession: async (id: number): Promise<ChatSession> => {
    const response = await api.get(`/chat/sessions/${id}`);
    return response.data;
  },

  deleteSession: async (id: number): Promise<void> => {
    await api.delete(`/chat/sessions/${id}`);
  },

  sendMessage: async (
    sessionId: number,
    question: string
  ): Promise<GeminiResponse> => {
    const response = await api.post(`/chat/sessions/${sessionId}/messages`, {
      question,
    });
    return response.data;
  },

  getMessages: async (sessionId: number): Promise<Message[]> => {
    const response = await api.get(`/chat/sessions/${sessionId}/messages`);
    return response.data;
  },

  getSessionSummary: async (sessionId: number): Promise<any> => {
    const response = await api.get(`/chat/sessions/${sessionId}/summary`);
    return response.data;
  },
};

// ====================================
// Documents
// ====================================

export const documentsApi = {
  upload: async (
    file: File,
    municipalityId: string, // UUID
    documentType: 'loa' | 'ldo',
    year: number
  ): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('municipality_id', municipalityId.toString());
    formData.append('document_type', documentType);
    formData.append('year', year.toString());

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (municipalityId?: string): Promise<Document[]> => {
    const params = municipalityId ? { municipality_id: municipalityId } : {};
    const response = await api.get('/documents', { params });
    return response.data;
  },

  getStatus: async (id: number): Promise<Document> => {
    const response = await api.get(`/documents/${id}/status`);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },

  reprocess: async (id: number): Promise<void> => {
    await api.post(`/documents/${id}/reprocess`);
  },
};

// ====================================
// Portal da Transparência
// ====================================

export const portalApi = {
  listPackages: async (): Promise<{ packages: string[]; total: number }> => {
    const response = await api.get('/portal/packages');
    return response.data;
  },

  searchPackages: async (query: string, rows: number = 10): Promise<any> => {
    const response = await api.post('/portal/packages/search', {
      query,
      rows,
    });
    return response.data;
  },

  getPackage: async (packageId: string): Promise<any> => {
    const response = await api.get(`/portal/packages/${packageId}`);
    return response.data;
  },
};

// ====================================
// Health Check
// ====================================

export const healthApi = {
  check: async (): Promise<any> => {
    const response = await api.get('/health');
    return response.data;
  },
};

// ====================================
// Dashboard LOA/LDO
// ====================================

export interface ExercicioListItem {
  id: string;
  ano: number;
  municipio: string;
  tipo_documento: string;
  orcamento_total: number;
  processado_em: string;
}

export interface VisaoGeralData {
  ano: number;
  municipio: string;
  tipo_documento: string;
  prefeito: string | null;
  orcamento_total: number;
  orcamento_fiscal: number;
  orcamento_seguridade: number;
  limite_suplementacao: number | null;
  variacao_ano_anterior: number | null;
  top_orgaos: Array<{
    codigo: string;
    nome: string;
    sigla: string | null;
    valor: number;
  }>;
  principais_programas: Array<{
    codigo: string;
    nome: string;
    valor_total: number;
    valor_fiscal: number;
    valor_seguridade: number;
    percentual_fiscal: number;
    percentual_seguridade: number;
  }>;
}

export interface ReceitasData {
  ano: number;
  receitas_correntes_total: number;
  receitas_capital_total: number;
  receitas_correntes: Array<{
    categoria: string;
    codigo: string | null;
    valor: number;
    descricao_popular: string | null;
  }>;
  receitas_capital: Array<{
    categoria: string;
    codigo: string | null;
    valor: number;
    descricao_popular: string | null;
  }>;
  serie_historica: Array<{ ano: number; valor: number }>;
}

export interface DespesasData {
  ano: number;
  despesa_total: number;
  por_categoria: Array<{
    categoria: string;
    codigo: string | null;
    valor_total: number;
    valor_fiscal: number;
    valor_seguridade: number;
  }>;
  programas: Array<{
    codigo: string;
    nome: string;
    objetivo: string | null;
    valor_total: number;
    valor_fiscal: number;
    valor_seguridade: number;
    percentual_fiscal: number;
    percentual_seguridade: number;
    orgao_responsavel: string | null;
  }>;
}

export interface InvestimentoRegionalData {
  ano: number;
  total_regionais: number;
  regionais: Array<{
    numero: number;
    nome: string | null;
    valor: number;
    bairros: string[];
    destaques: Array<{
      categoria: string;
      nome: string;
      descricao: string;
      prioridade: string;
      valor: number;
    }>;
  }>;
}

export interface ParticipacaoSocialData {
  ano: number;
  foruns_realizados: number;
  temas_chave: number;
  total_priorizado: number;
  rastreabilidade: number;
  descricao: string | null;
  iniciativas: Array<{
    nome: string;
    valor: number;
    descricao: string;
    categoria: string;
  }>;
}

export interface LimitesConstitucionaisData {
  ano: number;
  educacao: {
    minimo: number;
    previsto: number | null;
    valor: number | null;
    cumprindo: boolean | null;
  };
  saude: {
    minimo: number;
    previsto: number | null;
    valor: number | null;
    cumprindo: boolean | null;
  };
  pessoal: {
    limite: number;
    previsto: number | null;
    valor: number | null;
    dentro_limite: boolean | null;
  };
}

export const dashboardApi = {
  listExercicios: async (municipio: string = 'Fortaleza'): Promise<ExercicioListItem[]> => {
    const response = await api.get('/dashboard/exercicios', { params: { municipio } });
    return response.data;
  },

  getVisaoGeral: async (ano: number, municipio: string = 'Fortaleza'): Promise<VisaoGeralData> => {
    const response = await api.get(`/dashboard/visao-geral/${ano}`, { params: { municipio } });
    return response.data;
  },

  getReceitas: async (ano: number, municipio: string = 'Fortaleza'): Promise<ReceitasData> => {
    const response = await api.get(`/dashboard/receitas/${ano}`, { params: { municipio } });
    return response.data;
  },

  getDespesas: async (ano: number, municipio: string = 'Fortaleza'): Promise<DespesasData> => {
    const response = await api.get(`/dashboard/despesas/${ano}`, { params: { municipio } });
    return response.data;
  },

  getInvestimentoRegional: async (ano: number, municipio: string = 'Fortaleza'): Promise<InvestimentoRegionalData> => {
    const response = await api.get(`/dashboard/investimento-regional/${ano}`, { params: { municipio } });
    return response.data;
  },

  getParticipacaoSocial: async (ano: number, municipio: string = 'Fortaleza'): Promise<ParticipacaoSocialData> => {
    const response = await api.get(`/dashboard/participacao-social/${ano}`, { params: { municipio } });
    return response.data;
  },

  getLimitesConstitucionais: async (ano: number, municipio: string = 'Fortaleza'): Promise<LimitesConstitucionaisData> => {
    const response = await api.get(`/dashboard/limites-constitucionais/${ano}`, { params: { municipio } });
    return response.data;
  },

  processarDocumento: async (file: File, municipio: string = 'Fortaleza'): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('municipio', municipio);
    const response = await api.post('/dashboard/processar-documento', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

// ====================================
// API de LDO
// ====================================

import type {
  ExercicioLDO,
  MetasPrioridadesData,
  MetasFiscaisData,
  RiscosFiscaisData,
  PoliticasSetoriaisData
} from '../types';

export const ldoApi = {
  listExercicios: async (municipio: string = 'Fortaleza'): Promise<ExercicioLDO[]> => {
    const response = await api.get('/ldo/exercicios', { params: { municipio } });
    return response.data;
  },

  getMetasPrioridades: async (ano: number, municipio: string = 'Fortaleza'): Promise<MetasPrioridadesData> => {
    const response = await api.get(`/ldo/metas-prioridades/${ano}`, { params: { municipio } });
    return response.data;
  },

  getMetasFiscais: async (ano: number, municipio: string = 'Fortaleza'): Promise<MetasFiscaisData> => {
    const response = await api.get(`/ldo/metas-fiscais/${ano}`, { params: { municipio } });
    return response.data;
  },

  getRiscosFiscais: async (ano: number, municipio: string = 'Fortaleza'): Promise<RiscosFiscaisData> => {
    const response = await api.get(`/ldo/riscos-fiscais/${ano}`, { params: { municipio } });
    return response.data;
  },

  getPoliticasSetoriais: async (ano: number, municipio: string = 'Fortaleza'): Promise<PoliticasSetoriaisData> => {
    const response = await api.get(`/ldo/politicas-setoriais/${ano}`, { params: { municipio } });
    return response.data;
  },

  getConsolidado: async (ano: number, municipio: string = 'Fortaleza'): Promise<any> => {
    const response = await api.get(`/ldo/consolidado/${ano}`, { params: { municipio } });
    return response.data;
  },
};

export default api;

