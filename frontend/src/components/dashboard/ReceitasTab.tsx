import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  ArrowUpRight,
  Loader2,
  Info
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';
import { dashboardApi, type ReceitasData } from '../../services/api';

interface Props {
  ano: number;
}

export default function ReceitasTab({ ano }: Props) {
  const [data, setData] = useState<ReceitasData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [ano]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getReceitas(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar receitas:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatFullCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!data) return null;

  // Dados para gráfico de fontes
  const fontesData = data.receitas_correntes.slice(0, 6).map(r => ({
    name: r.categoria.length > 25 ? r.categoria.substring(0, 25) + '...' : r.categoria,
    valor: r.valor,
  }));

  return (
    <div className="space-y-6">
      {/* Banner explicativo */}
      <div className="bg-blue-50 rounded-xl p-6 border border-blue-100">
        <div className="flex items-start gap-4">
          <div className="bg-blue-100 p-3 rounded-full">
            <TrendingUp className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-blue-900 mb-1">
              Entendendo as Receitas de Fortaleza
            </h3>
            <p className="text-blue-700 text-sm">
              A receita é todo o dinheiro que entra no cofre da Prefeitura para pagar as contas da cidade. 
              A maior parte vem das <strong>Receitas Correntes</strong>, que são como o "salário mensal" da cidade. 
              Dentro delas, o destaque são as <strong>Transferências Correntes</strong>.
            </p>
            <div className="mt-3 flex items-center gap-2 text-xs text-blue-600">
              <Info className="h-4 w-4" />
              <span>
                <strong>O que são Transferências Correntes?</strong> É o dinheiro que Fortaleza recebe obrigatoriamente 
                do Governo Federal e do Estado do Ceará (como o Fundo de Participação dos Municípios e o ICMS).
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Cards de totais */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Receitas Correntes */}
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-6 text-white">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-white/20 p-2 rounded-lg">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <p className="text-blue-100 text-sm">Receitas Correntes</p>
              <span className="bg-blue-500 px-2 py-0.5 rounded text-xs">Dinheiro do dia a dia</span>
            </div>
          </div>
          <p className="text-3xl font-bold mb-4">
            {formatCurrency(data.receitas_correntes_total)}
          </p>
          
          <div className="space-y-3">
            {data.receitas_correntes.slice(0, 4).map((r, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">{r.categoria}</p>
                  {r.descricao_popular && (
                    <p className="text-blue-200 text-xs">{r.descricao_popular}</p>
                  )}
                </div>
                <p className="font-bold">{formatCurrency(r.valor)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Receitas de Capital */}
        <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-6 text-white">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-white/20 p-2 rounded-lg">
              <ArrowUpRight className="h-5 w-5" />
            </div>
            <div>
              <p className="text-green-100 text-sm">Receitas de Capital</p>
              <span className="bg-green-500 px-2 py-0.5 rounded text-xs">Dinheiro para investimentos</span>
            </div>
          </div>
          <p className="text-3xl font-bold mb-4">
            {formatCurrency(data.receitas_capital_total)}
          </p>
          
          <div className="space-y-3">
            {data.receitas_capital.map((r, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">{r.categoria}</p>
                  {r.descricao_popular && (
                    <p className="text-green-200 text-xs">{r.descricao_popular}</p>
                  )}
                </div>
                <p className="font-bold">{formatCurrency(r.valor)}</p>
              </div>
            ))}
            {data.receitas_capital.length === 0 && (
              <p className="text-green-200 text-sm italic">Dados não disponíveis</p>
            )}
          </div>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolução da Arrecadação */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            <TrendingUp className="inline h-5 w-5 mr-2 text-blue-600" />
            Evolução da Arrecadação
          </h3>
          <p className="text-sm text-gray-500 mb-4">Série histórica de receitas</p>
          
          {data.serie_historica.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={data.serie_historica}>
                <defs>
                  <linearGradient id="colorReceita" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="ano" />
                <YAxis tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip formatter={(value: number) => formatFullCurrency(value)} />
                <Area 
                  type="monotone" 
                  dataKey="valor" 
                  stroke="#3B82F6" 
                  fillOpacity={1} 
                  fill="url(#colorReceita)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center bg-gray-50 rounded-lg">
              <p className="text-gray-400">Série histórica não disponível</p>
            </div>
          )}
        </div>

        {/* Principais Fontes */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            De onde vem o dinheiro?
          </h3>
          <p className="text-sm text-gray-500 mb-4">Principais fontes de receita</p>
          
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={fontesData}>
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
              <YAxis tickFormatter={(v) => formatCurrency(v)} />
              <Tooltip formatter={(value: number) => formatFullCurrency(value)} />
              <Bar dataKey="valor" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabela Geral */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Tabela Geral de Receitas
        </h3>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Categoria / Termo Técnico</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Valor Estimado</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Traduzindo...</th>
              </tr>
            </thead>
            <tbody>
              {data.receitas_correntes.map((r, idx) => (
                <tr 
                  key={idx} 
                  className={`border-b border-gray-100 hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-gray-50/50' : ''}`}
                >
                  <td className="py-3 px-4 font-medium text-gray-900">{r.categoria}</td>
                  <td className="py-3 px-4 text-right font-bold text-blue-600">
                    {formatCurrency(r.valor)}
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-sm italic">
                    {r.descricao_popular || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

