// ====================================
// Types para a aplicação
// ====================================

export interface Municipality {
  id: string; // UUID
  name: string;
  state: string;
  year: number;
  created_at: string;
}

export interface ChatSession {
  id: number;
  municipality_id: string; // UUID
  title: string;
  created_at: string;
  message_count: number;
}

export interface Message {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// Componentes visuais
export interface TextComponent {
  type: 'text';
  content: string;
}

export interface MetricComponent {
  type: 'metric';
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export interface ChartComponent {
  type: 'chart';
  chart_type: 'bar' | 'line' | 'pie' | 'area';
  title: string;
  // Formato Recharts - array de objetos
  data: Array<Record<string, any>>;
  x_key?: string; // Chave para eixo X (bar, line)
  y_keys?: string[]; // Chaves para eixo Y (bar, line)
  value_key?: string; // Chave de valor (pie)
  name_key?: string; // Chave de nome (pie)
}

export interface TableComponent {
  type: 'table';
  title: string;
  columns: string[];
  rows: string[][];
}

export interface AlertComponent {
  type: 'alert';
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

export interface ComparisonComponent {
  type: 'comparison';
  title: string;
  items: Array<{
    label: string;
    value: string;
    percentage: number;
  }>;
}

export interface TimelineComponent {
  type: 'timeline';
  title: string;
  events: Array<{
    date: string;
    title: string;
    description?: string;
  }>;
}

export type Component =
  | TextComponent
  | MetricComponent
  | ChartComponent
  | TableComponent
  | AlertComponent
  | ComparisonComponent
  | TimelineComponent;

export interface ResponseMetadata {
  sources: string[];
  confidence: 'high' | 'medium' | 'low';
  processing_time_ms: number;
  suggestions?: string[];
}

export interface GeminiResponse {
  session_id: string;
  timestamp: string;
  response: {
    components: Component[];
    metadata: ResponseMetadata;
  };
}

export interface Document {
  id: string; // UUID
  type: string; // 'LOA' ou 'LDO'
  filename: string;
  status: string; // 'pending', 'processing', 'completed', 'failed'
  upload_date: string;
  processed_date?: string | null;
  total_chunks: number;
  processed_batches: number;
  total_batches: number;
  error_message?: string | null;
}

// ====================================
// Types para LDO
// ====================================

export interface ExercicioLDO {
  ano: number;
  municipio: string;
  prefeito?: string;
  documento_legal?: string;
  processado_em?: string;
}

export interface Prioridade {
  ordem: number;
  setor: string;
  titulo: string;
  descricao?: string;
  justificativa?: string;
  meta_quantitativa?: string;
  indicador?: string;
  prazo?: string;
}

export interface MetaSetorial {
  meta: string;
  indicador: string;
  valor_atual: number;
  valor_meta: number;
  unidade: string;
  recursos_necessarios?: number;
}

export interface ProgramaPrioritario {
  codigo?: string;
  nome: string;
  justificativa?: string;
}

export interface MetasPrioridadesData {
  ano: number;
  municipio: string;
  prefeito?: string;
  prioridades: Prioridade[];
  diretrizes_gerais: string[];
  metas_setoriais: Record<string, MetaSetorial>;
  programas_prioritarios: ProgramaPrioritario[];
  diretrizes_setoriais: Record<string, string[]>;
}

export interface MetaFiscal {
  meta: number | null;
  ano_anterior: number | null;
  dois_anos_antes?: number | null;
}

export interface RenunciaReceita {
  tipo: string;
  valor: number;
  justificativa: string;
}

export interface MetasFiscaisData {
  ano: number;
  municipio: string;
  resultado_primario: MetaFiscal;
  resultado_nominal: MetaFiscal;
  divida_consolidada: MetaFiscal & { percentual_rcl?: number };
  divida_liquida: MetaFiscal & { percentual_rcl?: number };
  rcl: {
    prevista: number | null;
    ano_anterior: number | null;
    dois_anos_antes?: number | null;
  };
  receita_total_prevista: number | null;
  despesa_total_prevista: number | null;
  projecoes_trienio: Record<string, any>;
  premissas_macroeconomicas: Record<string, number>;
  margem_expansao_despesas_obrigatorias: number | null;
  renuncias_receita: {
    total: number | null;
    detalhes: RenunciaReceita[];
  };
  metodologia_calculo?: string;
  observacoes?: string;
}

export interface RiscoFiscal {
  categoria: 'receita' | 'despesa' | 'divida' | 'judicial' | 'economico' | 'operacional';
  subcategoria?: string;
  titulo: string;
  descricao: string;
  impacto_estimado: number;
  impacto_percentual_orcamento?: number;
  probabilidade: 'baixa' | 'media' | 'alta';
  nivel_risco: 'baixo' | 'medio' | 'alto' | 'critico';
  providencias_mitigacao?: string;
  fonte?: string;
  historico?: string;
}

export interface PassivoContingente {
  tipo: 'trabalhista' | 'civel' | 'tributario' | 'previdenciario';
  quantidade_processos: number;
  valor_total: number;
  valor_provisionado?: number;
  probabilidade_perda: 'remota' | 'possivel' | 'provavel';
  descricao: string;
}

export interface RiscosFiscaisData {
  ano: number;
  municipio: string;
  riscos: RiscoFiscal[];
  passivos_contingentes: {
    total: number;
    detalhes: PassivoContingente[];
  };
  demandas_judiciais: {
    total: number;
    detalhes: any[];
  };
  garantias_concedidas: {
    total: number;
    detalhes: any[];
  };
  operacoes_credito_riscos: any[];
  riscos_macroeconomicos: Record<string, any>;
  riscos_especificos_municipio: any[];
  avaliacao_geral_risco: 'baixo' | 'moderado' | 'alto' | 'critico' | 'nao_informado';
  total_exposicao_risco: number;
  percentual_exposicao_orcamento: number;
}

export interface PoliticaSetorial {
  diretrizes: string[];
  programas_prioritarios: string[];
  metas: Array<{
    descricao: string;
    indicador: string;
    meta: number;
    atual: number;
  }>;
  recursos_estimados?: number;
  percentual_orcamento?: number;
  acoes_principais?: string[];
}

export interface PoliticasSetoriaisData {
  ano: number;
  municipio: string;
  politicas: Record<string, PoliticaSetorial>;
}

