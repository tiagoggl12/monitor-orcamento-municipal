import { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  TrendingUp, 
  TrendingDown, 
  MapPin, 
  Users,
  Scale,
  ChevronDown,
  Loader2
} from 'lucide-react';
import { dashboardApi, type ExercicioListItem } from '../../services/api';
import VisaoGeralTab from './VisaoGeralTab';
import ReceitasTab from './ReceitasTab';
import DespesasTab from './DespesasTab';
import InvestimentoRegionalTab from './InvestimentoRegionalTab';
import ParticipacaoSocialTab from './ParticipacaoSocialTab';

type TabType = 'visao-geral' | 'receitas' | 'despesas' | 'investimento' | 'participacao';

const tabs = [
  { id: 'visao-geral' as TabType, name: 'Visão Geral', icon: LayoutDashboard },
  { id: 'receitas' as TabType, name: 'Receitas', icon: TrendingUp },
  { id: 'despesas' as TabType, name: 'Despesas', icon: TrendingDown },
  { id: 'investimento' as TabType, name: 'Investimento Regional', icon: MapPin },
  { id: 'participacao' as TabType, name: 'Participação Social', icon: Users },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('visao-geral');
  const [exercicios, setExercicios] = useState<ExercicioListItem[]>([]);
  const [selectedAno, setSelectedAno] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showYearDropdown, setShowYearDropdown] = useState(false);

  useEffect(() => {
    loadExercicios();
  }, []);

  const loadExercicios = async () => {
    try {
      setLoading(true);
      const data = await dashboardApi.listExercicios();
      setExercicios(data);
      if (data.length > 0) {
        setSelectedAno(data[0].ano);
      }
    } catch (err) {
      console.error('Erro ao carregar exercícios:', err);
      setError('Nenhum exercício orçamentário processado. Faça upload de uma LOA ou LDO.');
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

  const selectedExercicio = exercicios.find(e => e.ano === selectedAno);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />
        <span className="ml-4 text-lg text-gray-600">Carregando dados orçamentários...</span>
      </div>
    );
  }

  if (error || !selectedAno) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8 text-center">
        <Scale className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-yellow-800 mb-2">Nenhum Exercício Disponível</h2>
        <p className="text-yellow-700">
          {error || 'Faça upload de um documento LOA ou LDO para visualizar o dashboard.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header com seletor de ano */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="bg-white/20 p-2 rounded-lg">
                <Scale className="h-6 w-6" />
              </div>
              <div className="relative">
                <button
                  onClick={() => setShowYearDropdown(!showYearDropdown)}
                  className="flex items-center gap-2 text-2xl font-bold hover:bg-white/10 px-3 py-1 rounded-lg transition"
                >
                  {selectedExercicio?.municipio || 'Fortaleza'}
                  <span className="text-blue-200">|</span>
                  <span className="text-blue-100">{selectedExercicio?.tipo_documento} {selectedAno}</span>
                  <ChevronDown className="h-5 w-5" />
                </button>
                
                {showYearDropdown && (
                  <div className="absolute top-full left-0 mt-2 bg-white text-gray-800 rounded-lg shadow-xl py-2 min-w-[200px] z-50">
                    {exercicios.map(ex => (
                      <button
                        key={ex.id}
                        onClick={() => {
                          setSelectedAno(ex.ano);
                          setShowYearDropdown(false);
                        }}
                        className={`w-full text-left px-4 py-2 hover:bg-blue-50 ${
                          ex.ano === selectedAno ? 'bg-blue-100 text-blue-700' : ''
                        }`}
                      >
                        {ex.tipo_documento} {ex.ano} - {ex.municipio}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <p className="text-blue-100 text-sm">
              Documento de Referência: Exercício Orçamentário {selectedAno}
            </p>
          </div>
          
          <div className="text-right">
            <p className="text-blue-200 text-sm">Orçamento Total</p>
            <p className="text-3xl font-bold">
              {formatCurrency(selectedExercicio?.orcamento_total || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* Navegação por abas */}
      <nav className="bg-white rounded-xl shadow-sm border border-gray-100 p-1 flex gap-1 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 rounded-lg font-medium transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon className="h-5 w-5" />
              {tab.name}
            </button>
          );
        })}
      </nav>

      {/* Conteúdo da aba ativa */}
      <div className="min-h-[500px]">
        {activeTab === 'visao-geral' && <VisaoGeralTab ano={selectedAno} />}
        {activeTab === 'receitas' && <ReceitasTab ano={selectedAno} />}
        {activeTab === 'despesas' && <DespesasTab ano={selectedAno} />}
        {activeTab === 'investimento' && <InvestimentoRegionalTab ano={selectedAno} />}
        {activeTab === 'participacao' && <ParticipacaoSocialTab ano={selectedAno} />}
      </div>
    </div>
  );
}

