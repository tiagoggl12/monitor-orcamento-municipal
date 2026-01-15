import { useState, useEffect } from 'react';
import { ldoApi, type ExercicioLDO } from '../../services/api';
import { FileText, Target, TrendingUp, AlertTriangle, Users } from 'lucide-react';
import MetasPrioridadesTab from './MetasPrioridadesTab';
import MetasFiscaisTab from './MetasFiscaisTab';
import RiscosFiscaisTab from './RiscosFiscaisTab';

type LDOTabType = 'metas-prioridades' | 'metas-fiscais' | 'riscos-fiscais' | 'politicas-setoriais';

export default function LDOPage() {
  const [exercicios, setExercicios] = useState<ExercicioLDO[]>([]);
  const [selectedAno, setSelectedAno] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<LDOTabType>('metas-prioridades');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadExercicios();
  }, []);

  const loadExercicios = async () => {
    try {
      setLoading(true);
      const data = await ldoApi.listExercicios();
      setExercicios(data);
      if (data.length > 0) {
        setSelectedAno(data[0].ano);
      }
    } catch (err) {
      console.error('Erro ao carregar exercícios LDO:', err);
      setError('Nenhuma LDO processada. Faça upload de uma LDO para começar.');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    {
      id: 'metas-prioridades',
      name: 'Metas e Prioridades',
      icon: Target,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-600',
    },
    {
      id: 'metas-fiscais',
      name: 'Metas Fiscais',
      icon: TrendingUp,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-600',
    },
    {
      id: 'riscos-fiscais',
      name: 'Riscos Fiscais',
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-600',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando LDO...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center max-w-2xl mx-auto">
          <FileText className="w-16 h-16 text-yellow-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-yellow-900 mb-2">Nenhuma LDO Encontrada</h2>
          <p className="text-yellow-800 mb-6">{error}</p>
          <div className="bg-white rounded-lg p-4 border border-yellow-200">
            <p className="text-sm text-gray-700 mb-2">
              <strong>O que é LDO?</strong>
            </p>
            <p className="text-sm text-gray-600">
              A Lei de Diretrizes Orçamentárias (LDO) estabelece as metas e prioridades da administração pública
              para o exercício financeiro seguinte. É um documento obrigatório pela LRF que orienta a elaboração
              do orçamento anual.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-600" />
            LDO - Lei de Diretrizes Orçamentárias
          </h1>
          <p className="text-gray-600 mt-1">
            Metas fiscais, prioridades governamentais e riscos fiscais
          </p>
        </div>

        {/* Seletor de Ano */}
        {exercicios.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Exercício</label>
            <select
              value={selectedAno || ''}
              onChange={(e) => setSelectedAno(Number(e.target.value))}
              className="block w-48 px-4 py-2 pr-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {exercicios.map((ex) => (
                <option key={ex.ano} value={ex.ano}>
                  {ex.ano} - {ex.municipio}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-4" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as LDOTabType)}
                className={`
                  group inline-flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm
                  transition-colors duration-200
                  ${
                    isActive
                      ? `${tab.borderColor} ${tab.color}`
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon
                  className={`w-5 h-5 ${
                    isActive ? tab.color : 'text-gray-400 group-hover:text-gray-600'
                  }`}
                />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {activeTab === 'metas-prioridades' && <MetasPrioridadesTab ano={selectedAno} />}
        {activeTab === 'metas-fiscais' && <MetasFiscaisTab ano={selectedAno} />}
        {activeTab === 'riscos-fiscais' && <RiscosFiscaisTab ano={selectedAno} />}
      </div>

      {/* Footer Info */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-2">Sobre a LDO</h3>
        <p className="text-sm text-gray-700">
          A Lei de Diretrizes Orçamentárias (LDO) é um instrumento de planejamento previsto pela Constituição
          Federal que estabelece as metas e prioridades da administração pública para o exercício financeiro
          seguinte. De acordo com a Lei de Responsabilidade Fiscal (LRF), a LDO deve conter:
        </p>
        <ul className="mt-3 space-y-1 text-sm text-gray-700">
          <li className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
            <strong>Anexo de Metas Fiscais:</strong> com metas para receitas, despesas, resultado primário e
            dívida pública
          </li>
          <li className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
            <strong>Anexo de Riscos Fiscais:</strong> avaliação de passivos contingentes e outros riscos capazes
            de afetar as contas públicas
          </li>
          <li className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
            <strong>Diretrizes e Prioridades:</strong> orientações estratégicas para elaboração do orçamento
            anual
          </li>
        </ul>
      </div>
    </div>
  );
}

