import React from 'react';
import { X, MapPin, TrendingUp, ExternalLink, Download } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface DestaqueDetalhado {
  categoria: string;
  categoria_nome: string;
  categoria_icone: string;
  cor: string;
  nome: string;
  descricao: string;
  prioridade: string;
  valor_estimado: number;
  status: string;
  previsao: string;
}

interface DivisaoPorArea {
  nome: string;
  valor: number;
  percentual: number;
  cor: string;
}

interface RegionalDetail {
  ano: number;
  regional_numero: number;
  regional_nome: string;
  valor_total: number;
  bairros: string[];
  num_bairros: number;
  divisao_por_area: Record<string, DivisaoPorArea>;
  acoes_estrategicas: DestaqueDetalhado[];
  indicadores: {
    idh_variacao_estimada: number;
    populacao_beneficiada_estimada: number;
    investimento_per_capita: number;
  };
  fonte_dados: string;
  documento_referencia: string;
}

interface Props {
  ano: number;
  regionalNumero: number;
  onClose: () => void;
}

function RegionalDetailModal({ ano, regionalNumero, onClose }: Props) {
  const [data, setData] = React.useState<RegionalDetail | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ano, regionalNumero]);

  const loadDetail = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:4001/api/dashboard/investimento-regional/${ano}/regional/${regionalNumero}`
      );
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar detalhamento:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getPrioridadeBadge = (prioridade: string) => {
    const config = {
      alta: { label: 'PRIORIDADE ALTA', className: 'bg-red-100 text-red-700' },
      media: { label: 'PRIORIDADE MÉDIA', className: 'bg-yellow-100 text-yellow-700' },
      baixa: { label: 'PRIORIDADE BAIXA', className: 'bg-green-100 text-green-700' }
    }[prioridade] || { label: 'PRIORIDADE', className: 'bg-gray-100 text-gray-700' };

    return (
      <span className={`text-xs px-2 py-0.5 rounded ${config.className} font-medium`}>
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Carregando detalhes...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Preparar dados para o gráfico pizza
  const chartData = Object.entries(data.divisao_por_area).map(([, area]) => ({
    name: area.nome,
    value: area.percentual,
    valorAbsoluto: area.valor,
    color: area.cor
  }));

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center overflow-y-auto" style={{marginTop: 0}}>
      <div className="bg-white w-full max-w-5xl relative my-4 mx-4 max-h-[calc(100vh-2rem)] overflow-y-auto flex flex-col rounded-xl shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6 flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="bg-white text-blue-600 px-3 py-1 rounded-full text-sm font-bold">
                REGIONAL {data.regional_numero}
              </span>
              <span className="bg-green-500 text-white px-3 py-1 rounded text-xs font-medium">
                PLANEJADO {data.ano}
              </span>
            </div>
            <h2 className="text-2xl font-bold">Detalhamento do Plano de Investimento</h2>
            <p className="text-blue-100 text-sm mt-1">
              {data.regional_nome} • {data.bairros.join(' • ')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Bairros */}
          <div>
            <h3 className="text-sm text-gray-500 mb-3 flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              BAIRROS E TERRITÓRIOS
            </h3>
            <div className="flex flex-wrap gap-2">
              {data.bairros.map((bairro, idx) => (
                <span
                  key={idx}
                  className="text-sm bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg"
                >
                  {bairro}
                </span>
              ))}
            </div>
          </div>

          {/* Divisão por Área + Ações Estratégicas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Gráfico Pizza */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-sm text-gray-500 mb-4">DIVISÃO POR ÁREA DE ATUAÇÃO</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number, name: string, props: any) => [
                      `${value.toFixed(1)}% (${formatCurrency(props.payload.valorAbsoluto)})`,
                      name
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>

              {/* Legenda do gráfico */}
              <div className="space-y-2 mt-4">
                {chartData.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-sm text-gray-700">{item.name}</span>
                    </div>
                    <span className="text-sm font-medium text-gray-900">
                      {formatCurrency(item.valorAbsoluto)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Ações Estratégicas */}
            <div className="space-y-3">
              <h3 className="text-sm text-gray-500 mb-4">AÇÕES E METAS ESTRATÉGICAS</h3>
              <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2">
                {data.acoes_estrategicas.map((acao, idx) => (
                  <div
                    key={idx}
                    className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-3">
                      {/* Ícone colorido */}
                      <div
                        className="p-2 rounded-lg flex-shrink-0"
                        style={{ backgroundColor: `${acao.cor}20` }}
                      >
                        <div className="w-6 h-6" style={{ color: acao.cor }}>
                          {/* Renderizar ícone baseado no tipo */}
                          {acao.categoria === 'saude' && '❤️'}
                          {acao.categoria === 'infraestrutura' && '🏗️'}
                          {acao.categoria === 'educacao' && '🎓'}
                          {acao.categoria === 'social' && '👥'}
                          {acao.categoria === 'urbanismo' && '🏙️'}
                          {acao.categoria === 'cultura' && '🎨'}
                          {acao.categoria === 'esporte' && '⚽'}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex-1">
                            <span className="text-xs text-gray-500 uppercase">
                              {acao.categoria_nome}
                            </span>
                          </div>
                          {getPrioridadeBadge(acao.prioridade)}
                        </div>
                        <h4 className="font-semibold text-gray-900 mb-1">{acao.nome}</h4>
                        <p className="text-sm text-gray-600 mb-2">{acao.descricao}</p>
                        <button className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
                          ACOMPANHAR LICITAÇÃO
                          <ExternalLink className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Indicador de Impacto */}
          {data.indicadores.idh_variacao_estimada > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-blue-900">
                    Este plano visa aumentar o IDH-B (Índice de Desenvolvimento Humano por Bairro) 
                    desta regional em até <strong>{data.indicadores.idh_variacao_estimada}%</strong> até 
                    o final de {data.ano}.
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    População beneficiada: {data.indicadores.populacao_beneficiada_estimada.toLocaleString('pt-BR')} habitantes
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Footer com informações */}
          <div className="border-t border-gray-200 pt-4 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              <p className="flex items-center gap-1">
                ℹ️ Dados baseados no {data.fonte_dados} - {data.documento_referencia}
              </p>
            </div>
            <div className="flex gap-2">
              <button className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 flex items-center gap-2">
                <ExternalLink className="h-4 w-4" />
                TRANSPARÊNCIA
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
                <Download className="h-4 w-4" />
                BAIXAR PDF
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegionalDetailModal;
