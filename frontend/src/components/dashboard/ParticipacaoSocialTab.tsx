import { useState, useEffect } from 'react';
import { 
  Users, 
  MessageSquare,
  CheckSquare,
  DollarSign,
  Target,
  Loader2
} from 'lucide-react';
import { dashboardApi, type ParticipacaoSocialData } from '../../services/api';

interface Props {
  ano: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  educacao: 'bg-blue-500',
  saude: 'bg-red-500',
  infraestrutura: 'bg-orange-500',
  social: 'bg-purple-500',
  urbanismo: 'bg-green-500',
};

export default function ParticipacaoSocialTab({ ano }: Props) {
  const [data, setData] = useState<ParticipacaoSocialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [ano]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getParticipacaoSocial(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar participação social:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) {
      return `R$ ${(value / 1_000_000_000).toFixed(2)}B`;
    }
    if (value >= 1_000_000) {
      return `R$ ${(value / 1_000_000).toFixed(1)}M`;
    }
    return `R$ ${value.toLocaleString('pt-BR')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!data || (data.foruns_realizados === 0 && data.iniciativas.length === 0)) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8 text-center">
        <Users className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-yellow-800 mb-2">
          Dados de Participação Social Não Disponíveis
        </h2>
        <p className="text-yellow-700">
          Os dados do orçamento participativo não estão disponíveis para este exercício.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-8 text-white relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-white rounded-full translate-y-1/2 -translate-x-1/2" />
        </div>
        
        <div className="relative">
          <h2 className="text-2xl font-bold mb-3">Orçamento Participativo {ano}</h2>
          <p className="text-purple-100 max-w-2xl">
            {data.descricao || `O processo de escuta cidadã envolveu ${data.foruns_realizados} Fóruns Territoriais 
            e uma plataforma virtual, permitindo que a população priorizasse ${data.temas_chave} temas 
            estruturantes para o desenvolvimento da cidade.`}
          </p>

          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8">
            <div className="text-center">
              <p className="text-4xl font-bold">{data.foruns_realizados}</p>
              <p className="text-purple-200 text-sm">FÓRUNS REALIZADOS</p>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold">{data.temas_chave}</p>
              <p className="text-purple-200 text-sm">TEMAS CHAVE</p>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold">{formatCurrency(data.total_priorizado)}</p>
              <p className="text-purple-200 text-sm">TOTAL PRIORIZADO</p>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold">{data.rastreabilidade}%</p>
              <p className="text-purple-200 text-sm">RASTREABILIDADE</p>
            </div>
          </div>
        </div>
      </div>

      {/* Iniciativas Priorizadas */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-6">
          <Target className="h-5 w-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Iniciativas Priorizadas pela População
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.iniciativas.map((iniciativa, idx) => (
            <div 
              key={idx}
              className="border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CheckSquare className="h-5 w-5 text-green-500" />
                  <span className="text-xs text-gray-500 uppercase font-medium">
                    Prioritário
                  </span>
                </div>
                <div className={`w-2 h-2 rounded-full ${CATEGORY_COLORS[iniciativa.categoria] || 'bg-gray-400'}`} />
              </div>

              <h4 className="font-semibold text-gray-900 mb-2">{iniciativa.nome}</h4>
              
              <p className="text-sm text-gray-500 mb-4">{iniciativa.descricao}</p>

              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <span className="text-xs text-gray-400">INVESTIMENTO</span>
                <span className="text-blue-600 font-bold">{formatCurrency(iniciativa.valor)}</span>
              </div>
            </div>
          ))}
        </div>

        {data.iniciativas.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>Nenhuma iniciativa registrada para este exercício.</p>
          </div>
        )}
      </div>

      {/* Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-5 border border-purple-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-purple-500 p-2 rounded-lg">
              <MessageSquare className="h-5 w-5 text-white" />
            </div>
            <span className="text-purple-700 font-medium">Escuta Cidadã</span>
          </div>
          <p className="text-purple-900 text-2xl font-bold">{data.foruns_realizados} Fóruns</p>
          <p className="text-purple-600 text-sm">realizados em toda a cidade</p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-5 border border-blue-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-blue-500 p-2 rounded-lg">
              <Users className="h-5 w-5 text-white" />
            </div>
            <span className="text-blue-700 font-medium">Temas Priorizados</span>
          </div>
          <p className="text-blue-900 text-2xl font-bold">{data.temas_chave} Temas</p>
          <p className="text-blue-600 text-sm">estruturantes definidos</p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-5 border border-green-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-green-500 p-2 rounded-lg">
              <DollarSign className="h-5 w-5 text-white" />
            </div>
            <span className="text-green-700 font-medium">Recursos Alocados</span>
          </div>
          <p className="text-green-900 text-2xl font-bold">{formatCurrency(data.total_priorizado)}</p>
          <p className="text-green-600 text-sm">em investimentos diretos</p>
        </div>
      </div>
    </div>
  );
}

