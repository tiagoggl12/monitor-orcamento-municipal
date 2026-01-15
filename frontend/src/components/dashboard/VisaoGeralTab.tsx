import { useState, useEffect } from 'react';
import { 
  DollarSign, 
  Building2, 
  ShieldCheck, 
  Percent,
  TrendingUp,
  Loader2
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend
} from 'recharts';
import { dashboardApi, type VisaoGeralData } from '../../services/api';

interface Props {
  ano: number;
}

const COLORS = {
  fiscal: '#3B82F6',       // Blue
  seguridade: '#10B981',   // Green
};

export default function VisaoGeralTab({ ano }: Props) {
  const [data, setData] = useState<VisaoGeralData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [ano]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getVisaoGeral(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar visão geral:', err);
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

  const pieData = [
    { name: 'Orçamento Fiscal', value: data.orcamento_fiscal, color: COLORS.fiscal },
    { name: 'Seguridade Social', value: data.orcamento_seguridade, color: COLORS.seguridade },
  ];

  const orgaosData = data.top_orgaos.slice(0, 6).map(org => ({
    name: org.nome.length > 30 ? org.nome.substring(0, 30) + '...' : org.nome,
    valor: org.valor,
  }));

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Orçamento Total */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <DollarSign className="h-5 w-5 text-blue-600" />
            </div>
            <span className="text-sm text-gray-500">Orçamento Total</span>
            {data.variacao_ano_anterior && (
              <span className="ml-auto text-green-600 text-sm font-medium flex items-center">
                <TrendingUp className="h-4 w-4 mr-1" />
                +{data.variacao_ano_anterior}%
              </span>
            )}
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(data.orcamento_total)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {formatFullCurrency(data.orcamento_total)}
          </p>
        </div>

        {/* Orçamento Fiscal */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <Building2 className="h-5 w-5 text-blue-600" />
            </div>
            <span className="text-sm text-gray-500">Orçamento Fiscal</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(data.orcamento_fiscal)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {((data.orcamento_fiscal / data.orcamento_total) * 100).toFixed(1)}% do total
          </p>
        </div>

        {/* Seguridade Social */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-green-100 p-2 rounded-lg">
              <ShieldCheck className="h-5 w-5 text-green-600" />
            </div>
            <span className="text-sm text-gray-500">Seguridade Social</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(data.orcamento_seguridade)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {((data.orcamento_seguridade / data.orcamento_total) * 100).toFixed(1)}% do total
          </p>
        </div>

        {/* Limite Suplementação */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-orange-100 p-2 rounded-lg">
              <Percent className="h-5 w-5 text-orange-600" />
            </div>
            <span className="text-sm text-gray-500">Lim. Suplementação</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {data.limite_suplementacao ? `${data.limite_suplementacao}%` : 'N/A'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Créditos adicionais
          </p>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de Pizza - Esferas */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Esferas Orçamentárias
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value: number) => formatFullCurrency(value)}
              />
              <Legend 
                verticalAlign="bottom" 
                height={36}
                formatter={(value) => <span className="text-sm text-gray-600">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Gráfico de Barras - Top Órgãos */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top Secretarias e Fundos
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              layout="vertical"
              data={orgaosData}
              margin={{ left: 20, right: 20 }}
            >
              <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
              <YAxis 
                type="category" 
                dataKey="name" 
                width={150}
                tick={{ fontSize: 11 }}
              />
              <Tooltip formatter={(value: number) => formatFullCurrency(value)} />
              <Bar dataKey="valor" fill="#3B82F6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabela de Programas */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Principais Programas de Governo
          </h3>
          <span className="text-sm text-gray-500">
            {data.principais_programas.length} programas
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">ID</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Programa</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Fiscal</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Seguridade</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.principais_programas.map((prog, idx) => (
                <tr 
                  key={prog.codigo} 
                  className={`border-b border-gray-100 hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-gray-50/50' : ''}`}
                >
                  <td className="py-3 px-4">
                    <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm font-medium">
                      {prog.codigo}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-medium text-gray-900">
                    {prog.nome}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    {formatCurrency(prog.valor_fiscal)}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    {formatCurrency(prog.valor_seguridade)}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-blue-600">
                    {formatCurrency(prog.valor_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info do Prefeito */}
      {data.prefeito && (
        <div className="bg-gray-50 rounded-xl p-4 text-center text-sm text-gray-500">
          <span>Prefeito: <strong className="text-gray-700">{data.prefeito}</strong></span>
          <span className="mx-3">•</span>
          <span>Exercício {data.ano}</span>
        </div>
      )}
    </div>
  );
}

