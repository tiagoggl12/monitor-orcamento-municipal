import { useState, useEffect } from 'react';
import { ldoApi, type MetasFiscaisData } from '../../services/api';
import { AlertCircle, DollarSign, Target, BarChart3, Info } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface MetasFiscaisTabProps {
  ano: number | null;
}

export default function MetasFiscaisTab({ ano }: MetasFiscaisTabProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MetasFiscaisData | null>(null);

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
      const result = await ldoApi.getMetasFiscais(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar metas fiscais:', err);
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

  if (!ano) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Selecione um ano para visualizar as metas fiscais</p>
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
        <p className="text-yellow-800">Nenhuma meta fiscal encontrada para este ano.</p>
      </div>
    );
  }

  // Preparar dados para gráficos
  const resultadoPrimarioData = [
    {
      periodo: `${ano - 2}`,
      valor: data.resultado_primario.dois_anos_antes ? data.resultado_primario.dois_anos_antes / 1000000 : 0,
    },
    {
      periodo: `${ano - 1}`,
      valor: data.resultado_primario.ano_anterior ? data.resultado_primario.ano_anterior / 1000000 : 0,
    },
    {
      periodo: `${ano} (Meta)`,
      valor: data.resultado_primario.meta ? data.resultado_primario.meta / 1000000 : 0,
    },
  ];

  const dividaConsolidadaData = [
    {
      periodo: `${ano - 2}`,
      valor: data.divida_consolidada.dois_anos_antes ? data.divida_consolidada.dois_anos_antes / 1000000 : 0,
    },
    {
      periodo: `${ano - 1}`,
      valor: data.divida_consolidada.ano_anterior ? data.divida_consolidada.ano_anterior / 1000000 : 0,
    },
    {
      periodo: `${ano} (Meta)`,
      valor: data.divida_consolidada.meta ? data.divida_consolidada.meta / 1000000 : 0,
    },
  ];

  const rclData = [
    {
      periodo: `${ano - 2}`,
      valor: data.rcl.dois_anos_antes ? data.rcl.dois_anos_antes / 1000000 : 0,
    },
    {
      periodo: `${ano - 1}`,
      valor: data.rcl.ano_anterior ? data.rcl.ano_anterior / 1000000 : 0,
    },
    {
      periodo: `${ano} (Prev.)`,
      valor: data.rcl.prevista ? data.rcl.prevista / 1000000 : 0,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-2">Metas Fiscais {ano}</h2>
        <p className="text-green-100">
          Anexo de Metas Fiscais - Obrigatório pela Lei de Responsabilidade Fiscal (LRF)
        </p>
        <p className="text-sm text-green-100 mt-2">
          Define metas de resultado primário, nominal, dívida e receita corrente líquida
        </p>
      </div>

      {/* Cards de Indicadores Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Resultado Primário */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Resultado Primário</h3>
            </div>
          </div>
          <p className="text-2xl font-bold text-blue-600 mb-1">
            {formatCurrency(data.resultado_primario.meta)}
          </p>
          {data.resultado_primario.ano_anterior && (
            <p className="text-sm text-gray-600">
              Ano anterior: {formatCurrency(data.resultado_primario.ano_anterior)}
            </p>
          )}
        </div>

        {/* Resultado Nominal */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-gray-900">Resultado Nominal</h3>
            </div>
          </div>
          <p className="text-2xl font-bold text-green-600 mb-1">
            {formatCurrency(data.resultado_nominal.meta)}
          </p>
          {data.resultado_nominal.ano_anterior && (
            <p className="text-sm text-gray-600">
              Ano anterior: {formatCurrency(data.resultado_nominal.ano_anterior)}
            </p>
          )}
        </div>

        {/* Dívida Consolidada */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-orange-600" />
              <h3 className="font-semibold text-gray-900">Dívida Consolidada</h3>
            </div>
          </div>
          <p className="text-2xl font-bold text-orange-600 mb-1">
            {formatCurrency(data.divida_consolidada.meta)}
          </p>
          {data.divida_consolidada.percentual_rcl && (
            <p className="text-sm text-gray-600">
              {data.divida_consolidada.percentual_rcl.toFixed(1)}% da RCL
            </p>
          )}
        </div>

        {/* RCL Prevista */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">RCL Prevista</h3>
            </div>
          </div>
          <p className="text-2xl font-bold text-purple-600 mb-1">
            {formatCurrency(data.rcl.prevista)}
          </p>
          {data.rcl.ano_anterior && (
            <p className="text-sm text-gray-600">
              Ano anterior: {formatCurrency(data.rcl.ano_anterior)}
            </p>
          )}
        </div>
      </div>

      {/* Gráficos de Evolução */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolução do Resultado Primário */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Evolução do Resultado Primário</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={resultadoPrimarioData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis label={{ value: 'R$ Milhões', angle: -90, position: 'insideLeft' }} />
              <Tooltip
                formatter={(value: number) => [`R$ ${value.toFixed(2)}M`, 'Valor']}
              />
              <Legend />
              <Line type="monotone" dataKey="valor" stroke="#2563eb" strokeWidth={2} name="Resultado Primário" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Evolução da Dívida Consolidada */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Evolução da Dívida Consolidada</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={dividaConsolidadaData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periodo" />
              <YAxis label={{ value: 'R$ Milhões', angle: -90, position: 'insideLeft' }} />
              <Tooltip
                formatter={(value: number) => [`R$ ${value.toFixed(2)}M`, 'Valor']}
              />
              <Legend />
              <Bar dataKey="valor" fill="#f97316" name="Dívida Consolidada" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Evolução da RCL */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Evolução da Receita Corrente Líquida (RCL)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rclData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="periodo" />
            <YAxis label={{ value: 'R$ Milhões', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              formatter={(value: number) => [`R$ ${value.toFixed(2)}M`, 'Valor']}
            />
            <Legend />
            <Bar dataKey="valor" fill="#9333ea" name="RCL" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Projeções Plurianuais */}
      {data.projecoes_trienio && Object.keys(data.projecoes_trienio).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Projeções Plurianuais (Triênio)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">Ano</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">Receita Total</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">Despesa Total</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">Resultado Primário</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">RCL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Object.entries(data.projecoes_trienio).map(([ano, proj]: [string, any]) => (
                  <tr key={ano} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{ano}</td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {formatCurrency(proj.receita_total)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {formatCurrency(proj.despesa_total)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {formatCurrency(proj.resultado_primario)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {formatCurrency(proj.rcl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Premissas Macroeconômicas */}
      {data.premissas_macroeconomicas && Object.keys(data.premissas_macroeconomicas).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-bold text-gray-900">Premissas Macroeconômicas</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(data.premissas_macroeconomicas).map(([chave, valor]: [string, number]) => {
              const labels: Record<string, string> = {
                pib_crescimento: 'Crescimento do PIB',
                inflacao_ipca: 'Inflação IPCA',
                inflacao_igpm: 'Inflação IGPM',
                taxa_selic: 'Taxa SELIC',
                cambio_dolar: 'Câmbio Dólar',
                salario_minimo: 'Salário Mínimo',
                crescimento_transferencias_federais: 'Cresc. Transferências',
              };
              return (
                <div key={chave} className="border border-gray-200 rounded-lg p-4">
                  <p className="text-xs text-gray-600 mb-1">{labels[chave] || chave}</p>
                  <p className="text-lg font-bold text-gray-900">
                    {chave.includes('taxa') || chave.includes('crescimento') || chave.includes('inflacao')
                      ? `${valor}%`
                      : chave.includes('cambio')
                      ? `R$ ${valor}`
                      : chave.includes('salario')
                      ? `R$ ${valor}`
                      : String(valor)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Renúncias de Receita */}
      {data.renuncias_receita?.total && data.renuncias_receita.total > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Renúncias de Receita</h3>
          <p className="text-3xl font-bold text-red-600 mb-4">
            {formatCurrency(data.renuncias_receita.total)}
          </p>
          {data.renuncias_receita.detalhes && data.renuncias_receita.detalhes.length > 0 && (
            <div className="space-y-3">
              {data.renuncias_receita.detalhes.map((renuncia: MetasFiscaisData['renuncias_receita']['detalhes'][0], idx: number) => (
                <div key={idx} className="border-l-4 border-red-400 pl-4 py-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-gray-900">{renuncia.tipo}</h4>
                      <p className="text-sm text-gray-600">{renuncia.justificativa}</p>
                    </div>
                    <span className="font-bold text-red-600 ml-4">
                      {formatCurrency(renuncia.valor)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metodologia e Observações */}
      {(data.metodologia_calculo || data.observacoes) && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
          {data.metodologia_calculo && (
            <div className="mb-4">
              <h4 className="font-semibold text-gray-900 mb-2">Metodologia de Cálculo</h4>
              <p className="text-sm text-gray-700">{data.metodologia_calculo}</p>
            </div>
          )}
          {data.observacoes && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Observações</h4>
              <p className="text-sm text-gray-700">{data.observacoes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

