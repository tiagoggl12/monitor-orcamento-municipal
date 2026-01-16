import { useState, useEffect } from 'react';
import { ldoApi, type RiscosFiscaisData } from '../../services/api';
import { AlertCircle, Shield, Info, TrendingDown } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface RiscosFiscaisTabProps {
  ano: number | null;
}

export default function RiscosFiscaisTab({ ano }: RiscosFiscaisTabProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RiscosFiscaisData | null>(null);

  useEffect(() => {
    if (ano) {
      loadData();
    }
  }, [ano]);

  const loadData = async () => {
    if (!ano) return;

    try {
      setLoading(true);
      setError(null);
      const result = await ldoApi.getRiscosFiscais(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar riscos fiscais:', err);
      setError('Erro ao carregar dados. Verifique se a LDO foi processada.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (!value) return 'N/D';
    const absValue = Math.abs(value);
    if (absValue >= 1000000000) {
      return `${value < 0 ? '-' : ''}R$ ${(absValue / 1000000000).toFixed(2)}B`;
    } else if (absValue >= 1000000) {
      return `${value < 0 ? '-' : ''}R$ ${(absValue / 1000000).toFixed(2)}M`;
    }
    return `${value < 0 ? '-' : ''}R$ ${absValue.toFixed(2)}`;
  };

  const getRiscoColor = (nivel: string) => {
    switch (nivel) {
      case 'critico':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'alto':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'medio':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'baixo':
        return 'bg-green-100 text-green-800 border-green-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getProbabilidadeColor = (prob: string) => {
    switch (prob) {
      case 'alta':
        return 'text-red-600';
      case 'media':
        return 'text-yellow-600';
      case 'baixa':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  if (!ano) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Selecione um ano para visualizar os riscos fiscais</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-3" />
        <p className="text-red-800 font-medium">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <AlertCircle className="w-12 h-12 text-yellow-600 mx-auto mb-3" />
        <p className="text-yellow-800">Nenhum risco fiscal encontrado para este ano.</p>
      </div>
    );
  }

  // Dados para gráficos
  const riscosPorCategoria = data.riscos?.reduce((acc: Record<string, number>, risco) => {
    acc[risco.categoria] = (acc[risco.categoria] || 0) + risco.impacto_estimado;
    return acc;
  }, {});

  const categoriaChartData = riscosPorCategoria
    ? Object.entries(riscosPorCategoria).map(([categoria, valor]: [string, number]) => ({
        name: categoria.charAt(0).toUpperCase() + categoria.slice(1),
        value: valor / 1000000, // Em milhões
      }))
    : [];

  const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-600 to-orange-600 text-white rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-2">Riscos Fiscais {ano}</h2>
        <p className="text-red-100">
          Anexo de Riscos Fiscais - Obrigatório pela Lei de Responsabilidade Fiscal (LRF)
        </p>
        <p className="text-sm text-red-100 mt-2">
          Identifica eventos que podem impactar negativamente as contas públicas
        </p>
      </div>

      {/* Card de Avaliação Geral */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Avaliação Geral de Risco</h3>
            <p className="text-4xl font-bold">
              <span
                className={`${
                  data.avaliacao_geral_risco === 'critico'
                    ? 'text-red-600'
                    : data.avaliacao_geral_risco === 'alto'
                    ? 'text-orange-600'
                    : data.avaliacao_geral_risco === 'moderado'
                    ? 'text-yellow-600'
                    : 'text-green-600'
                }`}
              >
                {data.avaliacao_geral_risco?.toUpperCase() || 'NÃO INFORMADO'}
              </span>
            </p>
          </div>
          <Shield
            className={`w-16 h-16 ${
              data.avaliacao_geral_risco === 'critico'
                ? 'text-red-600'
                : data.avaliacao_geral_risco === 'alto'
                ? 'text-orange-600'
                : data.avaliacao_geral_risco === 'moderado'
                ? 'text-yellow-600'
                : 'text-green-600'
            }`}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Exposição Total ao Risco</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(data.total_exposicao_risco)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">% do Orçamento</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.percentual_exposicao_orcamento?.toFixed(2)}%
            </p>
          </div>
        </div>
      </div>

      {/* Gráfico de Riscos por Categoria */}
      {categoriaChartData.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Distribuição de Riscos por Categoria</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoriaChartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: R$ ${value.toFixed(1)}M`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {categoriaChartData.map((_entry, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => `R$ ${value.toFixed(2)}M`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Lista de Riscos Identificados */}
      {data.riscos && data.riscos.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Riscos Identificados</h3>
          <div className="space-y-4">
            {data.riscos.map((risco: RiscosFiscaisData['riscos'][0], idx: number) => (
              <div
                key={idx}
                className={`border-l-4 pl-4 py-3 rounded-r-lg ${
                  risco.nivel_risco === 'critico'
                    ? 'border-red-600 bg-red-50'
                    : risco.nivel_risco === 'alto'
                    ? 'border-orange-600 bg-orange-50'
                    : risco.nivel_risco === 'medio'
                    ? 'border-yellow-600 bg-yellow-50'
                    : 'border-green-600 bg-green-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiscoColor(
                          risco.nivel_risco
                        )}`}
                      >
                        {risco.nivel_risco.toUpperCase()}
                      </span>
                      <span className="text-xs font-medium text-gray-600">
                        {risco.categoria.charAt(0).toUpperCase() + risco.categoria.slice(1)}
                      </span>
                      {risco.subcategoria && (
                        <span className="text-xs text-gray-500">→ {risco.subcategoria}</span>
                      )}
                    </div>
                    <h4 className="font-semibold text-gray-900 mb-1">{risco.titulo}</h4>
                    <p className="text-sm text-gray-700 mb-3">{risco.descricao}</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                      <div>
                        <span className="text-gray-600">Impacto Estimado:</span>
                        <span className="font-bold text-gray-900 ml-2">
                          {formatCurrency(risco.impacto_estimado)}
                        </span>
                        {risco.impacto_percentual_orcamento && (
                          <span className="text-gray-600 ml-1">
                            ({risco.impacto_percentual_orcamento.toFixed(2)}%)
                          </span>
                        )}
                      </div>
                      <div>
                        <span className="text-gray-600">Probabilidade:</span>
                        <span className={`font-bold ml-2 ${getProbabilidadeColor(risco.probabilidade)}`}>
                          {risco.probabilidade.charAt(0).toUpperCase() + risco.probabilidade.slice(1)}
                        </span>
                      </div>
                    </div>
                    {risco.providencias_mitigacao && (
                      <div className="mt-3 p-3 bg-white rounded border border-gray-200">
                        <p className="text-xs font-semibold text-gray-700 mb-1">Providências de Mitigação:</p>
                        <p className="text-sm text-gray-600">{risco.providencias_mitigacao}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Passivos Contingentes */}
      {data.passivos_contingentes && data.passivos_contingentes.total > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Passivos Contingentes</h3>
          <p className="text-3xl font-bold text-orange-600 mb-4">
            {formatCurrency(data.passivos_contingentes.total)}
          </p>
          {data.passivos_contingentes.detalhes && data.passivos_contingentes.detalhes.length > 0 && (
            <div className="space-y-3">
              {data.passivos_contingentes.detalhes.map((passivo: RiscosFiscaisData['passivos_contingentes']['detalhes'][0], idx: number) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-semibold text-gray-900">{passivo.tipo.toUpperCase()}</span>
                      <p className="text-sm text-gray-600">{passivo.descricao}</p>
                    </div>
                    <span className="font-bold text-orange-600 ml-4">{formatCurrency(passivo.valor_total)}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                    <div>
                      <p className="text-gray-600">Quantidade de Processos</p>
                      <p className="font-semibold text-gray-900">{passivo.quantidade_processos}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Valor Provisionado</p>
                      <p className="font-semibold text-gray-900">
                        {formatCurrency(passivo.valor_provisionado)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Probabilidade de Perda</p>
                      <p className={`font-semibold ${getProbabilidadeColor(passivo.probabilidade_perda)}`}>
                        {passivo.probabilidade_perda.charAt(0).toUpperCase() + passivo.probabilidade_perda.slice(1)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Demandas Judiciais */}
      {data.demandas_judiciais && data.demandas_judiciais.total > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Demandas Judiciais (Precatórios)</h3>
          <p className="text-3xl font-bold text-red-600 mb-4">
            {formatCurrency(data.demandas_judiciais.total)}
          </p>
          {data.demandas_judiciais.detalhes && data.demandas_judiciais.detalhes.length > 0 && (
            <div className="space-y-3">
              {data.demandas_judiciais.detalhes.map((demanda: any, idx: number) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Tipo</p>
                      <p className="font-semibold text-gray-900">{demanda.tipo}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Quantidade</p>
                      <p className="font-semibold text-gray-900">{demanda.quantidade}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Valor Total</p>
                      <p className="font-semibold text-red-600">{formatCurrency(demanda.valor_total)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Previsão Pagamento</p>
                      <p className="font-semibold text-gray-900">{demanda.previsao_pagamento}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Riscos Macroeconômicos */}
      {data.riscos_macroeconomicos && Object.keys(data.riscos_macroeconomicos).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-bold text-gray-900">Riscos Macroeconômicos</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(data.riscos_macroeconomicos).map(([risco, dados]: [string, any]) => {
              const labels: Record<string, string> = {
                inflacao_acima_previsto: 'Inflação Acima do Previsto',
                queda_pib: 'Queda do PIB',
                alta_juros: 'Alta de Juros',
              };
              return (
                <div key={risco} className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">{labels[risco] || risco}</h4>
                  <p className="text-sm text-gray-600 mb-1">
                    Impacto: <span className="font-bold text-purple-600">{formatCurrency(dados.impacto)}</span>
                  </p>
                  <p className="text-sm text-gray-600">
                    Probabilidade:{' '}
                    <span className={`font-bold ${getProbabilidadeColor(dados.probabilidade)}`}>
                      {dados.probabilidade}
                    </span>
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Informações Adicionais */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <Info className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">Sobre o Anexo de Riscos Fiscais</h4>
            <p className="text-sm text-blue-800">
              A Lei de Responsabilidade Fiscal (LRF) exige que a LDO contenha o Anexo de Riscos Fiscais, onde devem ser
              avaliados os passivos contingentes e outros riscos capazes de afetar as contas públicas, informando as
              providências a serem tomadas, caso se concretizem.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

