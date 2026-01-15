import { useState, useEffect } from 'react';
import { 
  MapPin, 
  Heart,
  Building,
  GraduationCap,
  Users,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { dashboardApi, type InvestimentoRegionalData } from '../../services/api';
import RegionalDetailModal from './RegionalDetailModal';

interface Props {
  ano: number;
}

const AREA_ICONS: Record<string, typeof Heart> = {
  saude: Heart,
  infraestrutura: Building,
  educacao: GraduationCap,
  social: Users,
};

// Cores atualizadas para corresponder ao backend
const AREA_COLORS: Record<string, { bg: string; text: string; hex: string }> = {
  saude: { bg: 'bg-red-50', text: 'text-red-500', hex: '#EF4444' },
  infraestrutura: { bg: 'bg-orange-50', text: 'text-orange-500', hex: '#F97316' },
  educacao: { bg: 'bg-purple-50', text: 'text-purple-500', hex: '#8B5CF6' },
  social: { bg: 'bg-blue-50', text: 'text-blue-500', hex: '#3B82F6' },
};

export default function InvestimentoRegionalTab({ ano }: Props) {
  const [data, setData] = useState<InvestimentoRegionalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRegional, setSelectedRegional] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, [ano]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getInvestimentoRegional(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar investimento regional:', err);
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

  if (!data || data.regionais.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8 text-center">
        <MapPin className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-yellow-800 mb-2">
          Dados Regionais Não Disponíveis
        </h2>
        <p className="text-yellow-700">
          Os dados de investimento por regional não estão disponíveis para este exercício.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl p-6 text-white">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="h-5 w-5" />
              <span className="text-blue-200 text-sm">GEOGRAFIA DO ORÇAMENTO</span>
            </div>
            <h2 className="text-2xl font-bold mb-2">Investimento Regionalizado</h2>
            <p className="text-blue-100">
              Descubra como os {formatCurrency(data.total_regionais)} são aplicados em cada território
              para reduzir as desigualdades sociais de Fortaleza.
            </p>
          </div>
          <div className="bg-white/20 rounded-xl p-4 text-center">
            <p className="text-blue-200 text-xs">TOTAL PARA AS REGIONAIS</p>
            <p className="text-3xl font-bold">{formatCurrency(data.total_regionais)}</p>
          </div>
        </div>
      </div>

      {/* Grid de Regionais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.regionais.map((regional) => (
          <div 
            key={regional.numero}
            className="bg-white rounded-xl border border-gray-200 hover:shadow-lg transition-shadow flex flex-col"
          >
            {/* Conteúdo do card */}
            <div className="p-5 flex-1">
              {/* Header da Regional */}
              <div className="flex items-center justify-between mb-4">
                <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                  REGIONAL {regional.numero}
                </span>
                <span className="text-blue-600 font-bold text-lg">
                  {formatCurrency(regional.valor)}
                </span>
              </div>

              {/* Bairros - Mostrar TODOS */}
              {regional.bairros && regional.bairros.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    BAIRROS E TERRITÓRIOS
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {regional.bairros.map((bairro, idx) => (
                      <span 
                        key={idx}
                        className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded"
                      >
                        {bairro}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Destaques com ícones coloridos */}
              {regional.destaques && regional.destaques.length > 0 && (
                <div className="border-t border-gray-100 pt-4">
                  <p className="text-xs text-gray-500 mb-3">DESTAQUES DO PLANO</p>
                  <div className="space-y-2">
                    {regional.destaques.slice(0, 2).map((destaque, idx) => {
                      const Icon = AREA_ICONS[destaque.categoria] || Building;
                      const colors = AREA_COLORS[destaque.categoria] || { bg: 'bg-gray-50', text: 'text-gray-500' };
                      
                      return (
                        <div key={idx} className="flex items-start gap-2">
                          <div className={`p-1.5 rounded ${colors.bg}`}>
                            <Icon className={`h-4 w-4 ${colors.text}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{destaque.nome}</p>
                            <p className="text-xs text-gray-500 line-clamp-2">{destaque.descricao}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Botão fixo no bottom */}
            <div className="border-t border-gray-100 p-4">
              <button 
                onClick={() => setSelectedRegional(regional.numero)}
                className="w-full text-center text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 font-medium flex items-center justify-center gap-1 py-2 rounded-lg transition-colors"
              >
                VER PLANO COMPLETO
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Legenda com ícones coloridos */}
      <div className="bg-gray-50 rounded-xl p-4">
        <div className="flex flex-wrap justify-center gap-6">
          {Object.entries(AREA_ICONS).map(([area, Icon]) => {
            const colors = AREA_COLORS[area] || { bg: 'bg-gray-50', text: 'text-gray-500' };
            const labels: Record<string, string> = {
              saude: 'Saúde',
              infraestrutura: 'Infraestrutura',
              educacao: 'Educação',
              social: 'Social'
            };
            return (
              <div key={area} className="flex items-center gap-2">
                <div className={`p-1.5 rounded ${colors.bg}`}>
                  <Icon className={`h-4 w-4 ${colors.text}`} />
                </div>
                <span className="text-sm text-gray-600">{labels[area] || area}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal de Detalhamento */}
      {selectedRegional !== null && (
        <RegionalDetailModal
          ano={ano}
          regionalNumero={selectedRegional}
          onClose={() => setSelectedRegional(null)}
        />
      )}
    </div>
  );
}

